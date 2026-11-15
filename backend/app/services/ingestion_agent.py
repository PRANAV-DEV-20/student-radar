import re
import uuid
import logging
import httpx
from typing import Dict, Any, Optional
from app.services.gemini_client import gemini_service

logger = logging.getLogger(__name__)

class IngestionAgent:
    @staticmethod
    def generate_slug(title: str) -> str:
        """Creates a clean, URL-safe slug with unique 6-character suffix."""
        cleaned = re.sub(r"[^\w\s-]", "", title.lower())
        slug_base = re.sub(r"[-\s]+", "-", cleaned).strip("-")[:45]
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

        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.get(raw_readme_url)
                if res.status_code == 200:
                    return res.text[:12000]
                res2 = await client.get(fallback_readme_url)
                if res2.status_code == 200:
                    return res2.text[:12000]
            except Exception as e:
                logger.warning(f"Failed to fetch GitHub README for {owner}/{repo}: {e}")

        return f"GitHub Project: {owner}/{repo}\nURL: {url}\nAutomated extraction of repository structure and open-source artifacts."

    @staticmethod
    def extract_pdf_text(file_bytes: bytes) -> str:
        """Extracts text from PDF bytes using PyMuPDF (fitz)."""
        try:
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text_chunks = []
            for page in doc:
                text_chunks.append(page.get_text())
            doc.close()
            return "\n\n".join(text_chunks)[:15000]
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return "Failed to parse PDF document. Falling back to title extraction."

    async def process_artifact(
        self,
        input_type: str,
        raw_content: str,
        domain_persona: str = "tech_builder"
    ) -> Dict[str, Any]:
        """Orchestrates content acquisition, LLM extraction, and embedding creation."""
        extracted_text = raw_content

        if input_type == "github" and ("github.com" in raw_content):
            extracted_text = await self.fetch_github_content(raw_content)

        # 1. Structured dossier extraction via Gemini
        dossier_data = await gemini_service.generate_structured_dossier(
            raw_content=extracted_text,
            domain_persona=domain_persona,
            input_type=input_type
        )

        # Ensure slug is generated
        slug = self.generate_slug(dossier_data.get("title", "Project Dossier"))
        dossier_data["slug"] = slug

        # 2. Embedding calculation for vector matching
        embed_text = f"{dossier_data.get('title', '')}: {dossier_data.get('tagline', '')} {dossier_data.get('problem_statement', '')}"
        embedding = await gemini_service.generate_embedding(embed_text)
        dossier_data["embedding"] = embedding

        return dossier_data

ingestion_agent = IngestionAgent()

