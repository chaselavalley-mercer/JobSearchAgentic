"""
scrape_jobs.py — Phase 1 Playwright Scraper (Raw Text Only)
Layer: 3 (Execution)

Responsibility: Fetch raw page content from a job posting URL using a
headless browser. No LLM calls. No structured extraction. Raw text output
only — Claude Code handles extraction via the job-scraper SKILL.md.

Usage:
    python scrape_jobs.py --url <URL> --user <user_id>

Output:
    .tmp/{user_id}/raw_job.txt  — raw page text for Claude Code to parse
"""

import asyncio
import argparse
import os
from playwright.async_api import async_playwright


async def scrape_page_content(url: str) -> str:
    print(f"[*] Navigating to: {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            bypass_csp=True
        )
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)

            content = await page.evaluate("document.body.innerText")

            links = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('a'))
                    .map(a => a.href)
                    .filter(href => href.includes('job') || href.includes('role') || href.includes('req'))
                    .join('\\n');
            }""")

            return f"--- PAGE TEXT ---\n{content}\n\n--- RELEVANT LINKS ---\n{links}"

        except Exception as e:
            print(f"[!] Error scraping {url}: {e}")
            return ""
        finally:
            await browser.close()


def save_raw(content: str, user: str, url: str):
    if not content.strip():
        print("[!] Empty content — nothing to save.")
        return

    output_dir = f".tmp/{user}"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "raw_job.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"SOURCE_URL: {url}\n\n")
        f.write(content)

    print(f"[*] Raw content saved to: {output_file}")


async def main():
    parser = argparse.ArgumentParser(description="Playwright scraper — raw text output only")
    parser.add_argument("--url", required=True, help="Job posting URL")
    parser.add_argument("--user", default="chase_lavalley", help="User ID")
    args = parser.parse_args()

    content = await scrape_page_content(args.url)
    save_raw(content, args.user, args.url)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[!] Interrupted.")