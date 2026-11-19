/**
 * Privacy-Safe Client-Side Web Crypto Hashing
 * 
 * Computes standard SHA-256 digests in the browser using the native Web Crypto API.
 * Ensures zero raw email addresses or PII are ever sent to the backend server.
 */

export async function hashEmail(email: string): Promise<string> {
  const normalized = email.trim().toLowerCase();
  const encoder = new TextEncoder();
  const data = encoder.encode(normalized);
  const hashBuffer = await window.crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, "0")).join("");
  return hashHex;
}

export async function hashEmailList(rawInput: string): Promise<string[]> {
  // Split on commas, newlines, semicolons, and spaces
  const emails = rawInput
    .split(/[\r\n,;]+/)
    .map(e => e.trim().toLowerCase())
    .filter(e => e.includes("@") && e.includes("."));

  const uniqueEmails = Array.from(new Set(emails));
  const hashes = await Promise.all(uniqueEmails.map(email => hashEmail(email)));
  return hashes;
}
