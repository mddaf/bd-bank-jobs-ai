"""
Bank & Financial Institution Registry
=======================================
Defines all target organizations with their career page URLs
and scraping configurations.

Each bank entry contains:
  - name: Official name
  - short_name: Abbreviated identifier
  - type: Category (state_owned | private | nbfi | govt_institution | specialized)
  - career_url: Direct link to career/jobs page
  - scrape_config: CSS selectors & parsing rules for that site
  - enabled: Whether to actively monitor (toggle off if broken)
"""

BANKS = [
    # ================================================================
    # STATE-OWNED COMMERCIAL BANKS
    # ================================================================
    {
        "name": "Bangladesh Bank",
        "short_name": "BB",
        "type": "central_bank",
        "career_url": "https://www.bb.org.bd/en/index.php/career",
        "scrape_config": {
            "method": "html",
            "job_container": "table.table tbody tr",
            "title_selector": "td:nth-child(1)",
            "link_selector": "td a",
            "deadline_selector": "td:nth-child(3)",
        },
        "enabled": True,
    },
    {
        "name": "Sonali Bank Limited",
        "short_name": "SBL",
        "type": "state_owned",
        "career_url": "https://www.sonalibank.com.bd/page/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-list .career-item, table.table tbody tr, .content-area a",
            "title_selector": "a, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Janata Bank Limited",
        "short_name": "JBL",
        "type": "state_owned",
        "career_url": "https://www.jb.com.bd/site/page/career",
        "scrape_config": {
            "method": "html",
            "job_container": "table tbody tr, .career-section .career-item",
            "title_selector": "td:first-child a, .title",
            "link_selector": "a",
            "deadline_selector": "td:last-child, .deadline",
        },
        "enabled": True,
    },
    {
        "name": "Agrani Bank Limited",
        "short_name": "ABL",
        "type": "state_owned",
        "career_url": "https://www.agranibank.org/career.php",
        "scrape_config": {
            "method": "html",
            "job_container": "table tbody tr, .career-list li",
            "title_selector": "td:first-child, a",
            "link_selector": "a",
            "deadline_selector": "td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Rupali Bank Limited",
        "short_name": "RBL",
        "type": "state_owned",
        "career_url": "https://www.rupalibank.org/career",
        "scrape_config": {
            "method": "html",
            "job_container": "table tbody tr, .career-item",
            "title_selector": "td:first-child, .title",
            "link_selector": "a",
            "deadline_selector": "td:last-child, .deadline",
        },
        "enabled": True,
    },
    {
        "name": "BASIC Bank Limited",
        "short_name": "BASIC",
        "type": "state_owned",
        "career_url": "https://www.basicbanklimited.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": "table tbody tr, .career-item",
            "title_selector": "td:first-child, a",
            "link_selector": "a",
            "deadline_selector": "td:last-child",
        },
        "enabled": True,
    },
    # ================================================================
    # PRIVATE COMMERCIAL BANKS
    # ================================================================
    {
        "name": "Dutch-Bangla Bank Limited",
        "short_name": "DBBL",
        "type": "private",
        "career_url": "https://www.dutchbanglabank.com/career/career-at-dbbl.html",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-list .career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "BRAC Bank Limited",
        "short_name": "BRAC",
        "type": "private",
        "career_url": "https://www.bracbank.com/en/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-list .career-item, .job-listing .job-item, table tbody tr",
            "title_selector": "h3, .job-title, a, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, .date, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Eastern Bank Limited",
        "short_name": "EBL",
        "type": "private",
        "career_url": "https://www.ebl.com.bd/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr, .job-list li",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "The City Bank Limited",
        "short_name": "CBL",
        "type": "private",
        "career_url": "https://www.thecitybank.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, .job-card, table tbody tr",
            "title_selector": "a, .title, h3, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, .date, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Islami Bank Bangladesh Limited",
        "short_name": "IBBL",
        "type": "private",
        "career_url": "https://www.islamibankbd.com/career.php",
        "scrape_config": {
            "method": "html",
            "job_container": "table tbody tr, .career-item",
            "title_selector": "td:first-child a, .title",
            "link_selector": "a",
            "deadline_selector": "td:last-child, .deadline",
        },
        "enabled": True,
    },
    {
        "name": "Prime Bank Limited",
        "short_name": "PBL",
        "type": "private",
        "career_url": "https://www.primebank.com.bd/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Pubali Bank Limited",
        "short_name": "PUBL",
        "type": "private",
        "career_url": "https://www.pubalibangla.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": "table tbody tr, .career-item",
            "title_selector": "td:first-child, a, .title",
            "link_selector": "a",
            "deadline_selector": "td:last-child, .deadline",
        },
        "enabled": True,
    },
    {
        "name": "Mutual Trust Bank Limited",
        "short_name": "MTB",
        "type": "private",
        "career_url": "https://www.mutualtrustbank.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Bank Asia Limited",
        "short_name": "BAL",
        "type": "private",
        "career_url": "https://www.bankasia-bd.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Mercantile Bank Limited",
        "short_name": "MBL",
        "type": "private",
        "career_url": "https://www.mblbd.com/home/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Standard Bank Limited",
        "short_name": "STBL",
        "type": "private",
        "career_url": "https://www.standardbankbd.com/Career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Southeast Bank Limited",
        "short_name": "SEBL",
        "type": "private",
        "career_url": "https://www.southeastbank.com.bd/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "NCC Bank Limited",
        "short_name": "NCCBL",
        "type": "private",
        "career_url": "https://www.nccbank.com.bd/career.php",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "ONE Bank Limited",
        "short_name": "OBL",
        "type": "private",
        "career_url": "https://www.onebank.com.bd/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "United Commercial Bank Limited",
        "short_name": "UCBL",
        "type": "private",
        "career_url": "https://www.ucb.com.bd/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "National Bank Limited",
        "short_name": "NBL",
        "type": "private",
        "career_url": "https://www.nblbd.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Dhaka Bank Limited",
        "short_name": "DHB",
        "type": "private",
        "career_url": "https://www.dhakabankltd.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    # ================================================================
    # NON-BANK FINANCIAL INSTITUTIONS (NBFIs)
    # ================================================================
    {
        "name": "IDCOL",
        "short_name": "IDCOL",
        "type": "govt_institution",
        "career_url": "https://idcol.org/home/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Investment Corporation of Bangladesh",
        "short_name": "ICB",
        "type": "govt_institution",
        "career_url": "https://www.icb.gov.bd/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "Lanka Bangla Finance Limited",
        "short_name": "LBFL",
        "type": "nbfi",
        "career_url": "https://www.lankabangla.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr",
            "title_selector": "a, .title, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, td:last-child",
        },
        "enabled": True,
    },
    {
        "name": "IPDC Finance Limited",
        "short_name": "IPDC",
        "type": "nbfi",
        "career_url": "https://www.ipdcbd.com/career",
        "scrape_config": {
            "method": "html",
            "job_container": ".career-item, table tbody tr, .job-card",
            "title_selector": "a, .title, h3, td:first-child",
            "link_selector": "a",
            "deadline_selector": ".deadline, .date, td:last-child",
        },
        "enabled": True,
    },
]

