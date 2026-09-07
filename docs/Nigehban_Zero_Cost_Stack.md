# Nigehban — Zero-Cost Stack (Quality-Preserving)

**Goal:** Run Nigehban with **$0/month recurring API/hosting bills** while keeping the multi-agent pipeline, source grounding, Urdu support, and audit trail.

**Companion docs:** [`Nigehban_PRD.md`](./Nigehban_PRD.md), [`Nigehban_Backend_Production_Spec.md`](./Nigehban_Backend_Production_Spec.md)

---

## 1. Replace every paid service

| Paid (current / planned) | Free replacement | Quality note |
|--------------------------|------------------|----------------|
| **Anthropic Claude** | **Ollama** (self-hosted) or **Groq free tier** | Use 2-tier: fast 8B for intake/extraction, 14B+ for judge/synthesis |
| **OpenAI / Voyage embeddings** | **sentence-transformers** or **fastembed** locally | Multilingual model for Urdu + English; pgvector stays |
| **Bing / Google Search API** | **DuckDuckGo** (`duckduckgo-search`) + **RSS** + curated index | Ground verdicts in URLs returned by search, not model memory |
| **Cloudflare R2 / AWS S3** | **Local disk** or **MinIO** on same VPS | Already supported in `storage.py` |
| **Managed Postgres / Redis** | **Docker Compose** on one VM | Same images as dev |
| **Vercel** | **Cloudflare Pages** or **Caddy** on same VM | Next.js `standalone` or static export |
| **Sentry** | Structured logs + **GlitchTip** (self-hosted) or skip | Optional |
| **TinEye / reverse-image API** | **imagehash** + internal pgvector media index | Match against prior uploads |
| **Meta WhatsApp API** | **Web-first** + optional **Telegram Bot API** (free) | See §3 — WhatsApp has no real free production tier |

---

## 2. Recommended zero-cost architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Oracle Cloud Always Free (or your own machine)             │
│  ARM VM ~24GB RAM — single node or 2 VMs                    │
├─────────────────────────────────────────────────────────────┤
│  Caddy (TLS + reverse proxy)                                │
│    ├── Next.js (frontend)                                   │
│    └── FastAPI (API)                                        │
│  Ollama                                                     │
│    ├── qwen2.5:7b-instruct   → haiku-tier agents            │
│    └── qwen2.5:14b-instruct  → sonnet-tier (judge, synth)   │
│  Docker: postgres+pgvector, redis, minio (optional)         │
│  Workers: same pipeline, asyncio or celery                  │
│  Embeddings: fastembed / sentence-transformers (in-process) │
└─────────────────────────────────────────────────────────────┘
```

**Why this preserves quality:**

1. **Multi-agent layout unchanged** — specialization still beats one big prompt.
2. **Judge + confidence floor unchanged** — safety rules don’t depend on Claude.
3. **Evidence from search/RSS** — LLM ranks and explains; it doesn’t invent facts.
4. **Rule-based scam signals** — OTP/urgency/impersonation heuristics + LLM.
5. **Open forensics for media** — EXIF + Hugging Face deepfake checkpoints (not LLM-only).
6. **Caching** — L1–L4 dedup cuts repeat LLM calls (critical on free/local LLMs).

---

## 3. WhatsApp: the one honest exception

Meta **WhatsApp Cloud API** charges per conversation after a small free tier. There is no sustainable **$0 public bot** on WhatsApp.

**Free alternatives that keep accessibility:**

| Option | Cost | UX for Uncle Tariq |
|--------|------|---------------------|
| **Mobile web** (PWA) | $0 | Add to home screen; paste/screenshot flow |
| **Telegram Bot API** | $0 | Very common in Pakistan; free unlimited bot API |
| **Share link** | $0 | “Check on Nigehban” link users forward in WhatsApp groups |
| **WhatsApp** (Meta) | Paid | Keep as optional paid channel later |

**Recommendation:** Ship **PWA + Telegram** for $0 messaging; defer WhatsApp until funding.

---

## 4. LLM strategy (quality vs speed)

### Option A — Fully self-hosted (true $0, no API limits)

| Role | Ollama model | RAM (approx) |
|------|--------------|--------------|
| Intake, OCR cleanup, risk signals, pattern ranking | `qwen2.5:7b-instruct` | ~5 GB |
| Claim extraction, synthesis, **Judge** | `qwen2.5:14b-instruct` | ~10 GB |
| Embeddings | `nomic-embed-text` via Ollama | ~1 GB |

Run **7B for parallel agents**, **14B only for judge + final synthesis** (2 calls max per check).

### Option B — Groq free tier (easier demo, caps apply)

| Role | Groq model |
|------|------------|
| Fast tier | `llama-3.1-8b-instant` |
| Reasoning tier | `llama-3.3-70b-versatile` (check current free limits) |

Good for hackathon; migrate to Ollama when rate limits bite.

### Option C — Hybrid (practical)

- **Groq** for development and demos.
- **Ollama** on Oracle Cloud for production unlimited inference.

**Code change:** Abstract `LLMService` behind a provider interface (`ollama` | `groq` | `anthropic`) — agents stay identical.

---

## 5. Search & grounding (no paid search API)

### Layer 1 — DuckDuckGo (free)

```python
# pip install duckduckgo-search
from duckduckgo_search import DDGS
results = DDGS().text("SBP loan scam Pakistan", max_results=8)
```

### Layer 2 — RSS (already in `ingestion.py`)

Configure `RSS_FEED_URLS` with free feeds:

- Dawn, Geo, BBC Urdu, Al Jazeera
- IFCN / Pakistani fact-check desks where RSS exists

### Layer 3 — Curated static index (high quality, $0)

Seed JSON/DB table of **verified** URLs:

- SBP scam advisories
- FIA cyber crime public pages
- Major bank fraud alert pages

**Verdict rule (keep):** No retrievable source → max confidence 60 → tend toward `unverified`.

---

## 6. Embeddings (replace hash stub)

| Library | Model | Dims | Urdu |
|---------|-------|------|------|
| **fastembed** | `BAAI/bge-m3` | 1024 | Strong multilingual |
| sentence-transformers | `paraphrase-multilingual-MiniLM-L12-v2` | 384 | Good |

**Migration:** Change pgvector column from `vector(1536)` to match model dims; re-index `scam_patterns` and `claims`.

---

## 7. Media forensics (free, better than LLM-only)

| Signal | Free tool |
|--------|-----------|
| Metadata | `exifread`, Pillow |
| Manipulation | `imagehash` (phash), OpenCV |
| Deepfake (image) | Hugging Face `prithivMLmods/Deep-Fake-Detector-v2` or similar |
| Reverse match | pgvector on media embeddings + phash dedup |
| Video | Extract frames with `ffmpeg` (free); run image model on frames |

**Do not** rely on LLM “I cannot see the image” for production media checks.

---

## 8. Hosting: $0 production options

| Provider | What you get | Fit for Nigehban |
|----------|--------------|------------------|
| **Oracle Cloud Always Free** | 4× ARM Ampere, 24 GB RAM total | Best fit — run Ollama + full stack |
| **Your PC / home server** | Full control | Dev + small public demo |
| **Cloudflare Pages** | Static frontend | Free CDN for Next export |
| **Fly.io / Railway** | Small free credits | OK for API-only demo, not Ollama |

**Single-VM stack:**

```bash
docker compose up -d postgres redis minio
ollama serve
ollama pull qwen2.5:7b-instruct qwen2.5:14b-instruct nomic-embed-text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 9. Cost control without cutting agents

