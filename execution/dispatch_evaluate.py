"""
dispatch_evaluate.py — Parallel Subagent Dispatcher
Layer: 3 (Execution)
Usage: python execution/dispatch_evaluate.py --user chase_lavalley --urls "url1" "url2" "url3"
   or: python execution/dispatch_evaluate.py --user chase_lavalley --url "url1"

Spawns one headless `claude -p` subagent per URL using asyncio.
All subagents run in parallel — results land in jobs.db as they complete.
Dispatcher does not wait for all to finish before returning progress updates.

Each subagent receives:
  - The URL to process
  - The evaluate_job.md directive injected as its system prompt

Exit codes:
  0 — All subagents completed (some may have written failed rows — check jobs.db)
  1 — Dispatcher itself failed (bad args, directive missing, etc.)
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Self-Source .env
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(dotenv_path=_env_path, override=False)
    _enc = os.environ.get("PYTHONIOENCODING", "")
    if _enc:
        import io
        if isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout.reconfigure(encoding=_enc)
        if isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr.reconfigure(encoding=_enc)
except (ImportError, AttributeError):
    pass


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DIRECTIVE_PATH = "directives/evaluate_job.md"
MAX_CONCURRENT = 5       # cap parallel subagents to avoid API rate limits
SUBAGENT_TIMEOUT = 300   # seconds before a subagent is considered hung (5 min)


# ---------------------------------------------------------------------------
# Single subagent runner
# ---------------------------------------------------------------------------
async def run_subagent(url: str, directive: str, user_id: str, semaphore: asyncio.Semaphore) -> dict:
    """
    Spawns a single headless claude -p subagent for one URL.
    Returns a result dict with url, status, exit_code, and output snippet.
    """
    async with semaphore:
        started_at = datetime.now(timezone.utc).isoformat()
        print(f"[DISPATCH] Starting → {url}")

        prompt = (
            f"You are a headless job evaluation subagent. "
            f"Your task is to evaluate this job posting URL: {url}\n\n"
            f"Follow the directive below exactly. Do not ask for user input at any point.\n\n"
            f"{directive}"
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                "claude",
                "-p",
                "--dangerously-skip-permissions",
                prompt,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=SUBAGENT_TIMEOUT
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                print(f"[DISPATCH] TIMEOUT → {url}")
                return {
                    "url": url,
                    "status": "timeout",
                    "exit_code": -1,
                    "started_at": started_at,
                    "output": "Subagent timed out after 300s",
                }

            exit_code = proc.returncode
            output = stdout.decode("utf-8", errors="replace").strip()
            err_output = stderr.decode("utf-8", errors="replace").strip()

            # Print last 3 lines of output for visibility without flooding terminal
            output_lines = output.splitlines()
            snippet = "\n".join(output_lines[-3:]) if output_lines else "(no output)"

            if exit_code == 0:
                print(f"[DISPATCH] ✅ Done → {url}")
            else:
                print(f"[DISPATCH] ❌ Failed (exit {exit_code}) → {url}")
                if err_output:
                    print(f"  stderr: {err_output[:200]}")

            print(f"  └─ {snippet}")

            return {
                "url": url,
                "status": "done" if exit_code == 0 else "failed",
                "exit_code": exit_code,
                "started_at": started_at,
                "output": snippet,
            }

        except FileNotFoundError:
            print(
                "[DISPATCH FATAL] `claude` CLI not found. "
                "Is Claude Code installed and on your PATH?",
                file=sys.stderr
            )
            return {
                "url": url,
                "status": "fatal",
                "exit_code": -1,
                "started_at": started_at,
                "output": "claude CLI not found",
            }
        except Exception as e:
            print(f"[DISPATCH] ERROR → {url}: {type(e).__name__}: {e}", file=sys.stderr)
            return {
                "url": url,
                "status": "error",
                "exit_code": -1,
                "started_at": started_at,
                "output": str(e),
            }


# ---------------------------------------------------------------------------
# Dispatcher orchestrator
# ---------------------------------------------------------------------------
async def dispatch_all(urls: list[str], user_id: str) -> None:
    # Load directive once — shared across all subagents
    if not os.path.exists(DIRECTIVE_PATH):
        print(f"[DISPATCH FATAL] Directive not found: {DIRECTIVE_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(DIRECTIVE_PATH, "r", encoding="utf-8") as f:
        directive = f.read()

    print(f"\n[DISPATCH] Spawning {len(urls)} subagent(s) | max concurrent: {MAX_CONCURRENT}")
    print(f"[DISPATCH] User: {user_id} | Directive: {DIRECTIVE_PATH}\n")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    tasks = [
        run_subagent(url.strip(), directive, user_id, semaphore)
        for url in urls
        if url.strip()
    ]

    results = await asyncio.gather(*tasks)

    # Summary
    done    = sum(1 for r in results if r["status"] == "done")
    failed  = sum(1 for r in results if r["status"] in ("failed", "error", "fatal", "timeout"))

    print(f"\n[DISPATCH] Complete — {done} succeeded, {failed} failed")
    print(f"[DISPATCH] Check .users/{user_id}/jobs.db for results\n")

    if failed:
        print("[DISPATCH] Failed URLs:")
        for r in results:
            if r["status"] not in ("done",):
                print(f"  {r['status'].upper()} → {r['url']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Dispatch parallel job evaluation subagents.")
    parser.add_argument("--user", required=True, help="User ID (e.g. chase_lavalley)")

    url_group = parser.add_mutually_exclusive_group(required=True)
    url_group.add_argument("--url",  type=str,           help="Single job URL")
    url_group.add_argument("--urls", type=str, nargs="+", help="Multiple job URLs")

    args = parser.parse_args()

    urls = [args.url] if args.url else args.urls

    # Deduplicate while preserving order
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    if len(unique_urls) < len(urls):
        print(f"[DISPATCH] Deduplicated {len(urls) - len(unique_urls)} duplicate URL(s)")

    asyncio.run(dispatch_all(unique_urls, args.user))


if __name__ == "__main__":
    main()