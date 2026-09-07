# Product Requirements Document (PRD)
# Nigehban — Pakistan's AI-Powered Fact-Check, Scam-Detection & Deepfake-Verification Portal

**Document Owner:** [Your Name / Team Name]
**Status:** Draft v1.0 — Hackathon Submission
**Last Updated:** August 26, 2026
**Category:** Civic Tech / Trust & Safety / Applied AI

---

## 1. Executive Summary

Nigehban ("guardian" / "watchman" in Urdu) is an AI-powered web portal built for Pakistan that fights three interconnected forms of digital harm in one place: **fake news, scams, and deepfakes**. It combines a live, auto-updating fact-check newsroom feed, a searchable and crowd-sourced scam database with instant message/screenshot verification, and a media-authenticity tool for detecting manipulated images and videos — all powered by a coordinated multi-agent AI pipeline. A public "what's spreading right now" dashboard gives the whole country situational awareness in real time, and a lightweight WhatsApp bot extends access to users who prefer messaging over browsing, since WhatsApp is Pakistan's dominant communication channel. The web portal is the primary product; WhatsApp is a companion access point.

The core insight: Pakistan currently has no single, independent, always-on, AI-native platform that unifies fact-checking, scam-reporting, and deepfake detection. Existing efforts (e.g., individual fact-checking desks, bank scam-alert pages, ad-hoc Twitter/X threads) are fragmented, slow, manual, and not built for the scale or speed at which misinformation and scams spread on WhatsApp, Facebook, and TikTok in Pakistan.

---

## 2. Problem Statement

**The problem:** Pakistani internet users — over 130 million as of 2026 — are exposed daily to a high volume of unverified news, financial scams (fake job offers, fraudulent investment schemes, SMS/WhatsApp phishing, fake government schemes), and increasingly convincing AI-generated deepfakes (political figures, celebrities, fabricated "leaked" audio/video). This content spreads fastest on closed platforms like WhatsApp, where it cannot be tracked, moderated, or fact-checked by anyone in real time.

**Who is affected:**
- **General public**, especially first-time internet users, older adults, and semi-urban/rural populations with lower digital literacy, who are the most common victims of scams and the most likely to share unverified news.
- **Journalists and newsrooms**, who need a fast, credible reference to verify claims before publishing.
- **Students and young professionals**, who are frequent targets of fake job/scholarship scams.
- **Small businesses and freelancers**, targeted by fraudulent payment and investment schemes.
- **Civil society / election-integrity and public-health stakeholders**, who need visibility into what disinformation narratives are trending, especially around elections, floods, and health emergencies.

**Cost of not solving it:**
- Direct **financial loss** to individuals from scams (fraudulent investment schemes and job scams alone are estimated to cost Pakistani citizens billions of rupees annually).
- **Erosion of public trust** in media, institutions, and digital content generally.
- **Real-world harm**: health misinformation (fake cures, anti-vaccine content), panic during disasters (fake flood/earthquake warnings), and communal or political tension fueled by fabricated content.
- **Reputational damage** to individuals and public figures targeted by deepfakes with no fast way to prove a video/audio clip is fabricated.
- Existing fact-checking in Pakistan is manual, slow (hours to days), and produced by a handful of small teams — it cannot keep pace with algorithmically-amplified misinformation.

**Evidence base (hackathon-stage):** Grounded in observable patterns — high WhatsApp forward volume in Pakistan, repeated bank/SBP scam alert advisories, recurring fake-news cycles around elections and natural disasters, and the global rise of deepfake incidents — rather than a formal user research study (out of scope for the hackathon timeline; flagged as an open question for post-hackathon validation).

---

## 3. Goals & Objectives

### Product Goals (User-Facing)
1. **G1 — Speed to answer:** A user should be able to check any suspicious message, claim, image, or video and get a verdict in under 60 seconds.
2. **G2 — One-stop coverage:** Cover all three major harm categories (fake news, scams, deepfakes) in a single product, eliminating the need to search multiple sources.
3. **G3 — Accessibility:** Make verification usable by people with low digital literacy via WhatsApp, Urdu-language support, and a simple screenshot/paste-and-check flow.
4. **G4 — Situational awareness:** Give the public and journalists a real-time view of what misinformation/scam narratives are currently trending in Pakistan.

### Business/Hackathon Goals
5. **G5 — Demonstrate a working multi-agent AI pipeline** that meaningfully improves verification quality/speed versus a single-LLM-call baseline (core technical differentiator for judging).
6. **G6 — Ship a working, demoable end-to-end product** within the hackathon timeframe: live feed + scam checker + deepfake checker + dashboard, with WhatsApp as a bonus integration.
7. **G7 — Position for post-hackathon viability**: architecture and data model should not require a rewrite to become a real, funded, or incubated product (e.g., candidate for a civic-tech grant, media partnership, or accelerator).

### Success looks like (at demo time)
- A judge can paste a real trending WhatsApp forward or screenshot and get a credible, sourced verdict.
- A judge can upload a real or AI-generated image/video and get a plausible authenticity score with an explanation.
- The public dashboard visibly updates/reflects "trending" items pulled from real or seeded data.
- The WhatsApp bot responds to a text/image query end-to-end, live, during the demo.

---

## 4. Non-Goals (Out of Scope for v1 / Hackathon)

