"""Stage 1 GitHub ingestion for Dossier v2.

Reads a bounded, evidence-bearing snapshot of a public repository through the
GitHub REST API. Never indexes a file containing a credential. README claims
are checked against the repository tree rather than trusted.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
DEFAULT_BRANCHES = ("main", "master")
KEY_FILES = (
    "README.md", "readme.md", "LICENSE", "LICENSE.md", "COPYING",
    "package.json", "requirements.txt", "pyproject.toml", "Dockerfile",
    "Cargo.toml", "go.mod", "pom.xml", "Makefile",
    "docs/README.md", "docs/architecture.md", "MODEL_CARD.md", "model-card.md",
    "dataset_card.md", "DATASET_CARD.md",
)
SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[\"']?[A-Za-z0-9_\-]{24,}"),
]
_CLAIM_RE = re.compile(r"(?i)(\d{1,3}(?:\.\d+)?\s?%|accuracy|benchmark|state of the art|SOTA)")
_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 900


def _repo_coords(url: str) -> Optional[Tuple[str, str]]:
    match = re.search(r"github\.com/([^/\s]+)/([^/\s?#]+)", url or "", re.IGNORECASE)
    if not match:
        return None
    return match.group(1), match.group(2).removesuffix(".git")


def _decode(content: str, encoding: str) -> str:
    if encoding == "base64":
        try:
            return base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception:
            return ""
    return content


def _secret_scan(text: str) -> List[str]:
    findings = []
    for pattern in SECRET_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append(pattern.pattern[:40])
    return findings


class GitHubIngestor:
    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self.client = client

    async def ingest(self, url: str) -> Dict[str, Any]:
        coords = _repo_coords(url)
        if not coords:
            return {"source_type": "github", "url": url, "ingest_error": "Not a GitHub repository URL"}
        owner, repo = coords
        cache_key = hashlib.sha256(f"{owner}/{repo}".encode()).hexdigest()
        cached = _CACHE.get(cache_key)
        if cached and time.time() - cached[0] < _CACHE_TTL_SECONDS:
            return {**cached[1], "cache_hit": True}

        owns = self.client is None
        client = self.client or httpx.AsyncClient(timeout=12.0, follow_redirects=True,
                                                  headers=self._headers())
        try:
            meta, tree, languages = await asyncio.gather(
                self._get_json(client, f"/repos/{owner}/{repo}"),
                self._get_tree(client, owner, repo),
                self._get_json(client, f"/repos/{owner}/{repo}/languages"),
            )
            default_branch = str((meta or {}).get("default_branch") or "main")
            paths = self._select_paths(tree)
            blobs = await asyncio.gather(*[
                self._get_text(client, owner, repo, default_branch, path) for path in paths
            ])
            releases = await self._get_json(client, f"/repos/{owner}/{repo}/releases/latest")
            commits = await self._get_json(client, f"/repos/{owner}/{repo}/commits?per_page=5")
            issues = await self._get_json(client, f"/repos/{owner}/{repo}/issues?state=open&per_page=5")

            files: Dict[str, str] = {}
            secrets_found: List[str] = []
            for path, text in zip(paths, blobs):
                if not text:
                    continue
                findings = _secret_scan(text)
                if findings:
                    secrets_found.append(path)
                    logger.warning("Refusing to index %s/%s: secret-like string detected", owner, repo)
                    continue
                files[path] = text[:4000]

            result = self._assemble(
                url=url, owner=owner, repo=repo, meta=meta or {}, tree=tree,
                languages=languages or {}, files=files, releases=releases,
                commits=commits, issues=issues, secrets_found=secrets_found,
            )
            _CACHE[cache_key] = (time.time(), result)
            return result
        finally:
            if owns:
                await client.aclose()

    @staticmethod
    def _headers() -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "LaunchPad-Dossier-v2/1.0 (research; public repositories only)",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"
        return headers

    async def _get_json(self, client: httpx.AsyncClient, path: str) -> Dict[str, Any] | List[Any]:
        try:
            response = await client.get(f"{API}{path}")
            if response.status_code != 200:
                logger.warning("GitHub API %s returned %s", path, response.status_code)
                return {}
            return response.json()
        except Exception as exc:
            logger.warning("GitHub API %s failed: %s", path, exc)
            return {}

    async def _get_tree(self, client: httpx.AsyncClient, owner: str, repo: str) -> List[Dict[str, Any]]:
        meta = await self._get_json(client, f"/repos/{owner}/{repo}")
        branch = str((meta or {}).get("default_branch") or DEFAULT_BRANCHES[0])
        data = await self._get_json(client, f"/repos/{owner}/{repo}/git/trees/{branch}?recursive=1")
        return [item for item in (data.get("tree") or []) if isinstance(item, dict)] if isinstance(data, dict) else []

    @staticmethod
    def _select_paths(tree: List[Dict[str, Any]]) -> List[str]:
        paths = [p for p in KEY_FILES if any(item.get("path") == p for item in tree)]
        # Add up to 4 bounded entry-point modules from the repository root.
        roots = [
            str(item["path"]) for item in tree
            if item.get("type") == "blob"
            and "/" not in str(item.get("path") or "")
            and str(item.get("path", "")).endswith((".py", ".ts", ".js", ".go", ".rs"))
        ][:4]
        for path in roots:
            if path not in paths:
                paths.append(path)
        return paths[:12]

    async def _get_text(self, client: httpx.AsyncClient, owner: str, repo: str, branch: str, path: str) -> str:
        try:
            response = await client.get(f"{RAW}/{owner}/{repo}/{branch}/{path}")
            if response.status_code == 200:
                return response.text[:6000]
        except Exception as exc:
            logger.warning("GitHub file fetch failed for %s: %s", path, exc)
        return ""

    @staticmethod
    def _assemble(
        *, url: str, owner: str, repo: str, meta: Dict[str, Any], tree: List[Dict[str, Any]],
        languages: Dict[str, Any], files: Dict[str, str], releases: Dict[str, Any],
        commits: Any, issues: Any, secrets_found: List[str],
    ) -> Dict[str, Any]:
        paths = [str(item.get("path") or "") for item in tree]
        has_tests = any("test" in path.lower() for path in paths)
        has_ci = any(".github/workflows" in path or path in {".travis.yml", "Jenkinsfile"} for path in paths)
        has_demo = any(token in path.lower() for path in paths for token in ("demo", "example"))
        has_model_card = any("model_card" in path.lower() or "model-card" in path.lower() for path in paths)
        has_dataset_doc = any("dataset_card" in path.lower() or "data/README" in path for path in paths)
        readme = next((v for k, v in files.items() if k.lower().startswith("readme")), "")
        licence = str((meta.get("license") or {}).get("spdx_id") or "") if isinstance(meta.get("license"), dict) else ""
        activity = commits[0].get("commit", {}).get("committer", {}).get("date") if isinstance(commits, list) and commits else None

        claims = []
        for sentence in re.split(r"(?<=[.!?])\s+|\n", readme):
            if _CLAIM_RE.search(sentence) and len(sentence.strip()) < 300:
                claims.append(sentence.strip()[:240])
        claims = claims[:8]

        claim_check = []
        for claim in claims:
            numeric = re.search(r"\d{1,3}(?:\.\d+)?\s?%", claim)
            supported = has_tests and any("eval" in path.lower() for path in paths)
            claim_check.append({
                "claim": claim,
                "status": "code_evidence_found" if supported else "no_evaluation_artifact_found",
                "note": (
                    "Test/evaluation files exist in the tree; verify the exact metric before relying on it."
                    if supported else
                    "README states a metric but no evaluation script or report was detected in the bounded file sample."
                ),
                "numeric": bool(numeric),
            })

        maturity = "idea"
        if meta.get("stargazers_count", 0) >= 10 or has_tests:
            maturity = "prototype"
        if meta.get("stargazers_count", 0) >= 100 or (has_tests and has_ci):
            maturity = "working"
        if releases and has_ci:
            maturity = "maintained"

        gaps = []
        if not has_tests:
            gaps.append("No test files detected in repository tree")
        if not has_ci:
            gaps.append("No CI workflow detected")
        if not licence or licence == "NOASSERTION":
            gaps.append("No machine-readable licence detected")
        if not has_dataset_doc and any("dataset" in c.lower() for c in claims):
            gaps.append("Dataset claims without a dataset card")
        if not has_model_card and any("model" in c.lower() for c in claims):
            gaps.append("Model claims without a model card")
        if not activity:
            gaps.append("Recent commit activity could not be confirmed")

        dna = {
            "source_type": "github",
            "title": str(meta.get("name") or repo).replace("-", " ").replace("_", " ").title(),
            "repo_full_name": f"{owner}/{repo}",
            "url": url,
            "description": str(meta.get("description") or ""),
            "topics": list(meta.get("topics") or []),
            "stars": int(meta.get("stargazers_count") or 0),
            "forks": int(meta.get("forks_count") or 0),
            "open_issues": int(meta.get("open_issues_count") or 0),
            "last_commit_at": activity,
            "default_branch": str(meta.get("default_branch") or "main"),
            "languages": languages,
            "license": licence,
            "files": files,
            "file_tree_sample": paths[:120],
            "readme": readme[:12000],
            "dependency_manifests": [k for k in files if k in {
                "package.json", "requirements.txt", "pyproject.toml", "Dockerfile",
                "Cargo.toml", "go.mod", "pom.xml"}],
            "tests_detected": has_tests,
            "ci_detected": has_ci,
            "demo_detected": has_demo,
            "model_card_detected": has_model_card,
            "dataset_doc_detected": has_dataset_doc,
            "releases_detected": bool(releases),
            "maturity_signal": maturity,
            "claims": claims,
            "claim_checks": claim_check,
            "code_gaps": gaps,
            "secrets_found": secrets_found,
            "problem": str(meta.get("description") or readme[:600] or url),
            "solution": f"Existing repository {owner}/{repo} implementing: {str(meta.get('description') or 'see README')[:300]}",
            "audience_guess": "Developers and researchers who depend on this repository",
            "stage": "Prototype" if maturity in {"idea", "prototype"} else "MVP",
            "technique": ", ".join(list(languages.keys())[:6]),
            "assumptions": [
                "The README describes the current default branch.",
                "Bounded file sampling (max 12 files) may miss files in nested directories.",
            ],
            "unknowns": [
                "Runtime performance was not measured.",
                "Actual user adoption cannot be inferred from stars alone.",
            ],
        }
        return dna


github_ingestor = GitHubIngestor()
