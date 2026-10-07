import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from scrapers.bdjobs_scraper import BdjobsScraper
from scrapers.portal_scraper import PortalScraper

print("=" * 60)
print("TESTING ALL 5 JOB PORTALS & AGGREGATORS")
print("=" * 60)

# 1. Bdjobs
print("\n--- 1. Testing Bdjobs Scraper ---")
bdjobs = BdjobsScraper()
bdjobs_jobs = bdjobs.scrape_all_categories()
print(f"✅ Bdjobs: Found {len(bdjobs_jobs)} jobs")
for j in bdjobs_jobs[:4]:
    print(f"  * {j['title']} @ {j['organization']} | Deadline: {j['deadline']} | URL: {j['url']}")

# 2. Portal Scraper (LinkedIn, BDJobsToday, Chakrir Khobor, Skill Jobs)
print("\n--- 2. Testing Portal Scraper ---")
portal = PortalScraper()

print("\nTesting LinkedIn...")
li_jobs = portal.scrape_linkedin()
print(f"✅ LinkedIn: Found {len(li_jobs)} jobs")
for j in li_jobs[:3]:
    print(f"  * {j['title']} @ {j['organization']} | URL: {j['url']}")

print("\nTesting BDJobsToday...")
bjt_jobs = portal.scrape_bdjobstoday()
print(f"✅ BDJobsToday: Found {len(bjt_jobs)} jobs")
for j in bjt_jobs[:3]:
    print(f"  * {j['title']} @ {j['organization']} | Deadline: {j['deadline']} | URL: {j['url']}")

print("\nTesting Chakrir Khobor...")
ck_jobs = portal.scrape_chakrir_khobor()
print(f"✅ Chakrir Khobor: Found {len(ck_jobs)} jobs")
for j in ck_jobs[:3]:
    print(f"  * {j['title']} @ {j['organization']} | URL: {j['url']}")

print("\nTesting Skill Jobs...")
sj_jobs = portal.scrape_skilljobs()
print(f"✅ Skill Jobs: Found {len(sj_jobs)} jobs")
for j in sj_jobs[:3]:
    print(f"  * {j['title']} @ {j['organization']} | URL: {j['url']}")

total = len(bdjobs_jobs) + len(li_jobs) + len(bjt_jobs) + len(ck_jobs) + len(sj_jobs)
print("\n" + "=" * 60)
print(f"TOTAL VERIFIED JOBS FOUND ACROSS ALL 5 PORTALS: {total}")
print("=" * 60)