1. **Not a general-purpose chatbot.** Nigehban will not answer unrelated queries (weather, homework, etc.) — scope is strictly fact-checking, scam-verification, and media authenticity. *Rationale: keeps the AI pipeline focused and prevents scope creep/hallucination risk on unrelated topics.*
2. **Not a legal or law-enforcement reporting tool.** Users cannot file a formal police/FIA complaint through Nigehban in v1; we may link out to official channels (e.g., FIA Cyber Crime Wing). *Rationale: legal integration requires partnerships/compliance beyond hackathon scope.*
3. **Not a content moderation or takedown service.** Nigehban does not report, flag, or request removal of content from Facebook/WhatsApp/TikTok. *Rationale: no platform API access/partnership in v1; verdicts are informational only.*
4. **Not a forensic-grade deepfake detector.** The media authenticity tool provides a probabilistic confidence score and explanation, not a court-admissible forensic certification. *Rationale: forensic-grade detection requires specialized models/hardware and legal chain-of-custody processes beyond hackathon scope.*
5. **Not multi-country.** v1 is Pakistan-specific (Urdu/English, PKR currency scams, local news sources, local scam patterns like SBP/FIA impersonation). *Rationale: focus increases relevance and demo credibility; internationalization is a future consideration.*
6. **Not real-time video-call deepfake detection** (e.g., live Zoom/WhatsApp call verification). *Rationale: real-time streaming analysis is a significantly harder, separate engineering problem.*
7. **No native mobile app in v1.** Web portal (mobile-responsive) + WhatsApp bot only. *Rationale: limited hackathon time; web + WhatsApp covers the accessibility goal without app-store overhead.*

---

## 5. Target Users & Personas

### Persona 1 — "Ayesha," the Everyday Sharer (Primary)
- 34, works in retail admin, Lahore. Active in 5+ family/friend WhatsApp groups.
- Receives 10+ forwarded messages/videos daily — health tips, "breaking news," job offers.
- Not digitally naive, but doesn't have time to verify before sharing/acting.
- **Need:** A fast, trustworthy "is this true / is this a scam?" check she can do from her phone in seconds — ideally without leaving WhatsApp.

### Persona 2 — "Bilal," the Job-Seeking Graduate (Primary — Scam Victim Risk)
- 23, recent graduate, Multan. Actively applying for jobs online, sees frequent "work from home, earn 80,000/month" ads and investment scheme messages.
- **Need:** A quick way to check if a job offer, WhatsApp recruiter, or investment scheme is a known scam pattern before sending money/documents.

### Persona 3 — "Sana," the Junior Journalist (Secondary — Power User)
- 27, works at a digital news outlet, Karachi. Needs to verify claims and viral clips quickly under deadline pressure.
- **Need:** A credible, source-linked verification tool she can cite, plus a dashboard of currently-trending claims to spot stories early.

### Persona 4 — "Uncle Tariq," the Low-Digital-Literacy User (Primary — Vulnerability Focus)
- 58, small shopkeeper, semi-urban Punjab. Uses WhatsApp daily but is not comfortable navigating websites or reading English.
- **Need:** Simplest possible interaction — send a message/photo to a WhatsApp number, get a clear Urdu-language answer ("Yeh scam hai" / "Yeh sach hai").

### Persona 5 — "Dr. Fatima," the Civil Society / Researcher (Secondary)
- 40, works at an NGO focused on digital rights/election integrity.
- **Need:** Aggregate, trend-level visibility into what's spreading (dashboard), not just one-off checks.

---

## 6. User Stories

### Fact-Check Feed
- As Ayesha, I want to browse a live feed of recently fact-checked claims so that I can see if something I received has already been verified.
- As Ayesha, I want each feed item to show a clear verdict (True / False / Misleading / Unverified) with a short explanation, so I don't have to read a long article to get the gist.
- As Sana, I want to filter the feed by category (politics, health, disaster, celebrity, finance) so I can find relevant claims quickly.
- As Sana, I want each fact-check to link to its original sources so I can cite it credibly.
- As a returning user, I want to see when a fact-check was last updated, so I know if new evidence has emerged.

### Scam Database & Checker
- As Bilal, I want to paste a suspicious WhatsApp message or job offer text and get an instant "scam risk" verdict, so I know whether to trust it.
- As Bilal, I want to upload a screenshot of a message and have the tool extract and analyze the text (OCR), so I don't have to retype anything.
- As Ayesha, I want to search a database of known scams by keyword (e.g., "SBP loan," "OLX advance payment") to see if a pattern has already been reported.
- As Uncle Tariq, I want the scam verdict explained in simple Urdu with a plain-language reason ("Yeh number sarkari nahi hai" / "This number does not belong to a government agency"), so I understand why.
- As any user, I want to report a new scam I encountered so the database grows and helps others (crowd-sourced reporting).
- As Bilal, I want to see the phone number/sender ID cross-checked against a known-scammer registry, so I get an extra signal beyond the message text.

### Media Authenticity Tool (Deepfake Detection)
- As Sana, I want to upload an image or video clip and get an authenticity confidence score (e.g., "78% likely AI-generated/manipulated") with a plain explanation of what triggered that score.
- As Dr. Fatima, I want to see which specific signals were used (face-swap artifacts, audio-video sync mismatch, metadata inconsistency, known reverse-image match) so I can judge the credibility of the result myself.
- As Ayesha, I want to just paste a video link (e.g., a YouTube/Twitter URL) instead of downloading and uploading the file, for convenience.
- As any user, I want a clear disclaimer that this is a probabilistic tool, not 100% certain proof, so I don't over-trust the result.

### Public Dashboard
- As Dr. Fatima, I want to see a real-time (or near-real-time) ranked list of "what's trending" across fake news, scams, and deepfakes, so I can spot emerging narratives.
- As a journalist, I want to see a trend graph of how a specific claim's spread has grown over the last 24-48 hours.
- As any visitor, I want a simple map/breakdown of which categories (health, politics, finance scams) are most active this week.

### WhatsApp Bot
- As Uncle Tariq, I want to send a text or photo to a WhatsApp number and receive a verdict within the chat, without ever opening a browser.
- As Ayesha, I want the bot to reply in my preferred language (Urdu or English).
- As a new user, I want the bot to explain what it can do (fact-check, scam-check, media-check) when I first message it.

### Trust & Transparency (Cross-Cutting)
- As any user, I want to see the confidence level and sources behind every verdict, so I can judge how much to trust it.
- As any user, I want a clear "how this works" / methodology page, so I understand this isn't a black box.
- As a skeptical user, I want a way to flag a verdict I disagree with, so there's a feedback loop and human oversight.

---

## 7. Features & Requirements

Prioritized using MoSCoW (P0 = Must-Have for hackathon demo, P1 = Nice-to-Have/fast-follow, P2 = Future Consideration).

