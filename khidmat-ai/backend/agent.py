"""KhidmatAI — Lightweight agentic chat.

Simple pipeline:
  1. Auto-detect query language (Urdu / Roman Urdu / English / any).
  2. Search local SQLite for matching welfare programs.
  3. Optionally enrich with Tavily web search (only for real-time queries).
  4. Call Gemini (primary) → Groq (fallback) for a conversational answer.

No LangGraph.  No DashScope chain.  No heavy scoring or metadata walls.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# API configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()

# Circuit breakers — skip a provider after auth failure
_gemini_auth_failed = False
_groq_auth_failed = False


# ---------------------------------------------------------------------------
# LLM callers
# ---------------------------------------------------------------------------

def _call_gemini(system_prompt: str, user_prompt: str) -> str | None:
    """Call Google Gemini via the REST API (plain text response)."""
    global _gemini_auth_failed
    if _gemini_auth_failed or not GEMINI_API_KEY:
        return None
    if GEMINI_API_KEY.startswith(("your_", "yahan_")):
        return None
    try:
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 2048,
            },
        }
        res = requests.post(
            url, params={"key": GEMINI_API_KEY}, json=payload, timeout=30
        )
        if res.status_code in (401, 403, 404):
            _gemini_auth_failed = True
            return None
        res.raise_for_status()
        data = res.json()
        candidates = data.get("candidates") or []
        if not candidates:
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts).strip()
        return text or None
    except Exception:
        return None


def _call_groq(system_prompt: str, user_prompt: str) -> str | None:
    """Call Groq API (OpenAI-compatible) as fallback."""
    global _groq_auth_failed
    if _groq_auth_failed or not GROQ_API_KEY:
        return None
    if GROQ_API_KEY.startswith(("your_", "yahan_")):
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
        }
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        if res.status_code in (401, 403):
            _groq_auth_failed = True
            return None
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _call_llm(system_prompt: str, user_prompt: str) -> tuple[str | None, str]:
    """Gemini primary → Groq fallback."""
    result = _call_gemini(system_prompt, user_prompt)
    if result:
        return result, f"Gemini ({GEMINI_MODEL})"
    result = _call_groq(system_prompt, user_prompt)
    if result:
        return result, f"Groq ({GROQ_MODEL})"
    return None, "offline"


# ---------------------------------------------------------------------------
# Tavily web search (only triggered for real-time queries)
# ---------------------------------------------------------------------------

def _web_search(query: str) -> list[dict[str, str]]:
    """Run a Tavily search.  Returns [] when key is missing or on error."""
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key or api_key.startswith(("your_", "yahan_", "paste_")):
        return []
    try:
        res = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": f"{query} Pakistan welfare official",
                "search_depth": "advanced",
                "max_results": 4,
                "include_answer": True,
                "include_raw_content": False,
            },
            timeout=30,
        )
        res.raise_for_status()
        data = res.json()
        return [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": (item.get("content") or "")[:1500],
            }
            for item in data.get("results", [])
        ]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Language auto-detection
# ---------------------------------------------------------------------------

_URDU_RE = re.compile(r"[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]")

_ROMAN_URDU_WORDS = {
    "kya", "hai", "hain", "ho", "kaise", "kahan", "kab", "kaun",
    "bhi", "nahi", "nahin", "mein", "mera", "meri", "hum", "tum", "aap",
    "kar", "raha", "rahi", "tha", "thi", "the", "sakta", "sakti",
    "chahiye", "zaroorat", "madad", "karo", "batao", "ta", "ti", "se",
    "ke", "ki", "ko", "par", "pe", "ne", "ga", "gi", "ge",
    "aur", "ya", "agar", "toh", "phir", "abhi", "bahut", "bohat", "thoda",
    "paisa", "paise", "rupay", "ilaaj", "ilaj", "taleem", "wazifa",
    "rashan", "atta", "dawa", "ghar", "naukri", "rozgar", "hunar",
    "sahara", "zakat", "baitulmal", "kafalat", "bewa", "mazoor",
}


def detect_language(text: str) -> str:
    """Auto-detect the language/script of *text*.

    Returns one of: ``'urdu'``, ``'roman'``, or ``'english'``.
    """
    if _URDU_RE.search(text):
        return "urdu"
    words = set(re.findall(r"[a-z]+", text.lower()))
    if len(words & _ROMAN_URDU_WORDS) >= 2:
        return "roman"
    return "english"


# ---------------------------------------------------------------------------
# Intent helpers
# ---------------------------------------------------------------------------

_WEB_TRIGGERS_EN = {
    "apply", "application", "deadline", "last date", "register",
    "how to apply", "new program", "latest", "update", "recent",
    "2024", "2025", "2026", "status check", "eligibility check",
    "check status", "online apply", "nsers", "8171",
}
_WEB_TRIGGERS_UR = {
    "درخواست", "رجسٹر", "آخری تاریخ", "نیا", "تازہ ترین", "8171",
}
_WEB_TRIGGERS_ROMAN = {
    "apply", "apply karna", "deadline", "aakhri tareekh", "last date",
    "register", "nayi scheme", "naya program", "8171", "nsers",
    "status check", "online apply",
}


def _needs_web_search(query: str) -> bool:
    """True only when the query asks about real-time info or application processes."""
    q = query.lower().strip()
    if any(t in q for t in _WEB_TRIGGERS_EN):
        return True
    if any(t in q for t in _WEB_TRIGGERS_UR):
        return True
    if any(t in q for t in _WEB_TRIGGERS_ROMAN):
        return True
    return False


# ---------------------------------------------------------------------------
# Lightweight DB search
# ---------------------------------------------------------------------------

def _search_db(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Simple keyword-rank search over the local programs table."""
    from . import database as db

    all_progs = db.get_all_programs()
    if not all_progs:
        return []

    q_tokens = set(re.findall(r"[a-z0-9\u0600-\u06FF]+", query.lower()))
    if not q_tokens:
        return []

    scored: list[tuple[int, dict[str, Any]]] = []
    for p in all_progs:
        text = " ".join([
            str(p.get("title", "")),
            str(p.get("category", "")),
            str(p.get("description", "")),
            " ".join(str(x) for x in p.get("keywords", [])),
            " ".join(str(x) for x in p.get("eligibility", [])),
            " ".join(str(x) for x in p.get("locations", [])),
        ]).lower()
        score = sum(1 for t in q_tokens if t in text)
        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in scored[:limit]]


