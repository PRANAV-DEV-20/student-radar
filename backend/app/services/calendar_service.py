"""RFC 5545 iCalendar generation."""

import hashlib
from datetime import datetime, timedelta, timezone
from typing import List, Optional


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _escape_text(value: str) -> str:
    """Escape a TEXT property value per RFC 5545 §3.3.11."""
    if value is None:
        return ""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _fold_line(line: str, limit: int = 75) -> List[str]:
    """Fold long content lines at 75 octets, never splitting a UTF-8 char."""
    encoded = line.encode("utf-8")
    if len(encoded) <= limit:
        return [line]

    folded: List[str] = []
    current = ""
    current_bytes = 0
    for char in line:
        char_bytes = len(char.encode("utf-8"))
        if current_bytes + char_bytes > limit:
            folded.append(current)
            current = " " + char
            current_bytes = 1 + char_bytes
        else:
            current += char
            current_bytes += char_bytes
    if current:
        folded.append(current)
    return folded


class CalendarService:
    """Generates RFC 5545 compliant .ics calendar export files."""

    @staticmethod
    def generate_ics(
        title: str,
        description: str,
        deadline: datetime,
        url: str,
        host_organization: Optional[str] = None,
        event_id: Optional[str] = None,
    ) -> str:
        deadline_utc = _as_utc(deadline)
        start_time = deadline_utc - timedelta(hours=2)
        dt_start_str = start_time.strftime("%Y%m%dT%H%M%SZ")
        dt_end_str = deadline_utc.strftime("%Y%m%dT%H%M%SZ")
        dt_stamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        organizer = _escape_text(host_organization or "Student Radar Event Engine")

        if event_id:
            uid_suffix = str(event_id).strip()
        else:
            digest = hashlib.sha256(
                f"{title}|{url}|{deadline_utc.isoformat()}".encode("utf-8")
            ).hexdigest()[:16]
            uid_suffix = digest

        uid = f"student-radar-{uid_suffix}@studentradar.dev"
        summary = _escape_text(f"{title} [DEADLINE]")
        description_text = _escape_text(
            f"{description}\n\nCanonical URL: {url}"
        )
        url_text = _escape_text(url or "")

        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Student Radar//Event Engine//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dt_stamp_str}",
            f"DTSTART:{dt_start_str}",
            f"DTEND:{dt_end_str}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description_text}",
            f"URL:{url_text}",
            f"ORGANIZER;CN={organizer}:MAILTO:radar@studentradar.dev",
            "STATUS:CONFIRMED",
            "END:VEVENT",
            "END:VCALENDAR",
        ]

        folded_lines: List[str] = []
        for line in lines:
            folded_lines.extend(_fold_line(line))
        return "\r\n".join(folded_lines) + "\r\n"


calendar_service = CalendarService()