### 7.1 Live Fact-Check Feed (Newsroom Feed)

**P0 — Must-Have**
| Requirement | Acceptance Criteria |
|---|---|
| Auto-updating feed of fact-checked claims, newest first | Given the feed is open, when a new fact-check is processed by the pipeline, then it appears at the top of the feed within 2 minutes without a manual page refresh (polling or websocket). |
| Verdict labeling system: **True / False / Misleading / Unverified / Satire** | Given a claim has been processed, when displayed in the feed, then it shows exactly one verdict label with a distinct color/icon. |
| Claim card with: headline, verdict, 2-3 sentence explanation, source links, timestamp, category tag | Given a user clicks a feed card, when the detail view opens, then all fields above are visible along with the AI agent's reasoning summary. |
| Category filtering (Politics, Health, Finance/Scam, Disaster, Celebrity/Entertainment, Other) | Given a user selects a category filter, when applied, then only matching claims are shown. |
| Search bar across all fact-checked claims | Given a user enters a keyword, when they search, then matching claims (title/body) are returned ranked by relevance. |
| Bilingual UI (English/Urdu) with Urdu content for claims where relevant | Given a user switches language, when toggled, then UI labels and available claim translations update. |

**P1 — Nice-to-Have**
- "Trending now" badge on high-velocity claims.
- Related-claims clustering (group near-duplicate claims into one verified story).
- Email/WhatsApp subscription to daily digest of top fact-checks.
- Upvote/downvote or "was this helpful" feedback per card.

**P2 — Future**
- Personalized feed based on user's region/interests.
- Multi-language support beyond Urdu/English (Pashto, Sindhi, Punjabi).
- Browser extension that flags claims in real time while browsing social media.

### 7.2 Scam Database & Instant Checker

**P0 — Must-Have**
| Requirement | Acceptance Criteria |
|---|---|
| Text-paste scam checker: user pastes message text, receives risk verdict | Given a user pastes text and submits, when the AI pipeline completes, then a verdict (Likely Scam / Likely Safe / Needs Caution) with a confidence score and explanation is returned within 15 seconds. |
| Screenshot upload with OCR extraction | Given a user uploads an image containing text, when submitted, then OCR extracts the text and the same scam-analysis pipeline runs on it, with the extracted text shown to the user for confirmation. |
| Searchable scam database (by keyword, scam type, sender number/ID) | Given a user searches a term, when results return, then matching previously-logged scam reports are listed with date and pattern description. |
| Scam categorization: Job Scam, Investment/Ponzi, Phishing (bank/SBP impersonation), Lottery/Prize, Romance Scam, Fake Government Scheme, OLX/Marketplace Scam, Other | Given a scam is logged (by AI or user report), when categorized, then it is tagged with one or more of the above types. |
| User-submitted scam reporting form (text, screenshot, sender number, description) | Given a user submits a report, when submitted, then it enters a review queue and, once processed by the AI pipeline, is added to the database. |
| Plain-language explanation output (Urdu + English) | Given any verdict is generated, when displayed, then it includes a jargon-free explanation of *why* (e.g., "Real banks never ask for your PIN over WhatsApp"). |

**P1 — Nice-to-Have**
- Known-scammer phone number / bank account cross-reference list (crowd-sourced + curated).
- "Scam of the week" spotlight on homepage.
- Risk score breakdown showing specific red flags detected (urgency language, request for money/OTP, suspicious link, impersonation claim).
- Shareable "scam alert card" (image) users can forward back into WhatsApp groups to warn others.

**P2 — Future**
- Browser/SMS-level real-time scam interception.
- Integration with banks' official fraud-reporting APIs.
- Community moderator roles for verifying user-submitted reports.

### 7.3 Media Authenticity Tool (Deepfake/Manipulation Detection)

**P0 — Must-Have**
| Requirement | Acceptance Criteria |
|---|---|
| Image upload and analysis | Given a user uploads a JPG/PNG, when analyzed, then an authenticity confidence score (0-100%, "Likely Authentic" to "Likely Manipulated") is returned with contributing factors listed. |
| Video upload and analysis (short clips) | Given a user uploads an MP4 under a defined size/duration limit (e.g., ≤60 seconds / 50MB for hackathon scope), when analyzed, then a similar confidence score and explanation is returned. |
| Explanation of signals used | Given a result is returned, when displayed, then it lists which detection signals contributed (e.g., facial artifact detection, metadata check, reverse image/video search match, audio-visual sync analysis) and their individual sub-scores. |
| Clear uncertainty disclaimer | Given any result is shown, when displayed, then a persistent disclaimer states this is a probabilistic AI assessment, not definitive proof. |
| Reverse-image/video search cross-check | Given a media file is submitted, when analyzed, then the system checks whether it matches known/previously fact-checked or indexed media and surfaces that match if found. |

**P1 — Nice-to-Have**
- URL-based submission (paste a YouTube/Twitter/Facebook video link instead of uploading).
- Audio-only deepfake (voice cloning) detection.
- Side-by-side comparison with the original source media (if a match is found).
- Batch checking (multiple images at once).

**P2 — Future**
- Real-time live-stream/video-call authenticity checking.
- Browser extension for in-line social media deepfake flagging.
- Partnership-based forensic-grade certification for legal use cases.

### 7.4 Public "What's Spreading Now" Dashboard

**P0 — Must-Have**
| Requirement | Acceptance Criteria |
|---|---|
| Ranked "Top Trending" list across all three categories (fake news, scams, deepfakes) | Given the dashboard loads, when displayed, then it shows the top 10 currently-trending items ranked by a defined "spread score" (e.g., report volume + recency-weighted). |
| Category breakdown visualization (chart) | Given the dashboard loads, when displayed, then a chart shows the proportion/count of active items per category over the selected time window (24h / 7d / 30d). |
| Trend detail view with timeline | Given a user clicks a trending item, when opened, then a simple time-series shows how report/verification volume has changed. |
| Public, no-login-required access | Given any visitor accesses the dashboard URL, when loaded, then all data is viewable without authentication. |

