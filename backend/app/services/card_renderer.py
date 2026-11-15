import os
import io
import base64
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
from app.core.config import settings

class CardRenderer:
    """Renders 1200x630 OpenGraph social cards adhering to the Obsidian Atelier design system."""

    def render_launch_card_image(self, dossier: Dict[str, Any]) -> Image.Image:
        width = 1200
        height = 630
        
        # 1. Void canvas (#06070B)
        image = Image.new("RGBA", (width, height), (6, 7, 11, 255))
        draw = ImageDraw.Draw(image)

        # 2. Specular Luminous Horizon Arc (Indigo #6366f1 to Violet #a855f7)
        for r in range(250, 0, -5):
            alpha = int(45 * (1 - r / 250))
            draw.ellipse(
                [(600 - r * 2.5, -150 - r), (600 + r * 2.5, 150 + r)],
                fill=(99, 102, 241, alpha)
            )

        # 3. Foreground Editorial Paper Card (#F8F9FA) with rounded edges
        card_x0, card_y0 = 60, 90
        card_x1, card_y1 = 1140, 570
        draw.rounded_rectangle(
            [(card_x0, card_y0), (card_x1, card_y1)],
            radius=16,
            fill=(248, 249, 250, 255),
            outline=(255, 255, 255, 60),
            width=2
        )

        # Text rendering with default fonts
        title = dossier.get("title", "Autonomous Proof-of-Work")[:55]
        tagline = dossier.get("tagline", "High-throughput distributed systems architecture.")[:90]
        domain = dossier.get("domain_persona", "tech_builder").upper().replace("_", " ")

        # Header bar on paper card
        draw.text((100, 125), f"STUDENT RADAR // {domain}", fill=(107, 114, 128))
        draw.text((920, 125), "VERIFIED ARTIFACT", fill=(16, 185, 129))

        # Main Title & Tagline
        draw.text((100, 175), title, fill=(17, 24, 39))
        draw.text((100, 225), tagline, fill=(75, 85, 99))

        # Divider line
        draw.line([(100, 280), (1100, 280)], fill=(229, 231, 235), width=2)

        # Metrics display
        metrics = dossier.get("key_metrics", [])
        start_x = 100
        for i, m in enumerate(metrics[:3]):
            box_x = start_x + (i * 330)
            draw.rounded_rectangle(
                [(box_x, 310), (box_x + 300, 420)],
                radius=10,
                fill=(255, 255, 255, 255),
                outline=(229, 231, 235, 255),
                width=1
            )
            draw.text((box_x + 20, 330), m.get("label", "Metric").upper(), fill=(107, 114, 128))
            draw.text((box_x + 20, 365), str(m.get("value", "N/A")), fill=(17, 24, 39))

        # Tech Stack footer
        tech_list = " • ".join(dossier.get("tech_stack", ["Python", "Rust", "FastAPI"])[:5])
        draw.text((100, 480), f"CORE ARTIFACTS: {tech_list}", fill=(55, 65, 81))
        draw.text((880, 515), "studentradar.dev/p/", fill=(99, 102, 241))

        return image

    def generate_card_data_uri(self, dossier: Dict[str, Any]) -> str:
        """Renders the card and returns a base64 data URI."""
        img = self.render_launch_card_image(dossier)
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/png;base64,{encoded}"

card_renderer = CardRenderer()

