import os
import logging
from typing import Dict, Any
from app.services.gemini_client import gemini_service

logger = logging.getLogger(__name__)

class PRStrategist:
    """Orchestrates promotional PR copy using version-controlled Markdown playbooks."""

    def __init__(self):
        self.playbooks_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "configs",
            "playbooks"
        )

    def load_playbook(self, playbook_type: str) -> str:
        file_map = {
            "linkedin": "linkedin_playbook.md",
            "instagram_reel": "instagram_reel_playbook.md",
            "cold_pitch": "cold_pitch_playbook.md"
        }
        filename = file_map.get(playbook_type, "linkedin_playbook.md")
        filepath = os.path.join(self.playbooks_dir, filename)

        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()

        return "# Standard PR Playbook\nStructure clearly with high contrast and verifiable proof."

    async def generate_pr_assets(
        self,
        dossier: Dict[str, Any],
        playbook_type: str = "linkedin",
        tone: str = "high_octane",
        target_audience: str = "Engineers and Investors"
    ) -> Dict[str, Any]:
        playbook_md = self.load_playbook(playbook_type)
        return await gemini_service.generate_pr_copy(
            dossier_data=dossier,
            playbook_markdown=playbook_md,
            tone=tone,
            target_audience=target_audience
        )

pr_strategist = PRStrategist()