**P1 — Nice-to-Have**
- Regional breakdown (if location data is available/inferable).
- Export/embed widget for journalists to embed the dashboard on their own sites.
- Weekly auto-generated summary report (PDF/shareable image).

**P2 — Future**
- Predictive "likely to trend next" signal using early-stage velocity detection.
- Public API for researchers/NGOs.

### 7.5 WhatsApp Bot (Companion Access Point)

**P0 — Must-Have**
| Requirement | Acceptance Criteria |
|---|---|
| Text message query support | Given a user sends a text message to the bot, when received, then the bot runs it through the scam/fact-check pipeline and replies with a verdict within 20 seconds. |
| Image message query support | Given a user sends an image, when received, then the bot runs OCR + media-authenticity analysis as applicable and replies with a verdict. |
| Onboarding/help message | Given a new user messages the bot for the first time, when received, then the bot replies with a short explanation of its three capabilities and example commands. |
| Language selection (Urdu/English) | Given a user requests a language change (e.g., types "Urdu"), when processed, then subsequent replies are in the selected language. |

**P1 — Nice-to-Have**
- Quick-reply buttons/menu (Meta WhatsApp Business API interactive messages).
- Daily/weekly digest opt-in of top trending fact-checks.
- Voice-note query support (transcribe then analyze).

**P2 — Future**
- Group-chat integration (bot can be added to a family/community group and proactively flag suspicious forwards).
- SMS fallback for users without WhatsApp/data.

---

## 8. Multi-Agent AI Pipeline — System Design

This is the technical core and primary differentiator of Nigehban. Rather than a single LLM call, verification runs through a coordinated pipeline of specialized agents, orchestrated by a controller.

### 8.1 Pipeline Overview

```
User Input (text / screenshot / image / video / URL)
        |
        v
[0] INTAKE AGENT — classifies input type & routes to correct sub-pipeline
        |
   -----------------------------------------------------
   |                     |                              |
   v                     v                              v
FACT-CHECK PATH     SCAM-CHECK PATH               MEDIA-AUTHENTICITY PATH
   |                     |                              |
[1] Claim Extraction  [1] OCR/Text Extraction        [1] Metadata Forensics Agent
    Agent               (if image)                       (EXIF, compression artifacts,
   |                     |                                encoding history)
[2] Evidence Retrieval [2] Pattern-Match Agent        [2] Visual Forensics Agent
    Agent (web search,   (compares against known         (face/edge artifact detection,
    news APIs, fact-      scam DB via embeddings)         GAN-fingerprint heuristics)
    check archive)       |                              |
   |                   [3] Risk Signal Agent          [3] Audio-Sync Agent (video only)
[3] Cross-Reference      (urgency language, money        (lip-sync mismatch, spectral
    Agent (compares       requests, impersonation,        anomalies in cloned voice)
    against known fact-    suspicious links/numbers)     |
    check databases)      |                            [4] Reverse-Search Agent
   |                   [4] Verdict Synthesis Agent        (matches against known media/
[4] Verdict Synthesis     |                                 previously-flagged content)
    Agent                                                  |
   |                                                     [5] Verdict Synthesis Agent
   -----------------------------------------------------
        |
        v
[FINAL] ORCHESTRATOR / JUDGE AGENT
   - Aggregates sub-verdicts + confidence scores
   - Applies consistency & safety checks (no unsupported claims, cites sources)
   - Produces final structured output: {verdict, confidence, explanation, sources, category, flags}
        |
        v
[STORAGE] → Database → Feed / Dashboard / API / WhatsApp response
```

### 8.2 Agent Descriptions

| Agent | Responsibility | Key Inputs | Key Outputs |
|---|---|---|---|
| **Intake Agent** | Detects input modality (text/image/video/URL) and language; routes to the correct sub-pipeline; performs basic content-safety screening | Raw user input | Input type, language, routing decision |
| **Claim Extraction Agent** | Pulls out the core factual claim(s) from a longer message/article, normalizes phrasing | Raw text | Structured claim(s), entities, date/location references |
| **Evidence Retrieval Agent** | Searches the web, news APIs, and a curated fact-check archive (e.g., prior IFCN-affiliated fact-checks, Pakistani news outlets) for relevant evidence | Structured claim | Ranked list of candidate sources with excerpts |
| **Cross-Reference Agent** | Compares the claim against existing verified/debunked claims in the internal database to avoid duplicate work and catch recurring hoaxes | Claim + evidence | Match/no-match, prior verdict if found |
| **OCR/Text Extraction Agent** | Extracts text from screenshots using OCR, handles Urdu + English script | Image | Extracted text, confidence score |
| **Pattern-Match Agent** | Uses embedding similarity search against the scam database to find near-duplicate known scams | Message text | Similar known scams + similarity score |
| **Risk Signal Agent** | Rule + LLM-based detection of scam red flags: urgency/pressure language, requests for OTP/PIN/advance payment, impersonation of banks/government, suspicious/shortened links, mismatched sender identity | Message text, metadata | List of detected red flags with severity |
| **Metadata Forensics Agent** | Inspects file metadata (EXIF, encoding history, editing software signatures) for manipulation indicators | Image/video file | Metadata anomaly flags |
| **Visual Forensics Agent** | Applies deepfake-detection heuristics/models (facial landmark consistency, blending artifacts, GAN fingerprint patterns) | Image/video frames | Manipulation likelihood score, affected regions |
| **Audio-Sync Agent** | For video: checks lip-sync alignment and audio spectral characteristics for signs of voice cloning | Video/audio track | Sync mismatch score, voice-clone likelihood |
| **Reverse-Search Agent** | Checks if media matches previously indexed authentic or previously-flagged manipulated content | Image/video | Match results with source/context if found |
| **Verdict Synthesis Agent (per-path)** | Combines all signals within its path into a preliminary verdict + confidence + explanation draft | All prior agent outputs in path | Draft verdict object |
| **Orchestrator / Judge Agent** | Final quality-control layer: checks the draft verdict against source citations, ensures no unsupported claims, resolves conflicts between agents, formats final structured response, and applies a "cannot verify" fallback if confidence is too low | Draft verdict + sources | Final structured verdict (JSON) |