| Technique | Saves |
|-----------|--------|
| L1 content-hash dedup | Skip entire pipeline for identical forwards |
| L2 embedding similarity | Near-duplicate scam messages |
| L3 evidence cache | Same claim → same search results 6h |
| Run 7B in parallel, 14B only for judge | ~40% fewer heavy tokens |
| Batch RSS ingestion off-peak | Spreads load |
| Cap video to 30s / 10 frames | Media path CPU bound |

---

## 10. Implementation checklist (code changes)

| Priority | Task | Effort |
|----------|------|--------|
| P0 | `LLMProvider` abstraction + Ollama client | 1–2 days |
| P0 | DuckDuckGo in `search.py` | 0.5 day |
| P0 | fastembed in `embeddings.py` + migration for vector dim | 1 day |
| P0 | Wire local storage / MinIO for all uploads | 0.5 day |
| P1 | Implement cache layers L1–L4 in Redis | 1 day |
| P1 | Hugging Face deepfake model in `visual_analysis.py` | 1–2 days |
| P1 | Telegram bot webhook (mirror WhatsApp handler) | 1 day |
| P2 | PWA manifest + mobile-optimized submit flow | 1 day |
| P2 | GlitchTip or log aggregation | optional |

---

## 11. What you give up vs paid stack

| Area | Tradeoff | Mitigation |
|------|----------|------------|
| LLM reasoning | Smaller models vs Claude Sonnet | Judge + sources + rules; 14B Qwen is strong |
| Search quality | DDG < Google/Bing | Curated index + RSS for Pakistan |
| WhatsApp | No free production bot | PWA + Telegram |
| Ops | You run the server | Oracle free tier + docker |
| Cold start | Ollama load time | Keep models warm; single worker |

**What you do NOT give up:**

- Multi-agent transparency (`agent_logs`)
- Confidence floor & sensitive-topic handling
- Urdu OCR (Tesseract)
- Scam pattern DB + vector search
- Public feed, dashboard, SSE

---

## 12. Summary

**Fully free, quality-preserving path:**

1. **Oracle Cloud Always Free** — one VM, everything on it.
2. **Ollama** (Qwen 7B + 14B) — replace Anthropic.
3. **fastembed + pgvector** — replace paid embeddings.
4. **DuckDuckGo + RSS + curated URLs** — replace search API.
5. **Local disk / MinIO** — replace R2.
6. **PWA + Telegram** — replace WhatsApp for $0 messaging.
7. **Open CV / HF models** — replace LLM-only media analysis.

Total recurring cost: **$0** (plus optional domain ~$10/year).

---

*End of document.*
