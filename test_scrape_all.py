import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from config.banks import BANKS
from scrapers.career_page_scraper import CareerPageScraper

scraper = CareerPageScraper()
total_found = 0
found_jobs = []

for b in BANKS:
    if b.get('short_name') == 'BB_BSCS':
        continue
    try:
        jobs = scraper.scrape(b)
        if jobs:
            print(f"[FOUND {len(jobs)}] {b['name']}")
            for j in jobs:
                print(f"   * {j['title']} | {j['url']}")
                found_jobs.append(j)
            total_found += len(jobs)
    except Exception as e:
        pass

print(f"\nTotal found from individual banks: {total_found}")