### 8.3 Why Multi-Agent (Design Rationale)
- **Specialization improves accuracy:** A single LLM call asked to "is this true and is it a scam and is this image fake" tends to produce shallow, unsupported answers. Splitting into specialized agents (retrieval vs. reasoning vs. forensic signal extraction) lets each step do one job well.
- **Grounding reduces hallucination:** The Evidence Retrieval and Reverse-Search agents force the pipeline to cite real, checkable sources rather than letting the model "guess" from parametric knowledge — critical for a trust product.
- **Auditability:** Because each agent's output is logged, a user (or judge) can inspect *why* a verdict was reached — supports the transparency goal (G-Trust).
- **Extensibility:** New detection capabilities (e.g., a new scam pattern type, a new deepfake technique) can be added as a new agent/tool without redesigning the whole system.
- **Fallback safety:** If evidence is insufficient, the Orchestrator agent is instructed to return "Unverified — Insufficient Evidence" rather than force a confident wrong answer. This is a hard safety requirement, not optional.

### 8.4 Orchestration Pattern
- **Pattern:** Controller/Orchestrator pattern (not fully autonomous agent-to-agent negotiation) — a central orchestrator calls each specialized agent as a tool/function in a defined sequence per path, then performs final synthesis. This is more reliable and debuggable for a hackathon timeline than an open-ended multi-agent conversation framework.
- **Suggested implementation approach:** Each "agent" is a distinct LLM call with a narrow system prompt and specific tools (web search, OCR, image-analysis model, vector DB lookup), coordinated by a lightweight orchestration script/framework (e.g., a simple Python state machine, or a framework such as LangGraph/CrewAI-style orchestration if time allows — framework choice is an implementation detail, not a fixed requirement).
- **Latency budget (target):**
  - Text/scam check: ≤ 15 seconds end-to-end
  - Image check (OCR + forensics): ≤ 20 seconds
  - Video check: ≤ 45 seconds (video is heavier; acceptable to show a "processing" state)
- **Confidence thresholding:** Final verdict includes a numeric confidence (0-100%). Below a defined threshold (e.g., 50%), the system defaults to "Unverified / Needs More Evidence" rather than a forced True/False call.

---

## 9. Technical Architecture

### 9.1 High-Level System Diagram (Description)

