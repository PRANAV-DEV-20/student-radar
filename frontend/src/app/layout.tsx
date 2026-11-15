import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Student Radar // Proof-of-Work Dossiers & Opportunity Radar",
  description: "Transform raw ideas, GitHub repositories, and research PDFs into verified Proof-of-Work Dossiers with automated PR playbooks and high-signal event matchmaking.",
  openGraph: {
    title: "Student Radar // Proof-of-Work Dossiers",
    description: "Single-player utility first, multiplayer discovery second. Turn student builds into publication-grade dossiers.",
    siteName: "Student Radar",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-void text-white antialiased selection:bg-horizon-indigo selection:text-white">
        {children}
      </body>
    </html>
  );
}

