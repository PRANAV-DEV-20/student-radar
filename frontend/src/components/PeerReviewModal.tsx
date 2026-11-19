"use client";

import React, { useState } from "react";
import { X, Sparkles, Check, AlertCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface PeerReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  dossierId: string;
  dossierTitle: string;
  onReviewSuccess?: (newBalance: number) => void;
}

export function PeerReviewModal({
  isOpen,
  onClose,
  dossierId,
  dossierTitle,
  onReviewSuccess
}: PeerReviewModalProps) {
  const [strength, setStrength] = useState("");
  const [bottleneck, setBottleneck] = useState("");
  const [suggestion, setSuggestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [isSuccess, setIsSuccess] = useState(false);

  if (!isOpen) return null;

  const totalLength = strength.trim().length + bottleneck.trim().length + suggestion.trim().length;
  const isSatisfied = totalLength >= 80;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isSatisfied) return;

    setIsLoading(true);
    setErrorMsg("");

    try {
      const res = await api.submitPeerReview({
        dossier_id: dossierId,
        rubric: {
          strength: strength.trim(),
          bottleneck: bottleneck.trim(),
          suggestion: suggestion.trim()
        }
      });

      setIsSuccess(true);
      if (onReviewSuccess) {
        onReviewSuccess(res.new_balance || 40);
      }
      setTimeout(() => {
        setIsSuccess(false);
        onClose();
      }, 1800);
    } catch (err: any) {
      setErrorMsg(err.message || "Review submission failed.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md">
      <div className="relative w-full max-w-lg rounded-2xl bg-void-card border border-void-border p-6 shadow-2xl text-white">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-gray-400 hover:text-white bg-void hover:bg-void-border transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center gap-2 mb-4">
          <div className="p-2 rounded-lg bg-horizon-violet/10 border border-horizon-violet/30">
            <Sparkles className="w-5 h-5 text-horizon-violet" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              Substantive Peer Review Rubric
              <span className="text-[10px] font-mono bg-horizon-violet/20 text-horizon-violet border border-horizon-violet/40 px-2 py-0.5 rounded-full">
                +10⚡ Reward
              </span>
            </h3>
            <span className="text-xs text-gray-400">Reviewing: {dossierTitle}</span>
          </div>
        </div>

        {/* Anti-spam rubric guidance */}
        <p className="text-xs text-gray-400 mb-4 leading-relaxed">
          To prevent spam and maintain community signal, reviews must address all 3 rubric dimensions with at least 80 characters total.
        </p>

        {errorMsg && (
          <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-400 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {isSuccess ? (
          <div className="py-8 text-center space-y-2">
            <div className="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
              <Check className="w-6 h-6" />
            </div>
            <h4 className="text-sm font-bold text-white">Review Verified & Accepted!</h4>
            <p className="text-xs text-gray-400">+10⚡ Visibility Credits awarded to your account.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3.5">
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                1. Technical / Architectural Strength:
              </label>
              <textarea
                rows={2}
                value={strength}
                onChange={(e) => setStrength(e.target.value)}
                placeholder="What architectural decision or benchmark impressed you?"
                className="w-full rounded-xl bg-void border border-void-border p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-horizon-violet"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                2. Potential Bottleneck / Vulnerability:
              </label>
              <textarea
                rows={2}
                value={bottleneck}
                onChange={(e) => setBottleneck(e.target.value)}
                placeholder="Where does this fail under scale, packet loss, or extreme stress?"
                className="w-full rounded-xl bg-void border border-void-border p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-horizon-violet"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                3. Concrete Actionable Suggestion:
              </label>
              <textarea
                rows={2}
                value={suggestion}
                onChange={(e) => setSuggestion(e.target.value)}
                placeholder="What alternative protocol or benchmark should the team run?"
                className="w-full rounded-xl bg-void border border-void-border p-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-horizon-violet"
              />
            </div>

            {/* Character Count Progress */}
            <div className="flex items-center justify-between text-[11px] font-mono pt-1">
              <span className={totalLength >= 80 ? "text-emerald-400" : "text-gray-400"}>
                {totalLength} / 80 Minimum Characters
              </span>
              {totalLength >= 80 ? (
                <span className="text-emerald-400 flex items-center gap-1">
                  <Check className="w-3 h-3" /> Rubric Satisfied
                </span>
              ) : (
                <span className="text-amber-400">Needs {80 - totalLength} more chars</span>
              )}
            </div>

            <button
              type="submit"
              disabled={isLoading || !isSatisfied}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-horizon-violet to-horizon-indigo hover:from-purple-600 hover:to-indigo-600 disabled:opacity-40 disabled:cursor-not-allowed text-white text-xs font-semibold py-2.5 rounded-xl shadow-md transition-all active:scale-95"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Submit Review & Earn +10⚡</span>
                </>
              )}
            </button>
          </form>
        )}

      </div>
    </div>
  );
}

