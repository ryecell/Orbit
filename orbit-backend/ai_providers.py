"""
Pluggable vision-AI backend for /ai/analyze, so Orbit can run on a free tier
instead of a paid API.

Pick one with the AI_PROVIDER env var:

  gemini      Google AI Studio free tier.   Needs GEMINI_API_KEY.
              Optional GEMINI_MODEL (default below — check AI Studio for current names).
  openai      Any OpenAI-compatible vision endpoint (Groq, OpenRouter, Cloudflare, ...).
              Needs AI_API_KEY, AI_BASE_URL and AI_MODEL.
              e.g. AI_BASE_URL=https://api.groq.com/openai/v1
  anthropic   The original paid Claude path.  Needs ANTHROPIC_API_KEY.

If AI_PROVIDER is unset it falls back to whichever key is present
(GEMINI_API_KEY, then AI_API_KEY, then ANTHROPIC_API_KEY).

AI_DAILY_LIMIT_PER_USER (default 10) and AI_DAILY_LIMIT_TOTAL (default 200) cap
usage so a free tier's daily quota can't be drained by one person.
"""
import json
import os
import re
import threading
from datetime import datetime, timezone
from typing import Optional

GEMINI_DEFAULT_MODEL = "gemini-flash-lite-latest"
ANTHROPIC_DEFAULT_MODEL = "claude-sonnet-4-6"


