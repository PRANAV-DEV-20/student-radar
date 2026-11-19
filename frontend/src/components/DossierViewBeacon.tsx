"use client";

import { useEffect } from "react";
import { getGuestSessionId } from "@/lib/api";

/**
 * Fires one anonymous, non-blocking view beacon for a public dossier page.
 * Kept as a tiny client island so the public page can remain a server component.
 */
export function DossierViewBeacon({ slug }: { slug: string }) {
  useEffect(() => {
    if (!slug) return;
    const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const payload = JSON.stringify({ source: "public_page" });

    try {
      const blob = new Blob([payload], { type: "application/json" });
      const sent = navigator.sendBeacon?.(
        `${base}/dossiers/${encodeURIComponent(slug)}/view`,
        blob,
      );
      if (sent) return;
    } catch {
      // Fall through to fetch below.
    }

    fetch(`${base}/dossiers/${encodeURIComponent(slug)}/view`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Guest-Session-ID": getGuestSessionId(),
      },
      body: payload,
      keepalive: true,
    }).catch(() => undefined);
  }, [slug]);

  return null;
}
