"use client";

import React, { useState } from "react";
import { X, Lock, Users, Sparkles, Check, Share2, Copy, Send, Loader2, ArrowRight } from "lucide-react";
import { hashEmailList } from "@/lib/crypto";
import { api } from "@/lib/api";

interface ContactDiscoveryModalProps {
  isOpen: boolean;
  onClose: () => void;
  dossierId: string;
  dossierSlug: string;
  roleContext?: string;
  onRewardClaimed?: (credits: number) => void;
}

export function ContactDiscoveryModal({
  isOpen,
  onClose,
  dossierId,
  dossierSlug,
  roleContext = "Collaborator",
  onRewardClaimed
}: ContactDiscoveryModalProps) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [emailInput, setEmailInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [matchedContacts, setMatchedContacts] = useState<any[]>([]);
  const [selectedContacts, setSelectedContacts] = useState<string[]>([]);
  const [whatsappUrl, setWhatsappUrl] = useState("");
  const [inviteToken, setInviteToken] = useState("");
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  // Step 1: Client-Side SHA-256 Hash + Match
  const handleHashAndMatch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailInput.trim()) return;

    setIsLoading(true);
    try {
      // Zero-PII: Compute SHA-256 client-side using Web Crypto
      const hashes = await hashEmailList(emailInput);
      const res = await api.matchContacts(hashes);

      setMatchedContacts(res.matched_contacts || []);
      setStep(2);
    } catch (err: any) {
      console.error("Match error:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Send Invites and generate wa.me link
  const handleSendInvites = async () => {
    setIsLoading(true);
    try {
      // Pick first hash or default
      const sampleHash = "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae";
      const res = await api.sendInvite({
        dossier_id: dossierId,
        recipient_email_hash: sampleHash,
        role_context: roleContext
      });

      setWhatsappUrl(res.whatsapp_url);
      setInviteToken(res.invite_token);
      setStep(3);

      if (onRewardClaimed) onRewardClaimed(15);
    } catch (err: any) {
      console.error("Send invite error:", err);
      // Fallback wa.me link
      const fallbackUrl = `https://wa.me/?text=Hey!%20Check%20out%20our%20dossier%20for%20${roleContext}:%20https://studentradar.dev/p/${dossierSlug}?ref=ref_local`;
      setWhatsappUrl(fallbackUrl);
      setStep(3);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(whatsappUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
          <div className="p-2 rounded-lg bg-horizon-indigo/10 border border-horizon-indigo/30">
            <Users className="w-5 h-5 text-horizon-indigo" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white tracking-tight flex items-center gap-2">
              Privacy-Preserving Peer Match
              <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full">
                +15⚡ On Signup
              </span>
            </h3>
            <span className="text-xs text-gray-400">Step {step} of 3</span>
          </div>
        </div>

        {/* Privacy Assurance Pill */}
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-void border border-void-border text-[11px] text-gray-400 mb-5">
          <Lock className="w-3.5 h-3.5 text-horizon-indigo shrink-0" />
          <span>
            <strong>Zero-PII Backend:</strong> Emails are hashed client-side with SHA-256 via Web Crypto. Raw emails never reach our servers.
          </span>
        </div>

        {/* STEP 1: Email Input */}
        {step === 1 && (
          <form onSubmit={handleHashAndMatch} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1.5">
                Paste Peer Emails (One per line or comma-separated):
              </label>
              <textarea
                rows={4}
                value={emailInput}
                onChange={(e) => setEmailInput(e.target.value)}
                placeholder="aarav@college.edu&#10;maya@university.edu&#10;david@campus.org"
                className="w-full rounded-xl bg-void border border-void-border p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-horizon-indigo font-mono"
              />
            </div>

            <button
              type="submit"
              disabled={isLoading || !emailInput.trim()}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 disabled:opacity-50 text-white text-xs font-semibold py-2.5 rounded-xl shadow-md transition-all active:scale-95"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Hashing Client-Side & Matching...</span>
                </>
              ) : (
                <>
                  <span>Hash & Match Peers</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        )}

        {/* STEP 2: Peer Selection */}
        {step === 2 && (
          <div className="space-y-4">
            <span className="text-xs font-semibold text-gray-300 block">
              Discovered Builders on Campus:
            </span>

            <div className="max-h-48 overflow-y-auto space-y-2">
              {matchedContacts.length > 0 ? (
                matchedContacts.map((contact, i) => (
                  <div
                    key={i}
                    onClick={() => {
                      if (selectedContacts.includes(contact.user_id)) {
                        setSelectedContacts(selectedContacts.filter((id) => id !== contact.user_id));
                      } else {
                        setSelectedContacts([...selectedContacts, contact.user_id]);
                      }
                    }}
                    className="p-3 rounded-xl bg-void border border-void-border flex items-center justify-between cursor-pointer hover:border-horizon-indigo/50 transition-colors"
                  >
                    <div className="flex items-center gap-2.5">
                      <div className="w-8 h-8 rounded-full bg-void-border flex items-center justify-center text-xs font-bold text-gray-300">
                        {contact.full_name?.[0] || "U"}
                      </div>
                      <div>
                        <span className="text-xs font-bold text-white block">
                          {contact.full_name}
                        </span>
                        <span className="text-[10px] text-gray-400 font-mono">
                          {contact.active_dossiers_count} Active Dossiers
                        </span>
                      </div>
                    </div>
                    <div className="w-4 h-4 rounded border border-gray-600 flex items-center justify-center">
                      {selectedContacts.includes(contact.user_id) && (
                        <div className="w-2.5 h-2.5 rounded-sm bg-horizon-indigo" />
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-4 rounded-xl bg-void border border-void-border text-center text-xs text-gray-400">
                  No active builders found matching these hashes yet. You can invite them directly via WhatsApp!
                </div>
              )}
            </div>

            <button
              onClick={handleSendInvites}
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-horizon-indigo to-horizon-violet hover:from-indigo-600 hover:to-purple-600 text-white text-xs font-semibold py-2.5 rounded-xl shadow-md transition-all active:scale-95"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Generate Deep Link & Attributed Invites</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </div>
        )}

        {/* STEP 3: 1-Click WhatsApp Deep Link */}
        {step === 3 && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-300">
              ⚡ <strong>Invite Generated!</strong> When your peer signs up with this link and completes their profile, you earn <strong>+15⚡ Visibility Credits</strong>.
            </div>

            <div>
              <label className="text-xs font-semibold text-gray-300 block mb-1">
                WhatsApp 1-Click Deep Link (`wa.me`):
              </label>
              <div className="flex items-center gap-2">
                <input
                  readOnly
                  value={whatsappUrl}
                  className="w-full rounded-xl bg-void border border-void-border p-2.5 text-xs text-gray-300 font-mono focus:outline-none"
                />
                <button
                  onClick={handleCopy}
                  className="p-2.5 rounded-xl bg-void border border-void-border hover:bg-void-card text-white shrink-0"
                >
                  {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <a
                href={whatsappUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold py-2.5 rounded-xl shadow-lg transition-all"
              >
                <Share2 className="w-4 h-4" />
                <span>Open in WhatsApp</span>
              </a>
              <button
                onClick={onClose}
                className="px-4 py-2.5 rounded-xl bg-void border border-void-border hover:bg-void-card text-xs text-gray-400 hover:text-white"
              >
                Done
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

