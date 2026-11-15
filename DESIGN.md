# 🎨 UI/UX Design System: Obsidian Atelier

## 1. Design Philosophy & Aesthetic Foundation

**Obsidian Atelier** is an ultra-refined aesthetic created to rescue student engineering and research work from the generic "AI demo" visual ghetto. It fuses:
1. **The Infinite Depth of the Void Canvas (`#06070B`)**: Deepest black with subtle radial horizon gradients that draw the viewer's eye into the focal workspace.
2. **Editorial Paper Dossier Surfaces (`#F8F9FA` / `#FFFFFF`)**: Crisp, light, tactile cards reminiscent of high-end architectural monographs and scientific journals, providing maximum legibility for technical breakdowns.
3. **Luminous Horizon Accents (`#6366F1` Indigo to `#A855F7` Violet)**: A signature specular top glow inspired by HorizonX AI, signaling future-forward computational power.
4. **Kinetic Choreography**: Micro-interactions, spring transitions, and 3-card fan-out stages driven by `motion/react` with low latency.

---

## 2. Color Palette & Specular Token System

### 2.1 Core Palette

| Token Name | Hex Code | Purpose & Application |
| :--- | :--- | :--- |
| `void-black` | `#06070B` | Primary global background; immersive viewport canvas. |
| `void-card` | `#0E1017` | Secondary dark containers, command docks, toolbars. |
| `editorial-paper` | `#F8F9FA` | The foreground Proof-of-Work Dossier card background. |
| `editorial-ink` | `#111827` | Primary high-contrast text on editorial paper surfaces. |
| `horizon-indigo` | `#6366F1` | Primary brand accent; active focus rings; terminal glows. |
| `horizon-violet` | `#A855F7` | Secondary radial light wash; credit badge highlights. |
| `emerald-verified` | `#10B981` | Verified Artifact badge; 200 OK external link checks. |
| `warning-amber` | `#F59E0B` | Urgent deadline tickers (<72h remaining). |
| `border-glass` | `rgba(255, 255, 255, 0.08)` | Specular 1px borders for dark glassmorphic containers. |

---

## 3. Typography Hierarchy

- **Display & Monograph Headings**: *Newsreader / Playfair / Editorial Serif* & *Plus Jakarta Sans*
- **Interface & Metrics Body**: *Plus Jakarta Sans* / *Inter*
- **Code, Hashes, & Tech Stacks**: *JetBrains Mono* / *Geist Mono*

```css
/* Typography Scale */
h1.hero-display    { font-size: 3.75rem; line-height: 1.1; font-weight: 800; letter-spacing: -0.03em; }
h2.dossier-title   { font-size: 2.25rem; line-height: 1.2; font-family: serif; font-weight: 700; }
h3.section-header  { font-size: 1.25rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
p.body-paper       { font-size: 1.00rem; line-height: 1.65; color: #374151; }
span.badge-code    { font-family: 'JetBrains Mono', monospace; font-size: 0.8125rem; font-weight: 500; }
```

---

## 4. The 5 Core Workspace Screens

### 4.1 Screen 0: Landing Page (Luminous Horizon & Omni-Command Dock)
- **Top Horizon Arc**: A centered radial gradient `radial-gradient(ellipse at 50% -20%, rgba(99, 102, 241, 0.3) 0%, rgba(6, 7, 11, 0) 70%)`.
- **Omni-Command Dock (`⌘K`)**: A floating central input pill supporting instant drag-and-drop of PDFs, pasting of GitHub links, or 1-tap live presets.
- **3-Card Kinetic Fan-Out**: Shows 3 publication-ready sample dossiers fanning out dynamically on scroll:
  - Card 1: *Autonomous Micro-Grid Orchestrator* (Tech/Engineering)
  - Card 2: *DeFi Liquidity Risk Sentinel* (Finance/Business)
  - Card 3: *CRISPR Off-Target Epigenetic Predictor* (Biotech/Design)
- **Interactive Scrollytelling Bento Grid**: Highlights live event radar crawling, zero-PII matching, and automated PR generation.

