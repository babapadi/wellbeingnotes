import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright

# ====================== CONFIG ======================
TOTAL_BOTS = 400          # ← Change this number easily
MAX_CONCURRENT = 12        # How many browsers at the same time
MIN_TIME = 10             # Minimum seconds on the page
MAX_TIME = 15             # Maximum seconds on the page
TOTAL_HOURS = 5          # Spread bots over this many hours
VISITS_PER_BOT = (2, 3)   # Each bot visits the page 2 or 3 times
# ====================================================

def load_page():
    pages = [line.strip() for line in Path("pages.txt").read_text().splitlines() if line.strip()]
    if not pages:
        raise Exception("No page found in pages.txt")
    return pages[0]

async def run_one_bot(browser, page_url, bot_id):
    context = await browser.new_context(
        user_agent=random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        ]),
        viewport={"width": random.randint(1200, 1920), "height": random.randint(800, 1080)}
    )
    page = await context.new_page()

    try:
        visits = random.randint(*VISITS_PER_BOT)

        for visit in range(visits):
            try:
                await page.goto(page_url, wait_until="domcontentloaded", timeout=30000)

                # Stay on the page for 10–15 seconds
                await page.wait_for_timeout(random.randint(MIN_TIME, MAX_TIME) * 1000)

                # Light human-like scroll
                await page.mouse.wheel(0, random.randint(300, 900))
                await page.wait_for_timeout(random.randint(800, 2000))

            except Exception as e:
                print(f"Bot {bot_id} visit {visit+1} error: {e}")
                continue

        print(f"✓ Bot {bot_id} finished ({visits} visits)")
    except Exception as e:
        print(f"✗ Bot {bot_id} failed: {e}")
    finally:
        await context.close()

async def main():
    page_url = load_page()
    print(f"Target page: {page_url}")
    print(f"Running {TOTAL_BOTS} bots spread over {TOTAL_HOURS} hours...")

    bots_per_batch = MAX_CONCURRENT
    total_batches = (TOTAL_BOTS + bots_per_batch - 1) // bots_per_batch
    delay_between_batches = (TOTAL_HOURS * 3600) / total_batches

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        for i in range(0, TOTAL_BOTS, bots_per_batch):
            batch_ids = range(i, min(i + bots_per_batch, TOTAL_BOTS))
            tasks = [run_one_bot(browser, page_url, bot_id + 1) for bot_id in batch_ids]
            
            await asyncio.gather(*tasks)

            if i + bots_per_batch < TOTAL_BOTS:
                sleep_time = delay_between_batches + random.uniform(-30, 60)
                sleep_time = max(30, sleep_time)
                print(f"Waiting {int(sleep_time)} seconds before next batch...")
                await asyncio.sleep(sleep_time)

        await browser.close()
        print("All bots completed!")

if __name__ == "__main__":
    asyncio.run(main())