# ================================================================
# JOB PORTALS — Aggregated sources
# ================================================================
JOB_PORTALS = [
    {
        "name": "bdjobs.com (Banking)",
        "short_name": "BDJOBS",
        "type": "job_portal",
        "career_url": "https://jobs.bdjobs.com/jobsearch.asp?fcatId=8",  # Category 8 = Bank/Non-Bank Fin. Institution
        "scrape_config": {
            "method": "html",
            "job_container": ".job-list-container .job-item, .norm, .topjob-block",
            "title_selector": ".job-title a, .job-title-text, a.title",
            "link_selector": "a",
            "company_selector": ".comp-name, .company-name",
            "deadline_selector": ".job-deadline, .dead-line",
        },
        "enabled": True,
    },
    {
        "name": "chakri.com (Banking)",
        "short_name": "CHAKRI",
        "type": "job_portal",
        "career_url": "https://www.chakri.com/bank-jobs",
        "scrape_config": {
            "method": "html",
            "job_container": ".job-item, .job-card, article",
            "title_selector": "a, h2, h3, .title",
            "link_selector": "a",
            "deadline_selector": ".deadline, .date",
        },
        "enabled": True,
    },
]

# ================================================================
# All sources combined for easy iteration
# ================================================================
ALL_SOURCES = BANKS + JOB_PORTALS

def get_enabled_sources():
    """Return only sources that are currently enabled."""
    return [s for s in ALL_SOURCES if s.get("enabled", True)]

def get_sources_by_type(source_type: str):
    """Filter sources by type (e.g., 'private', 'state_owned', 'nbfi')."""
    return [s for s in ALL_SOURCES if s.get("type") == source_type and s.get("enabled", True)]
