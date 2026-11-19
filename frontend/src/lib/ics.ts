/**
 * Client-Side RFC 5545 .ics Calendar File Downloader
 */

export function downloadCalendarEvent(event: {
  title: string;
  description: string;
  deadline: string;
  url: string;
  host_organization?: string;
}): void {
  const deadlineDate = new Date(event.deadline);
  const startDate = new Date(deadlineDate.getTime() - 2 * 60 * 60 * 1000); // 2 hours before

  const formatICSDate = (d: Date) =>
    d.toISOString().replace(/[-:]/g, "").split(".")[0] + "Z";

  const cleanTitle = event.title.replace(/\n/g, " ");
  const cleanDesc = event.description.replace(/\n/g, "\\n");
  const host = event.host_organization || "Student Radar Event Engine";

  const icsContent = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Student Radar//Event Engine//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    `UID:student-radar-${Date.now()}@studentradar.dev`,
    `DTSTAMP:${formatICSDate(new Date())}`,
    `DTSTART:${formatICSDate(startDate)}`,
    `DTEND:${formatICSDate(deadlineDate)}`,
    `SUMMARY:${cleanTitle} [DEADLINE]`,
    `DESCRIPTION:${cleanDesc}\\n\\nCanonical URL: ${event.url}`,
    `URL:${event.url}`,
    `ORGANIZER;CN=${host}:MAILTO:radar@studentradar.dev`,
    "STATUS:CONFIRMED",
    "END:VEVENT",
    "END:VCALENDAR"
  ].join("\r\n");

  const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
  const link = document.createElement("a");
  link.href = window.URL.createObjectURL(blob);
  link.setAttribute("download", `radar-event-${event.title.substring(0, 20).toLowerCase().replace(/\s+/g, "-")}.ics`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

