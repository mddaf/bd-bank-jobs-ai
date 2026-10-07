import time
from config.banks import BANKS
from scrapers.career_page_scraper import CareerPageScraper

scraper = CareerPageScraper()
sources = [b for b in BANKS if b.get('short_name') != 'BB_BSCS' and b.get('enabled', True)]
print(f"Testing parallel scraping across {len(sources)} institutions...")
t0 = time.time()
jobs = scraper.scrape_all_concurrent(sources, max_workers=15)
elapsed = time.time() - t0
print(f"Done in {elapsed:.2f} seconds! Discovered {len(jobs)} jobs.")
for j in jobs:
    print(f"  - {j['title']} | {j['organization']} | {j['url']}")