### 4.2 Screen 1: Dossier Workspace (65/35 Split)
- **Left Column (65% Width) — The Editorial Paper Dossier**:
  - Rendered on crisp `#F8F9FA` textured paper with clean typography.
  - Header: Verified Artifact emerald badge with live link validation status.
  - Technical Breakdown: Problem, Architecture, Solution, Tech Stack tags, and Key Quantitative Metrics.
  - Action Bar: "Export PDF", "Copy Dossier URL", "Open in PR Studio", "Unlock Peer Review".
- **Right Column (35% Width) — Idea Radar & Ecosystem Intelligence**:
  - **Whitespace Analysis**: Identified technical and market gaps extracted by the Trend Scout.
  - **Top Ecosystem Voices**: Leading figures, researchers, or founders to tag or engage with.
  - **Missing Role Recommender**: Intelligent suggestions for co-founders or team contributors with an invite button.

### 4.3 Screen 2: 3-Column PR Studio
- **Column 1: Playbook & Voice Configurator**:
  - Select Playbook: `LinkedIn Viral Hook`, `Instagram Reel Script`, `Investor/Recruiter Cold Pitch`.
  - Tone Slider: `Academic Rigor` $\leftrightarrow$ `High Octane Launch` $\leftrightarrow$ `Executive Brevity`.
  - Audience Selector: Peer builders, Angel Investors, Engineering Leads, Campus Recruiters.
- **Column 2: Live Copy Generator**:
  - Real-time markdown copy generated from the underlying dossier and selected playbook.
  - 1-Click Copy and character count monitors.
- **Column 3: 1200×630 Launch Card & Boost Studio**:
  - Live preview of the high-res OpenGraph launch card.
  - Cloudflare R2 image link generator.
  - **Visibility Credits Loop**: "Boost Dossier on Campus Feed" (`-20⚡`) or "Review 2 Peer Dossiers" (`+10⚡` each).

### 4.4 Screen 3: Daily & Weekly Event Radar
- **Persona Mode Switcher**: Pills for `Tech & AI`, `Policy & Law`, `Business & Finance`, `Design & Biotech`.
- **Urgent <72h Ticker**: Amber alert strip highlighting imminent hackathon and grant registration deadlines.
- **Strongest Pick Hero Card**: The algorithmically scored #1 highest-relevance opportunity for the user's active dossier.
  - Expandable **Networking Plan Drawer**: Pre-written icebreakers, target judges/speakers, and custom pitch angles.
  - **1-Click .ics Calendar Export**: Instantly downloads an RFC 5545 `.ics` file for Google/Apple Calendar.
  - **"Tailor Pitch" Button**: Passes opportunity requirements directly into the PR Studio to customize the application pitch.

### 4.5 Screen 4: SSR Public Dossier (`/p/[slug]`)
- Fully server-rendered for instant SEO and lightning-fast crawler indexing.
- Dynamic OpenGraph image injection: `<meta property="og:image" content="{r2_card_url}" />`.
- Clean "Fork / Inquire / Collaborate" call to actions for visiting recruiters and collaborators.

---

## 5. Micro-Interactions & Motion Choreography

All interactive states utilize spring physics rather than linear eases to feel responsive and physical:

```typescript
// Motion token specification
export const springTransition = {
  type: "spring",
  stiffness: 380,
  damping: 30,
};

export const fanOutVariants = {
  idle: { rotate: 0, y: 0, scale: 1 },
  leftFan: { rotate: -6, x: -40, y: 15, scale: 0.96 },
  centerFan: { rotate: 0, x: 0, y: 0, scale: 1.02, zIndex: 10 },
  rightFan: { rotate: 6, x: 40, y: 15, scale: 0.96 },
};
```

---

## 6. Accessibility & Responsiveness

- **High Contrast**: Editorial Paper cards strictly adhere to WCAG AAA contrast ratio ($> 7:1$) for dark text on light paper.
- **Keyboard Navigation**: The Omni-Command Dock can be opened from anywhere via `⌘K` or `Ctrl+K`. Tab indexing and Escape listeners are standardized across all drawers and modals.
- **Mobile Graceful Degradation**: On mobile screens ($< 768\text{px}$), the 65/35 workspace and 3-column studio collapse cleanly into sliding tab views with sticky bottom navigation.

