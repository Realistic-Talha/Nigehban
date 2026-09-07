# %% [markdown]
# 14 — Live AIGC remote (Colab GPU): CLIP zero-shot AI prompts + UnivFD head
# Honest limit: **no system detects every AI image / every future generator.**
# This ensemble is stronger than UnivFD alone on many modern gens (incl. often Gemini-like).
# POST /score → {p_aigc, p_aidetect (zero-shot), p_univfd}

# %%
# See Colab cell history — run the zero-shot+univfd Flask + cloudflared server on GPU.
# Then set laptop apps/api/.env:
#   AIGC_REMOTE_URL=https://xxxx.trycloudflare.com
# Keep the Colab runtime alive while using the web media checker.
