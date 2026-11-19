"use client";

import React, { useEffect } from "react";
import { X } from "lucide-react";

interface DetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  eyebrow?: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

/** Right-side panel used everywhere on the dashboard so every card can be
 * opened to reveal the actual work/info behind it. */
export function DetailDrawer({
  isOpen,
  onClose,
  eyebrow,
  title,
  subtitle,
  children,
  footer,
}: DetailDrawerProps) {
  useEffect(() => {
    if (!isOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex justify-end" role="dialog" aria-modal="true">
      <button
        aria-label="Close details"
        onClick={onClose}
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
      />
      <div className="relative flex h-full w-full max-w-xl flex-col border-l border-void-border bg-void-card shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-void-border px-6 py-5">
          <div>
            {eyebrow && (
              <p className="mb-1 font-mono text-[10px] uppercase tracking-widest text-horizon-indigo">
                {eyebrow}
              </p>
            )}
            <h2 className="text-lg font-bold text-white">{title}</h2>
            {subtitle && <p className="mt-1 text-xs text-gray-400">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            className="rounded-lg border border-void-border p-1.5 text-gray-400 transition-colors hover:text-white"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-6 py-5">{children}</div>

        {footer && <div className="border-t border-void-border px-6 py-4">{footer}</div>}
      </div>
    </div>
  );
}

export function DrawerSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h3 className="font-mono text-[10px] uppercase tracking-widest text-gray-500">{title}</h3>
      <div className="space-y-2 text-xs text-gray-300">{children}</div>
    </section>
  );
}

export function DrawerRow({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-void-border bg-void p-3">
      <div className="min-w-0">
        <p className="text-xs font-semibold text-white">{title}</p>
        {detail && <p className="mt-1 text-[11px] leading-relaxed text-gray-400">{detail}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
