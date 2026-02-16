#!/usr/bin/env python3
"""
Check API keys and their status (working / out of balance / invalid).

Usage:
    python scripts/check_api_status.py

Loads from .env.local or .env. Makes minimal API calls to verify each key.
"""

import asyncio
import os
import sys
from pathlib import Path

# Load env from project root
root = Path(__file__).resolve().parent.parent
os.chdir(root)
sys.path.insert(0, str(root))

# Load .env.local first, then .env
from dotenv import load_dotenv
load_dotenv(root / ".env.local")
load_dotenv(root / ".env")

# Now import after env is loaded
from config import settings


def check_anthropic() -> tuple[str, str]:
    """Test Anthropic API key with minimal request."""
    if not settings.ANTHROPIC_API_KEY:
        return "not_configured", "ANTHROPIC_API_KEY not set"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=settings.ANTHROPIC_MODEL,
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        return "ok", f"Working (model: {settings.ANTHROPIC_MODEL})"
    except Exception as e:
        err = str(e).lower()
        if "insufficient" in err or "quota" in err or "balance" in err or "credit" in err:
            return "out_of_balance", str(e)
        if "invalid" in err or "401" in err or "403" in err or "authentication" in err:
            return "invalid_key", str(e)
        return "error", str(e)


def check_openai() -> tuple[str, str]:
    """Test OpenAI API key with minimal request."""
    if not settings.OPENAI_API_KEY:
        return "not_configured", "OPENAI_API_KEY not set"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        # Use models.list - free and doesn't consume credits
        next(iter(client.models.list()))
        return "ok", "Working (key valid)"
    except Exception as e:
        err = str(e).lower()
        if "insufficient" in err or "quota" in err or "balance" in err or "billing" in err:
            return "out_of_balance", str(e)
        if "invalid" in err or "401" in err or "403" in err or "incorrect" in err:
            return "invalid_key", str(e)
        return "error", str(e)


def check_gemini() -> tuple[str, str]:
    """Test Google Gemini API key with minimal request."""
    if not settings.GOOGLE_API_KEY:
        return "not_configured", "GOOGLE_API_KEY not set"
    model_id = settings.GEMINI_MODEL_ID or settings.GEMINI_FALLBACK_MODEL_ID or "gemini-2.0-flash"
    try:
        # Try new google.genai first
        try:
            from google import genai
            client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            response = client.models.generate_content(
                model=model_id,
                contents="Say OK",
                config={"max_output_tokens": 10},
            )
        except ImportError:
            import google.generativeai as genai_old
            genai_old.configure(api_key=settings.GOOGLE_API_KEY)
            model = genai_old.GenerativeModel(model_id)
            response = model.generate_content("Say OK", generation_config={"max_output_tokens": 10})
        return "ok", f"Working (model: {model_id})"
    except Exception as e:
        err = str(e).lower()
        if "quota" in err or "resource_exhausted" in err or "429" in err:
            return "out_of_balance", str(e)
        if "invalid" in err or "401" in err or "403" in err or "api_key" in err:
            return "invalid_key", str(e)
        return "error", str(e)


def check_supabase() -> tuple[str, str]:
    """Test Supabase connection (no balance concept - just connectivity)."""
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        return "not_configured", "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set"
    try:
        from supabase import create_client
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
        # Simple health check - list tables or similar lightweight call
        client.table("pipeline_jobs").select("id").limit(1).execute()
        return "ok", "Connected"
    except Exception as e:
        err = str(e).lower()
        if "invalid" in err or "401" in err or "403" in err or "jwt" in err:
            return "invalid_key", str(e)
        return "error", str(e)


def check_railway() -> tuple[str, str]:
    """Test Railway worker URL (no balance API - just reachability)."""
    if not settings.WORKER_URL:
        return "not_configured", "WORKER_URL not set"
    try:
        import httpx
        # Just check if the worker responds (e.g. health or 404)
        r = httpx.get(settings.WORKER_URL, timeout=5)
        return "ok", f"Reachable (HTTP {r.status_code})"
    except Exception as e:
        return "error", str(e)


def main():
    print("=" * 60)
    print("Tragaldabas – API status check")
    print("=" * 60)

    results = []

    # 1. Anthropic (Claude)
    print("\n1. Anthropic (Claude)")
    status, msg = check_anthropic()
    results.append(("Anthropic", status, msg))
    icon = "✓" if status == "ok" else ("⚠" if status == "out_of_balance" else "✗")
    print(f"   {icon} {status}: {msg}")

    # 2. OpenAI
    print("\n2. OpenAI (GPT / Whisper)")
    status, msg = check_openai()
    results.append(("OpenAI", status, msg))
    icon = "✓" if status == "ok" else ("⚠" if status == "out_of_balance" else "✗")
    print(f"   {icon} {status}: {msg}")

    # 3. Google Gemini
    print("\n3. Google Gemini")
    status, msg = check_gemini()
    results.append(("Gemini", status, msg))
    icon = "✓" if status == "ok" else ("⚠" if status == "out_of_balance" else "✗")
    print(f"   {icon} {status}: {msg}")

    # 4. Supabase
    print("\n4. Supabase (DB/Auth)")
    status, msg = check_supabase()
    results.append(("Supabase", status, msg))
    icon = "✓" if status == "ok" else "✗"
    print(f"   {icon} {status}: {msg}")

    # 5. Railway worker
    print("\n5. Railway worker")
    status, msg = check_railway()
    results.append(("Railway", status, msg))
    icon = "✓" if status == "ok" else "✗"
    print(f"   {icon} {status}: {msg}")

    # AWS – not used by Tragaldabas (config ignores extra vars)
    print("\n6. AWS (Textract)")
    aws_key = os.environ.get("AWS_ACCESS_KEY_ID")
    if aws_key:
        print("   ⚠ Configured in .env but NOT used by this project (config ignores AWS vars)")
    else:
        print("   - Not configured (optional)")

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    ok = sum(1 for _, s, _ in results if s == "ok")
    out = sum(1 for _, s, _ in results if s == "out_of_balance")
    fail = sum(1 for _, s, _ in results if s in ("invalid_key", "error"))
    print(f"  Working: {ok}")
    if out:
        print(f"  Out of balance: {out}")
    if fail:
        print(f"  Failed: {fail}")

    print("\nTo check usage/balance in dashboards:")
    print("  • Anthropic: https://console.anthropic.com/")
    print("  • OpenAI:    https://platform.openai.com/usage")
    print("  • Gemini:    https://aistudio.google.com/usage")
    print("  • Supabase:  https://supabase.com/dashboard")
    print("  • Railway:   https://railway.app/dashboard")
    print("=" * 60)

    return 0 if ok > 0 and out == 0 and fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