- **Frontend (Web Portal):** Responsive web app (desktop + mobile browser) — the primary interface.
- **WhatsApp Bot Layer:** Integrates via WhatsApp Business API (or a sandbox/unofficial API for hackathon demo purposes, e.g., Twilio WhatsApp Sandbox or Meta Cloud API), forwards user messages to the same backend pipeline as the web portal.
- **Backend API Layer:** REST/GraphQL API handling submissions, retrieving feed/dashboard data, and exposing pipeline results.
- **Multi-Agent AI Orchestration Layer:** As described in Section 8; calls out to LLM provider(s), OCR service, image/video forensic models, and search/retrieval tools.
- **Data Layer:**
  - Primary relational DB (claims, scams, media checks, users' submitted reports, verdicts).
  - Vector database (embeddings for semantic similarity search — scam pattern matching, duplicate claim detection).
  - Object storage (uploaded images/videos, with defined retention policy).
- **Background Workers / Job Queue:** For async processing of media analysis and web-scraping tasks so the UI isn't blocked.
- **Auto-Update / Ingestion Service:** Scheduled jobs that pull trending topics from news RSS feeds, X/Twitter trends (where accessible), and prior fact-check archives to proactively seed the live feed (rather than relying solely on user submissions) — this is what makes the feed feel like a "newsroom."
- **Public Dashboard Service:** Aggregation/analytics layer computing trending scores from submission volume + recency.
- **Admin/Moderation Panel:** Internal tool for the team to review flagged/low-confidence items, curate the scam database, and moderate user-submitted reports.

### 9.2 Suggested Tech Stack (Hackathon-Pragmatic)

| Layer | Suggested Technology | Notes |
|---|---|---|
| Frontend | React / Next.js, Tailwind CSS | Fast to build, good for a newsroom-style responsive UI |
| Backend API | Node.js (Express/Fastify) or Python (FastAPI) | FastAPI is a strong choice if the AI pipeline is Python-based, for shared codebase |
| AI Orchestration | Python-based orchestration (custom state machine or lightweight agent framework) | Keep it simple and debuggable given hackathon time constraints |
| LLM Provider | Claude (Anthropic API) for reasoning/synthesis agents | Use tool-calling for web search, OCR, and DB lookups |
| OCR | Tesseract OCR (open-source, supports Urdu) or a cloud OCR API | Needed for screenshot scam-checking |
| Web Search / Evidence Retrieval | Search API (e.g., Bing/Google Search API, or a news API) | Needed for grounding fact-check claims in real sources |
| Deepfake/Forensics Models | Open-source pretrained deepfake detection models (e.g., existing face-forgery detection models) + metadata/EXIF libraries | Full custom model training is out of scope for hackathon; use/fine-tune existing open models |
| Vector DB | Pinecone / Weaviate / pgvector (Postgres extension) | pgvector is simplest if already using Postgres |
| Primary Database | PostgreSQL | Relational integrity for claims/scams/users |
| Object Storage | AWS S3 / Cloudflare R2 / similar | For uploaded media |
| WhatsApp Integration | Meta WhatsApp Cloud API or Twilio WhatsApp Sandbox | Sandbox is faster to set up for a demo |
| Hosting | Vercel (frontend) + Railway/Render/Fly.io (backend) or a single cloud VM | Optimize for fast deployment during hackathon |
| Real-time Feed Updates | Polling (simplest) or WebSockets (Socket.io) if time allows | Polling is acceptable for hackathon MVP |

*(Note: Specific vendor choices are suggestions for hackathon speed, not hard requirements — team should pick based on familiarity and available credits/API keys.)*

### 9.3 Data Model (Core Entities — Simplified)

- **Claim**: id, title, body, category, verdict, confidence_score, explanation, sources[], language, created_at, updated_at, trend_score
- **ScamReport**: id, submitted_text, extracted_text (if OCR), scam_type, risk_verdict, confidence_score, red_flags[], sender_identifier (optional), reported_by (anonymous or user id), created_at
- **MediaCheck**: id, media_type (image/video), file_url, authenticity_score, signals[] (metadata/visual/audio/reverse-search results), verdict, created_at
- **AgentLog**: id, parent_check_id, agent_name, input_summary, output_summary, confidence, latency_ms, timestamp — *(for auditability/transparency and debugging)*
- **User (optional for v1)**: id, contact (WhatsApp number / email, optional), language_preference, submission_history
- **TrendSnapshot**: id, related_entity_id (claim/scam/media), timestamp, report_volume, spread_score — *(feeds the dashboard)*

### 9.4 API Endpoints (Illustrative)

- `POST /api/v1/factcheck/submit` — submit a claim/text/URL for fact-checking
- `POST /api/v1/scamcheck/submit` — submit text or screenshot for scam analysis
- `POST /api/v1/mediacheck/submit` — submit image/video/URL for authenticity analysis
- `GET /api/v1/feed?category=&page=` — paginated live fact-check feed
- `GET /api/v1/scams/search?q=` — search scam database
- `GET /api/v1/dashboard/trending?window=24h|7d|30d` — trending items for dashboard
- `GET /api/v1/checks/:id` — full detail + agent reasoning trail for a specific check
- `POST /api/v1/report` — user-submitted scam/claim report
- `POST /api/webhook/whatsapp` — inbound WhatsApp message webhook

---

## 10. UX / Design Principles

1. **Newsroom, not lab report.** The feed should feel like a credible news source (clear headlines, verdict badges, timestamps) — not a raw AI output dump.
2. **Verdict-first hierarchy.** The verdict (True/False/Scam/Safe/Manipulated) must be the most visually prominent element on any result — users skimming should get the answer in under 2 seconds of looking.
3. **Explain like a knowledgeable friend, not a legal disclaimer.** Explanations should be short, plain-language, and specific — avoid hedgy academic language.
4. **Bilingual by default.** Urdu is not an afterthought — critical flows (submitting a check, reading a verdict) must work fully in Urdu, including right-to-left considerations for Urdu script rendering.
5. **Low-bandwidth friendly.** Given variable internet quality across Pakistan, the portal should be lightweight (optimize image sizes, avoid heavy client bundles) and the WhatsApp bot should be the fallback for low-connectivity users.
6. **Trust signals everywhere.** Sources, confidence scores, and "how we got this answer" should always be one click away, never hidden.
7. **No dead ends.** If confidence is low, never just say "unclear" — always suggest a next step (e.g., "we couldn't verify this — here's how to check the sender yourself" or "submit more context").

---

## 11. Success Metrics

### For Hackathon Demo (Immediate)
| Metric | Target |
|---|---|
| End-to-end demo completion (submit → verdict) for all 3 core tools | 100% success, no crashes, live during demo |
| Fact-check feed populated with real/seeded items | ≥ 20 items across ≥ 4 categories at demo time |
| Scam database populated | ≥ 30 known scam patterns seeded pre-demo |
| Average response latency (text/scam check) | ≤ 15 seconds |
| WhatsApp bot live round-trip demo | At least 1 successful text query + 1 image query during live demo |
| Judge-perceived "multi-agent" transparency | Agent reasoning trail visible/explainable on request |

### Post-Hackathon / Product Success (Leading Indicators)
- **Adoption rate:** number of unique checks submitted per week (web + WhatsApp combined).
- **Verdict engagement rate:** % of users who click into a full explanation/sources view (not just see the badge).
- **WhatsApp activation rate:** % of web visitors who also try the WhatsApp bot.
- **Report contribution rate:** number of user-submitted scam reports per week (community engagement signal).
- **Feed freshness:** average time between a claim trending and it appearing fact-checked in the feed.

### Post-Hackathon / Product Success (Lagging Indicators)
- **Retention:** % of users who return to check something again within 30 days.
- **Trust/satisfaction:** qualitative feedback / survey NPS from users and journalist power-users.
- **Real-world impact signal:** anecdotal/reported cases of users avoiding a scam or correcting a shared claim because of Nigehban (collected via feedback form).
- **Media pickup:** number of journalists/outlets citing Nigehban's dashboard or fact-checks.
- **Accuracy audit results:** periodic manual audit of a sample of verdicts against expert/human fact-checker review (critical trust metric for a product like this).

---

## 12. Non-Functional Requirements

### 12.1 Accuracy & AI Safety
- The system must **never fabricate sources** — every "True/False" verdict must cite at least one retrievable source; if none is found, the verdict must default to "Unverified."
- The Orchestrator/Judge agent must apply a **confidence floor**: verdicts below a defined confidence threshold cannot be labeled definitively True/False.
- All AI-generated verdicts must be clearly labeled as **AI-assisted**, with a visible path for human review/correction (feedback/flag button).
- Sensitive categories (e.g., claims about specific religious or ethnic groups, claims that could incite violence) should route through additional caution/review logic rather than auto-publishing a confident verdict without human-in-the-loop review, especially in v1.

### 12.2 Privacy & Data Handling
- User-submitted content (screenshots, messages, media) may contain personal information (phone numbers, names, financial details). The system must:
  - Avoid publicly displaying personally identifiable information (PII) from submitted content in the public feed/dashboard without redaction.
  - Define a clear data retention policy for uploaded media (e.g., auto-delete raw uploads after N days, retain only derived analysis results).
  - Allow anonymous submission (no account required) for both web and WhatsApp.
- WhatsApp number (if used to interact with the bot) should be treated as sensitive data and not exposed publicly.

### 12.3 Security
- Input validation and sanitization on all submission endpoints (prevent injection via text/file uploads).
- Rate limiting on submission endpoints to prevent abuse/spam of the AI pipeline (cost control + reliability).
- File upload validation (type/size limits, malware scanning consideration for production).
- Secure handling of API keys (LLM provider, WhatsApp API, search API) via environment variables/secrets manager — never hard-coded.

### 12.4 Performance & Scalability
- Hackathon target: handle concurrent demo load (dozens of simultaneous requests) without failure.
- Architecture should not preclude horizontal scaling of the worker/agent layer post-hackathon (e.g., queue-based processing so spikes don't block the API).

### 12.5 Localization
- Full Urdu language support for UI and AI-generated explanations (not just English with Urdu labels).
- OCR must support Urdu script in addition to English.
- Consider Roman Urdu (Urdu written in Latin script, common in informal texting) as an input pattern the Risk Signal / Claim Extraction agents should handle.

### 12.6 Accessibility
- Web portal should meet basic accessibility standards (readable font sizes, sufficient color contrast for verdict badges, screen-reader-friendly labels).
- WhatsApp bot as the primary accessibility fallback for low-literacy/low-tech-comfort users.

---

## 13. Risks & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| AI gives a confidently wrong verdict (false positive/negative) | High — directly undermines trust, could cause real harm | Medium | Confidence thresholding + mandatory source citation + "Unverified" fallback + visible feedback/correction mechanism + post-launch human audit sampling |
| Deepfake detection models produce unreliable results on Pakistani-context media (different lighting, video compression common on WhatsApp) | Medium-High | Medium-High | Clearly communicate confidence + limitations; use ensemble of multiple signals (not just one model) so no single weak model dominates the verdict; flag heavily-compressed/low-quality media as "lower confidence" explicitly |
| Legal/political sensitivity of fact-checking political claims in Pakistan | High | Medium | Focus initial scope/demo on scams and clearly factual/health/disaster claims; apply extra human-review caution on political content; maintain transparent, source-linked methodology to defend against bias accusations |
| WhatsApp Business API access/approval delays | Medium — could block bot demo | Medium | Use sandbox/testing mode (e.g., Twilio WhatsApp Sandbox) for hackathon demo; treat full Business API approval as a post-hackathon task |
| Scam database seeded with insufficient/inaccurate data for demo | Medium | Medium | Manually curate a seed set of well-known, verifiable Pakistani scam patterns (SBP/bank impersonation, common OLX scams, fake job schemes) before demo day |
| Cost of LLM API calls at scale (multi-agent = multiple calls per check) | Medium (post-hackathon concern) | Medium | Use smaller/cheaper models for narrow sub-tasks (e.g., OCR cleanup, red-flag classification) and reserve larger models for final synthesis/reasoning; cache/deduplicate repeated claim checks |
| Users submit sensitive personal data (financial details, ID numbers) in screenshots | Medium-High (privacy) | Medium | Redact/mask detected PII patterns before storing or displaying publicly; clear data retention/deletion policy |
| Low initial trust — "why should I believe an AI over what my group says" | Medium | Medium | Radical transparency (show sources + reasoning), partner with/reference existing credible fact-checkers where possible, plain-language explanations |
| Misuse: bad actors submitting real content to test/evade the system, or spamming the pipeline | Low-Medium | Medium | Rate limiting, abuse monitoring, CAPTCHA on high-volume public endpoints if needed |

---

## 14. Open Questions

| Question | Owner | Blocking? |
|---|---|---|
| Which LLM/model provider and budget/credits are available for the hackathon (affects how many agents can realistically be run per check)? | Engineering | Yes — affects pipeline design |
| Do we have access to a WhatsApp Business API sandbox, or should we use Twilio's sandbox for the demo? | Engineering | Yes — affects bot implementation timeline |
| What is the realistic time budget to source/fine-tune a deepfake detection model vs. using an off-the-shelf open-source model as-is? | Engineering | Yes — affects Media Authenticity Tool scope |
| Should political claim fact-checking be included in the live demo, given sensitivity, or should the demo focus on health/scam/disaster claims to reduce risk? | Product/Team | Yes — affects seed data and demo script |
| Is there a real or mock dataset of Pakistani scam reports we can seed the database with before demo day, or do we need to hand-curate one? | Product/Team | Yes — affects Scam Database credibility at demo |
| What is the data retention/deletion policy for uploaded media — is this even needed for a hackathon prototype, or can it be deferred? | Product/Legal (post-hackathon) | No — can defer, but should be documented |
| Will the team pursue post-hackathon continuation (grant funding, incubation, open-source release)? This affects how much "production-readiness" (auth, admin moderation tools) to build now vs. defer. | Team | No — but affects prioritization judgment calls |
| Should the dashboard use real scraped/live data sources (news RSS, social trend signals) or seeded/simulated data for the hackathon demo, given time constraints and API access? | Engineering | Yes — affects "auto-updating" claim credibility at demo |

---

## 15. Timeline & Phasing

### Phase 0 — Pre-Hackathon Prep (if any prep time exists)
- Finalize tech stack and provision API keys/credits (LLM provider, search API, WhatsApp sandbox, OCR).
- Hand-curate seed dataset: ~20-30 known Pakistani scam patterns, ~15-20 example fact-checkable claims (mix of true/false/misleading), a handful of test images/videos (including at least one known deepfake sample and authentic samples) for the demo.

### Phase 1 — Core Pipeline (Hackathon Day 1 — Build Priority Order)
1. Backend skeleton + database schema (Claim, ScamReport, MediaCheck entities).
2. Intake + Claim Extraction + Evidence Retrieval + Verdict Synthesis agents (fact-check path) — **this is the highest-priority path to get end-to-end first**, since it validates the multi-agent architecture pattern that the other two paths will reuse.
3. Basic web frontend: submission form + result display (unstyled/minimal is fine at this stage).

### Phase 2 — Feature Expansion (Hackathon Day 1-2)
4. Scam-check path: OCR integration + Pattern-Match + Risk Signal agents.
5. Live feed UI (auto-updating list, category filters, search).
6. Seed the scam database and fact-check feed with curated data so the product doesn't look empty.

### Phase 3 — Media Authenticity + Dashboard (Hackathon Day 2)
7. Media Authenticity path: metadata forensics + visual forensics agent (start with an existing open-source deepfake detection model rather than training from scratch) + reverse-search agent.
8. Public dashboard: trending list + category chart, computed from seeded + live submission data.

### Phase 4 — WhatsApp Bot + Polish (Hackathon Day 2-3 / Final Stretch)
9. WhatsApp webhook integration → routes to same backend pipeline as web.
10. UI/UX polish pass: verdict badges, Urdu localization of key flows, mobile responsiveness.
11. Prepare demo script: pre-select a real trending scam/claim + a test deepfake sample to showcase live, with a fallback pre-recorded run-through in case of live-demo technical issues.

### Phase 5 — Post-Hackathon Roadmap (Beyond Submission)
- Formal WhatsApp Business API approval and production deployment.
- Partnership outreach: existing Pakistani fact-checking organizations, SBP/FIA cyber crime wing (for scam data/credibility), local newsrooms.
- User accuracy audit process (sample verdicts reviewed by human fact-checkers).
- P1/P2 features from Section 7 (shareable scam alert cards, browser extension, predictive trending, etc.).
- Explore grant/accelerator funding for civic-tech/AI-for-good tracks.

---

## 16. Team & Roles (Template — Fill In Per Team)

| Role | Responsibility |
|---|---|
| AI/Backend Engineer(s) | Multi-agent pipeline, orchestration, LLM integration, database |
| Frontend Engineer(s) | Web portal (feed, checkers, dashboard UI) |
| Integration Engineer | WhatsApp bot webhook, OCR, media forensics model integration |
| Product/Design | UX flows, verdict/badge system design, Urdu localization, demo script |
| Data/Content | Seed dataset curation (scams, fact-checks, deepfake samples), post-hackathon accuracy validation |

---

## 17. Appendix

### 17.1 Example Verdict Output Schema (JSON)

```json
{
  "id": "chk_8f21a",
  "type": "scam_check",
  "input_summary": "Message claiming to be from 'SBP Loan Dept' asking for CNIC and OTP to release a loan.",
  "verdict": "Likely Scam",
  "confidence_score": 92,
  "category": "Phishing / Bank Impersonation",
  "explanation_en": "The State Bank of Pakistan does not distribute loans directly via WhatsApp and never asks for your OTP. This message matches a known scam pattern reported 47 times in our database.",
  "explanation_ur": "اسٹیٹ بینک آف پاکستان واٹس ایپ کے ذریعے براہ راست قرض جاری نہیں کرتا اور کبھی بھی آپ کا او ٹی پی نہیں مانگتا۔",
  "red_flags": ["impersonation_of_govt_entity", "otp_request", "urgency_language"],
  "sources": [
    {"title": "SBP Official Advisory on Loan Scams", "url": "https://example.gov.pk/advisory"}
  ],
  "agent_trail": [
    {"agent": "intake", "output": "text, Urdu+English mixed, routed to scam-check path"},
    {"agent": "ocr_extraction", "output": "n/a - direct text input"},
    {"agent": "pattern_match", "output": "94% similarity to known pattern #SCAM-0231"},
    {"agent": "risk_signal", "output": "3 red flags detected"},
    {"agent": "verdict_synthesis", "output": "draft verdict: Likely Scam, 90%"},
    {"agent": "orchestrator_judge", "output": "confirmed, added source citation, final 92%"}
  ],
  "created_at": "2026-08-26T10:15:00Z"
}
```

### 17.2 Verdict Label Definitions (Fact-Check Path)
- **True** — Claim is substantiated by credible, cross-checked sources.
- **False** — Claim is contradicted by credible sources / fabricated.
- **Misleading** — Contains some factual elements but presented in a way that distorts the overall meaning (missing context, exaggeration).
- **Satire** — Content originates from a known satire source and is not intended as factual reporting.
- **Unverified** — Insufficient evidence available to confidently confirm or deny (default safe fallback).

### 17.3 Verdict Label Definitions (Scam-Check Path)
- **Likely Scam** — Strong match to known scam patterns and/or multiple high-severity red flags detected.
- **Needs Caution** — Some suspicious signals present but not conclusive; proceed carefully.
- **Likely Safe** — No significant red flags or known scam pattern matches detected. *(Always paired with a reminder that this is not a guarantee.)*

### 17.4 Verdict Label Definitions (Media Authenticity Path)
- **Likely Authentic** (0-30% manipulation score)
- **Inconclusive** (31-69% manipulation score) — signals are mixed or insufficient
- **Likely Manipulated/AI-Generated** (70-100% manipulation score)

### 17.5 Sample Seed Scam Categories for Pakistan Context
- Fake bank/SBP loan or "account suspended" phishing messages
- Fake government scheme registration (e.g., fraudulent BISP/Ehsaas-style scheme messages requesting fees)
- "Work from home" / online task job scams requesting upfront payment
- Fraudulent investment/forex/crypto schemes promising guaranteed high returns
- OLX/Daraz marketplace advance-payment or fake courier scams
- Lottery/prize-won scams ("You've won a car/iPhone")
- Romance scams via social media leading to money requests
- Fake charity/donation appeals (especially during disaster events)
- SIM-swap / OTP-theft social engineering attempts

---

## 18. Glossary

- **Deepfake:** AI-generated or manipulated media (image, video, or audio) designed to convincingly depict something that did not actually happen or someone saying/doing something they did not.
- **Multi-Agent Pipeline:** An AI system architecture where multiple specialized AI "agents" (each with a narrow task and toolset) collaborate under an orchestrator to complete a complex task, rather than relying on a single general-purpose model call.
- **OCR (Optical Character Recognition):** Technology that extracts machine-readable text from images (e.g., screenshots).
- **Verdict Confidence Score:** A numeric (0-100%) estimate of how certain the AI pipeline is in its final verdict, used to determine whether a definitive label can be shown or whether the system should default to "Unverified."
- **Spread/Trend Score:** A computed metric (based on report volume and recency) used to rank items on the public dashboard by how actively they are currently circulating.

---

*End of Document.*
