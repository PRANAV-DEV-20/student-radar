import asyncio
import logging
import re
import uuid
from typing import Any, Dict, List, Optional

import httpx

from app.services.benchmark_scout import benchmark_scout
from app.services.gemini_client import gemini_service
from app.services.trend_scout import trend_scout

logger = logging.getLogger(__name__)

ALLOWED_STAGES = {"Idea", "Prototype", "MVP", "Research"}


class IngestionAgent:
    @staticmethod
    def generate_slug(title: str) -> str:
        """Creates a clean, URL-safe slug with unique 6-character suffix."""
        cleaned = re.sub(r"[^\w\s-]", "", (title or "").lower())
        slug_base = re.sub(r"[-\s]+", "-", cleaned).strip("-")[:45] or "project"
        suffix = uuid.uuid4().hex[:6]
        return f"{slug_base}-{suffix}"

    @staticmethod
    async def fetch_github_content(url: str) -> str:
        """Fetches README.md and repository metadata from GitHub."""
        match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
        if not match:
            return f"GitHub Project URL: {url}"

        owner, repo = match.group(1), match.group(2).replace(".git", "")
        raw_readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md"
        fallback_readme_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md"

        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            try:
                res = await client.get(raw_readme_url)
                if res.status_code == 200:
                    return res.text[:12000]
                res2 = await client.get(fallback_readme_url)
                if res2.status_code == 200:
                    return res2.text[:12000]
            except Exception as e:
                logger.warning(f"Failed to fetch GitHub README for {owner}/{repo}: {e}")

        return (
            f"GitHub Project: {owner}/{repo}\nURL: {url}\n"
            "Automated extraction of repository structure and open-source artifacts."
        )

    @staticmethod
    def extract_pdf_text(file_bytes: bytes) -> str:
        """Extracts text from PDF bytes using PyMuPDF (fitz)."""
        try:
            import fitz

            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text_chunks = [page.get_text() for page in doc]
            doc.close()
            text = "\n\n".join(text_chunks).strip()
            if not text:
                return "Empty PDF document."
            return text[:15000]
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return "Failed to parse PDF document. Falling back to title extraction."

    @staticmethod
    def _normalize_stage(value: Optional[str]) -> str:
        if not value:
            return "Prototype"
        normalized = str(value).strip().title()
        for stage in ALLOWED_STAGES:
            if normalized == stage.lower() or normalized == stage:
                return stage
        return "Prototype"

    @staticmethod
    async def _safe(coro, fallback):
        try:
            return await coro
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("Ingestion enrichment step failed: %s", exc)
            return fallback

    def _role_embedding_text(self, dossier_data: Dict[str, Any]) -> str:
        roles: List[str] = []
        for item in dossier_data.get("missing_roles") or []:
            if isinstance(item, dict) and item.get("role"):
                roles.append(str(item["role"]))
            elif isinstance(item, str):
                roles.append(item)
        if not roles:
            roles = ["Open co-builder with complementary verified portfolio skills"]
        return " || ".join(roles)

    async def process_artifact(
        self,
        input_type: str,
        raw_content: str,
        domain_persona: str = "tech_builder",
    ) -> Dict[str, Any]:
        """Orchestrates content acquisition, LLM extraction, trend scouting, and embeddings."""
        extracted_text = raw_content

        if input_type == "github" and ("github.com" in raw_content):
            extracted_text = await self.fetch_github_content(raw_content)

        # 1. Structured dossier extraction via Gemini (deterministic fallback if
        # the API key is absent or the upstream call fails).
        dossier_data = await gemini_service.generate_structured_dossier(
            raw_content=extracted_text,
            domain_persona=domain_persona,
            input_type=input_type,
        )

        dossier_data["slug"] = self.generate_slug(dossier_data.get("title", "Project Dossier"))
        dossier_data["stage"] = self._normalize_stage(dossier_data.get("stage"))
        dossier_data["domain_persona"] = domain_persona

        tech_stack = dossier_data.get("tech_stack") or []
        title = dossier_data.get("title", "Project Dossier")

        embed_text = (
            f"{title}: {dossier_data.get('tagline', '')} "
            f"{dossier_data.get('problem_statement', '')} "
            f"{' '.join(str(item) for item in tech_stack)}"
        )
        role_text = self._role_embedding_text(dossier_data)

        # 2. Parallel trend scouting, ecosystem benchmarking, and embeddings.
        trend_result, benchmark_result, embedding, missing_roles_embedding = await asyncio.gather(
            self._safe(
                trend_scout.scout_whitespace(
                    title=title,
                    domain_persona=domain_persona,
                    tech_stack=[str(item) for item in tech_stack],
                ),
                {},
            ),
            self._safe(
                benchmark_scout.build_benchmark(
                    {
                        "title": title,
                        "tagline": dossier_data.get("tagline", ""),
                        "problem_statement": dossier_data.get("problem_statement", ""),
                        "tech_stack": tech_stack,
                        "domain_persona": domain_persona,
                    }
                ),
                None,
            ),
            self._safe(gemini_service.generate_embedding(embed_text), []),
            self._safe(gemini_service.generate_embedding(role_text), []),
        )

        if trend_result:
            dossier_data["trend_radar_cache"] = trend_result
            whitespace = dossier_data.get("whitespace_analysis") or {}
            if isinstance(whitespace, dict) and not whitespace.get("market_gap"):
                dossier_data["whitespace_analysis"] = {
                    "market_gap": trend_result.get("market_gap", ""),
                    "top_voices": trend_result.get("top_voices", []),
                }
        else:
            dossier_data.setdefault("trend_radar_cache", dossier_data.get("whitespace_analysis") or {})

        dossier_data["benchmark_analysis"] = benchmark_result
        dossier_data["embedding"] = embedding or None
        dossier_data["missing_roles_embedding"] = missing_roles_embedding or None
        return dossier_data

    async def process_pdf_bytes(
        self,
        file_bytes: bytes,
        domain_persona: str = "tech_builder",
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract text from an uploaded PDF and run the standard pipeline."""
        text = self.extract_pdf_text(file_bytes)
        if filename:
            text = f"Uploaded document: {filename}\n\n{text}"
        return await self.process_artifact(
            input_type="pdf_text",
            raw_content=text,
            domain_persona=domain_persona,
        )


ingestion_agent = IngestionAgent()