class AIError(Exception):
    """Raised with a message that is safe to show the user."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.status = status


# ---------- configuration ----------

def provider_name(env=None) -> Optional[str]:
    env = os.environ if env is None else env
    explicit = (env.get("AI_PROVIDER") or "").strip().lower()
    if explicit:
        return explicit
    if env.get("GEMINI_API_KEY"):
        return "gemini"
    if env.get("AI_API_KEY"):
        return "openai"
    if env.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


# ---------- prompt & parsing (pure, unit-tested) ----------

def build_prompt(folders) -> str:
    return (
        "You are the AI auto-tagging engine inside a digital archive app called Orbit. "
        "Look at this image — it may be handwritten notes, a printed document, a diagram, or a photo — "
        "and respond with ONLY raw JSON, no markdown fences, no preamble, in exactly this shape: "
        '{"title": "short descriptive title, max 6 words", '
        f'"folder": "best matching folder from this list: {", ".join(folders)}", '
        '"tags": ["3 to 5 short lowercase keyword tags"], '
        '"summary": "one sentence, max 22 words, summarizing the content"}'
    )


def extract_json(text: str) -> dict:
    """Models sometimes wrap JSON in fences or add chatter; pull out the first {...} object."""
    cleaned = (text or "").replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not m:
            raise AIError("AI response was not valid JSON")
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            raise AIError("AI response was not valid JSON")
    if not isinstance(data, dict):
        raise AIError("AI response was not valid JSON")
    return data


def normalize_result(data: dict, folders) -> dict:
    """Coerce whatever the model returned into the shape the app expects."""
    title = str(data.get("title") or "Untitled note").strip()[:80] or "Untitled note"
    folder = str(data.get("folder") or "").strip()
    by_lower = {f.lower(): f for f in folders}
    folder = by_lower.get(folder.lower()) or (folders[0] if folders else "Personal")
    raw_tags = data.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = raw_tags.split(",")
    tags = []
    for t in raw_tags:
        t = str(t).strip().lower().lstrip("#")[:30]
        if t and t not in tags:
            tags.append(t)
    summary = str(data.get("summary") or "").strip()[:300]
    return {"title": title, "folder": folder, "tags": tags[:5], "summary": summary}


def gemini_request(model: str, image_b64: str, media_type: str, prompt: str) -> dict:
    return {
        "contents": [{"parts": [{"inline_data": {"mime_type": media_type, "data": image_b64}}, {"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 500, "temperature": 0.2},
    }


def gemini_text(resp: dict) -> str:
    try:
        parts = resp["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError):
        reason = (resp.get("promptFeedback") or {}).get("blockReason") if isinstance(resp, dict) else None
        raise AIError("The AI couldn't read that image" + (f" ({reason})." if reason else "."))
    return "".join(p.get("text", "") for p in parts)


def openai_request(model: str, image_b64: str, media_type: str, prompt: str) -> dict:
    return {
        "model": model,
        "max_tokens": 500,
        "temperature": 0.2,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{media_type};base64,{image_b64}"}},
            ],
        }],
    }


def openai_text(resp: dict) -> str:
    try:
        content = resp["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise AIError("The AI returned an unexpected response.")
    if isinstance(content, list):
        content = "".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content or ""


# ---------- daily usage caps (in-memory; per server process) ----------

class DailyQuota:
    def __init__(self):
        self._lock = threading.Lock()
        self._day = None
        self._per_user = {}
        self._total = 0

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def try_consume(self, user_id: str, per_user: int, total: int, today: Optional[str] = None) -> Optional[str]:
        """Returns None if allowed (and counts it), else a user-facing reason."""
        today = today or self._today()
        with self._lock:
            if self._day != today:
                self._day, self._per_user, self._total = today, {}, 0
            if self._per_user.get(user_id, 0) >= per_user:
                return f"You've used your {per_user} AI scans for today. They reset at midnight UTC — you can still save items manually."
            if self._total >= total:
                return "Orbit's free AI quota is used up for today. Try again tomorrow, or save the item manually."
            self._per_user[user_id] = self._per_user.get(user_id, 0) + 1
            self._total += 1
            return None

    def refund(self, user_id: str):
        with self._lock:
            if self._per_user.get(user_id, 0) > 0:
                self._per_user[user_id] -= 1
                self._total = max(0, self._total - 1)


quota = DailyQuota()


def limits(env=None):
    env = os.environ if env is None else env
    def _int(name, default):
        try:
            return max(1, int(env.get(name, default)))
        except (TypeError, ValueError):
            return default
    return _int("AI_DAILY_LIMIT_PER_USER", 10), _int("AI_DAILY_LIMIT_TOTAL", 200)


# ---------- the network call ----------

async def analyze(image_b64: str, media_type: str, folders, env=None) -> dict:
    import httpx

    env = os.environ if env is None else env
    name = provider_name(env)
    prompt = build_prompt(folders)

    if name == "gemini":
        key = env.get("GEMINI_API_KEY")
        if not key:
            raise AIError("GEMINI_API_KEY is not set on the server.", 500)
        model = env.get("GEMINI_MODEL") or GEMINI_DEFAULT_MODEL
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {"x-goog-api-key": key, "content-type": "application/json"}
        body, extract = gemini_request(model, image_b64, media_type, prompt), gemini_text
    elif name == "openai":
        key, base, model = env.get("AI_API_KEY"), (env.get("AI_BASE_URL") or "").rstrip("/"), env.get("AI_MODEL")
        if not (key and base and model):
            raise AIError("AI_API_KEY, AI_BASE_URL and AI_MODEL must all be set on the server.", 500)
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "content-type": "application/json"}
        body, extract = openai_request(model, image_b64, media_type, prompt), openai_text
    elif name == "anthropic":
        key = env.get("ANTHROPIC_API_KEY")
        if not key:
            raise AIError("ANTHROPIC_API_KEY is not set on the server.", 500)
        url = "https://api.anthropic.com/v1/messages"
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
        body = {
            "model": env.get("ANTHROPIC_MODEL") or ANTHROPIC_DEFAULT_MODEL,
            "max_tokens": 500,
            "messages": [{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": image_b64}},
                {"type": "text", "text": prompt},
            ]}],
        }
        extract = lambda r: "".join(b.get("text", "") for b in r.get("content", []))
    else:
        raise AIError("AI is not configured on the server (set AI_PROVIDER and its key).", 503)

    try:
        async with httpx.AsyncClient(timeout=40) as client:
            resp = await client.post(url, headers=headers, json=body)
    except httpx.HTTPError:
        raise AIError("Couldn't reach the AI service. Please try again.")

    if resp.status_code == 429:
        raise AIError("The AI service is busy or its free quota is used up. Try again later.", 429)
    if resp.status_code != 200:
        # Don't echo the provider's body to users (it can contain request details); log it server-side instead.
        from logging_config import logger
        logger.warning("AI provider %s returned %s: %s", name, resp.status_code, resp.text[:300])
        raise AIError("The AI service returned an error. Please try again.")

    return normalize_result(extract_json(extract(resp.json())), folders)
