from datetime import datetime, timezone, timedelta
from typing import Optional

class CalendarService:
    """Generates RFC 5545 compliant .ics calendar export files."""

    @staticmethod
    def generate_ics(
        title: str,
        description: str,
        deadline: datetime,
        url: str,
        host_organization: Optional[str] = None
    ) -> str:
        # Standard format: YYYYMMDDTHHMMSSZ
        start_time = deadline - timedelta(hours=2)
        dt_start_str = start_time.strftime("%Y%m%dT%H%M%SZ")
        dt_end_str = deadline.strftime("%Y%m%dT%H%M%SZ")
        dt_stamp_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        organizer = host_organization or "Student Radar Event Engine"

        # Sanitize single-line text fields
        clean_title = title.replace("\n", " ").replace("\r", "")
        clean_desc = description.replace("\n", "\\n").replace("\r", "")

        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Student Radar//Event Engine//EN\r\n"
            "CALSCALE:GREGORIAN\r\n"
            "METHOD:PUBLISH\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:student-radar-{int(deadline.timestamp())}@studentradar.dev\r\n"
            f"DTSTAMP:{dt_stamp_str}\r\n"
            f"DTSTART:{dt_start_str}\r\n"
            f"DTEND:{dt_end_str}\r\n"
            f"SUMMARY:{clean_title} [DEADLINE]\r\n"
            f"DESCRIPTION:{clean_desc}\\n\\nCanonical URL: {url}\r\n"
            f"URL:{url}\r\n"
            f"ORGANIZER;CN={organizer}:MAILTO:radar@studentradar.dev\r\n"
            "STATUS:CONFIRMED\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR\r\n"
        )
        return ics_content

calendar_service = CalendarService()

