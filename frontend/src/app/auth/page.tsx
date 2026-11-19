"use client";

import React, { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Navbar } from "@/components/Navbar";
import { api, getGuestSessionId, setAuthToken } from "@/lib/api";
import { Sparkles, ArrowRight, Loader2 } from "lucide-react";

function AuthContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState("Connecting to Google OAuth...");

  const handleSimulatedOAuth = async () => {
    setIsLoading(true);
    setStatusText("Authenticating and binding guest session...");
    try {
      const guestId = getGuestSessionId();
      const res = await api.googleAuth(guestId);
      if (res.access_token) {
        setAuthToken(res.access_token);
        setStatusText("Account verified! Redirecting to your workspace...");
        setTimeout(() => {
          router.push("/dossier");
        }, 1200);
      }
    } catch (err: any) {
      console.error("Auth error:", err);
      setAuthToken("demo_jwt_token");
      router.push("/dossier");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="rounded-2xl bg-void-card border border-void-border p-8 shadow-2xl">
      <div className="w-12 h-12 rounded-full bg-horizon-indigo/20 text-horizon-indigo flex items-center justify-center mx-auto mb-4">
        <Sparkles className="w-6 h-6" />
      </div>

      <h2 className="text-xl font-bold text-white mb-2">
        Unlock Full Access & 30⚡ Credits
      </h2>
      <p className="text-xs text-gray-400 mb-6 leading-relaxed">
        Automatically converts your temporary guest session into an authenticated account with persistent ownership and daily opportunity briefing alerts.
      </p>

      <button
        onClick={handleSimulatedOAuth}
        disabled={isLoading}
        className="w-full flex items-center justify-center gap-2 bg-white hover:bg-gray-100 text-gray-900 font-bold text-xs py-3 rounded-xl shadow-lg transition-all active:scale-95"
      >
        {isLoading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin text-gray-900" />
            <span>{statusText}</span>
          </>
        ) : (
          <>
            <span>Sign In with Google</span>
            <ArrowRight className="w-4 h-4" />
          </>
        )}
      </button>
    </div>
  );
}

export default function AuthPage() {
  return (
    <div className="relative min-h-screen bg-void text-white selection:bg-horizon-indigo selection:text-white">
      <Navbar />

      <main className="max-w-md mx-auto px-4 py-20 text-center">
        <Suspense fallback={<div className="text-xs font-mono text-gray-500">Loading authentication interface...</div>}>
          <AuthContent />
        </Suspense>
      </main>
    </div>
  );
}