def _summarize_for_llm(programs: list[dict[str, Any]]) -> str:
    """Build a concise text block of program data to feed to the LLM."""
    if not programs:
        return ""
    lines: list[str] = []
    for p in programs:
        title = p.get("title", "")
        desc = str(p.get("description", ""))[:200]
        elig = ", ".join(str(x) for x in p.get("eligibility", []))[:150]
        support = ", ".join(str(x) for x in p.get("support", []))[:120]
        src = p.get("source_url", "")
        lines.append(f"- {title}: {desc}")
        if elig:
            lines.append(f"  Eligibility: {elig}")
        if support:
            lines.append(f"  Support: {support}")
        if src:
            lines.append(f"  Official: {src}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Response parser (tolerant: plain text or JSON)
# ---------------------------------------------------------------------------

def _parse_response(raw: str) -> str:
    """Extract clean conversational text from the LLM response.

    Handles plain text, JSON ``{"summary": "..."}``, and code-fenced output.
    """
    if not raw:
        return ""
    text = raw.strip()
    # Try JSON extraction first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and obj.get("summary"):
            return str(obj["summary"]).strip()
    except (json.JSONDecodeError, TypeError):
        pass
    m = re.search(r"\{[^{}]*\"summary\"\s*:\s*\".*?\"\s*[^{}]*\}", text, re.S)
    if m:
        try:
            obj = json.loads(m.group(0))
            if obj.get("summary"):
                return str(obj["summary"]).strip()
        except (json.JSONDecodeError, TypeError):
            pass
    # Strip code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are KhidmatAI, Pakistan's welfare assistant.\n"
    "Reply in the EXACT same language and script as the user's message "
    "(English, Roman Urdu, Urdu, or any other). Mirror their language.\n"
    "Keep the response short, direct, and conversational (2-4 sentences "
    "for simple questions, a bit longer when listing programs).\n"
    "Use bullet points when listing multiple items.\n"
    "If welfare program data is provided below, use it to answer accurately.\n"
    "If no data matches, briefly guide the user to check the platform's "
    "program library or official portals (bisp.gov.pk, helpline 8171).\n"
    "NEVER invent specific amounts, deadlines, or eligibility criteria "
    "not in the provided data.\n"
    "Do NOT include metadata, source labels, or technical tags in your reply."
)


def run_chat(query: str) -> dict:
    """Run the lightweight chat pipeline and return a structured response.

    The returned ``answer.summary`` is a clean conversational paragraph.
    """
    language = detect_language(query)

    # 1 — Local DB search
    db_matches = _search_db(query)

    # 2 — Web search (only for real-time / application queries)
    web_results: list[dict[str, str]] = []
    if _needs_web_search(query) and not db_matches:
        web_results = _web_search(query)

    # 3 — Build context for the LLM
    user_parts: list[str] = []

    if db_matches:
        user_parts.append(
            f"WELFARE PROGRAMS FOUND:\n{_summarize_for_llm(db_matches)}"
        )

    if web_results:
        web_text = "\n".join(
            f"- {r['title']}: {r['snippet'][:400]} ({r['url']})"
            for r in web_results
        )
        user_parts.append(f"WEB SEARCH RESULTS:\n{web_text}")

    if not user_parts:
        user_parts.append(
            "No matching programs found locally. Guide the user to check "
            "the platform's program library or official portals."
        )

    user_prompt = "\n\n".join(user_parts) + f"\n\nUser query: {query}"

    # 4 — LLM call (Gemini → Groq)
    raw, model_used = _call_llm(_SYSTEM_PROMPT, user_prompt)

    summary = _parse_response(raw) if raw else ""
    if not summary:
        # Deterministic fallback — no LLM output
        if db_matches:
            titles = ", ".join(p.get("title", "") for p in db_matches[:3])
            summary = (
                f"Found {len(db_matches)} relevant programs: {titles}. "
                "Check the official sources for full details."
            )
        else:
            summary = (
                "I couldn't find specific information right now. "
                "Please check bisp.gov.pk or call the 8171 helpline for guidance."
            )

    official_source = ""
    if db_matches:
        official_source = db_matches[0].get("source_url", "")

    return {
        "answer": {
            "summary": summary,
            "programs": [],
            "official_source": official_source,
            "next_steps": [],
        },
        "model_used": model_used,
        "language": language,
        "matches": [],
        "sources": [],
    }
