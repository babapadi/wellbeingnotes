import asyncio
import random
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright

# ====================== CONFIG ======================
TOTAL_BOTS = 400          # Total bots to run
MAX_CONCURRENT = 12       # Increased to safely fit in 5 hours
MIN_TIME = 10             # Minimum seconds on the final page
MAX_TIME = 15             # Maximum seconds on the final page
TOTAL_HOURS = 5           # Fits comfortably under GitHub's 6hr limit
VISITS_PER_BOT = (2, 3)   # Visits per bot
MAX_PROXY_RETRIES = 5     # Times a bot will swap broken proxies before giving up
# ====================================================

def load_page():
    pages = [line.strip() for line in Path("pages.txt").read_text().splitlines() if line.strip()]
    if not pages:
        raise Exception("No page found in pages.txt")
    return pages[0]

def fetch_live_proxies():
    print("🌐 Downloading fresh public proxy list...")
    try:
        # Pulls live verified SOCKS5 proxies compiled hourly
        url = "https://jsdelivr.net"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            proxies = [f"socks5://{line.strip()}" for line in response.read().decode('utf-8').splitlines() if line.strip()]
        print(f"📡 Successfully loaded {len(proxies)} public SOCKS5 proxies into rotation pool.")
        return proxies
    except Exception as e:
        print(f"⚠️ Failed to fetch public proxy feed: {e}. Running without proxies.")
        return []

# Initialize the global proxy pool
PROXY_POOL = fetch_live_proxies()

async def run_one_bot(playwright_object, page_url, bot_id):
    visits = random.randint(*VISITS_PER_BOT)
    
    for visit in range(visits):
        success = False
        retries = 0
        
        while not success and retries < MAX_PROXY_RETRIES:
            # Pick a fresh proxy from the pool for this attempt
            proxy_server = random.choice(PROXY_POOL) if PROXY_POOL else None
            proxy_config = {"server": proxy_server} if proxy_server else None
            
            # Setup a unique browser context for this specific attempt
            context = await playwright_object.chromium.launch_persistent_context(
                user_data_dir=f"/tmp/playwright_profile_bot_{bot_id}_{visit}_{retries}",
                headless=True,
                user_agent=random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
                ]),
                viewport={"width": random.randint(1200, 1920), "height": random.randint(800, 1080)},
                proxy=proxy_config
            )
            
            page = await context.new_page()
            
            try:
                print(f"🤖 Bot {bot_id} (Visit {visit+1}/{visits}) -> Attempting proxy {proxy_server} (Retry {retries}/{MAX_PROXY_RETRIES})...")
                
                # 45-second timeout to handle slow public proxies
                await page.goto(page_url, wait_until="networkidle", timeout=45000)
                
                print(f"🔗 Bot {bot_id} landed successfully on final page! Viewing...")
                await page.wait_for_timeout(random.randint(MIN_TIME, MAX_TIME) * 1000)
                
                # Human behavior simulation
                await page.mouse.wheel(0, random.randint(300, 900))
                await page.wait_for_timeout(random.randint(800, 2000))
                
                success = True  # Break out of the retry loop for this visit
                
            except Exception as e:
                retries += 1
                print(f"⚠️ Proxy failed or timed out for Bot {bot_id} on visit {visit+1}. Swapping proxy... Error: {str(e)[:60]}")
            finally:
                await context.close()
                
        if not success:
            print(f"✗ Bot {bot_id} gave up on visit {visit+1} after failing {MAX_PROXY_RETRIES} consecutive proxies.")

    print(f"✓ Bot {bot_id} sequence finalized.")

async def main():
    page_url = load_page()
    print(f"🎯 Target Smartlink URL: {page_url}")
    print(f"🚀 Spawning {TOTAL_BOTS} automated bots over a {TOTAL_HOURS}-hour execution window...")

    bots_per_batch = MAX_CONCURRENT
    total_batches = (TOTAL_BOTS + bots_per_batch - 1) // bots_per_batch
    delay_between_batches = (TOTAL_HOURS * 3600) / total_batches

    async with async_playwright() as p:
        for i in range(0, TOTAL_BOTS, bots_per_batch):
            batch_ids = range(i, min(i + bots_per_batch, TOTAL_BOTS))
            
            # Execute the batch concurrently
            tasks = [run_one_bot(p, page_url, bot_id + 1) for bot_id in batch_ids]
            await asyncio.gather(*tasks)

            if i + bots_per_batch < TOTAL_BOTS:
                sleep_time = delay_between_batches + random.uniform(-20, 45)
                sleep_time = max(15, sleep_time)
                print(f"💤 Batch complete. Sleeping for {int(sleep_time)} seconds before launching next batch...")
                await asyncio.sleep(sleep_time)

        print("🎉 Sequence complete. All batches processed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
