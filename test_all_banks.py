import requests
import urllib3
urllib3.disable_warnings()

banks_to_test = [
    # ==========================================
    # CENTRAL BANK & COMMON PORTALS
    # ==========================================
    ("Bangladesh Bank Career", "https://www.bb.org.bd/en/index.php/career"),
    ("BB eRecruitment (For all State/Govt Banks)", "https://erecruitment.bb.org.bd/onlineapp/joblist.php"),

    # ==========================================
    # SCHEDULED BANKS (63 TOTAL)
    # ==========================================
    
    # --- State-Owned Commercial Banks (SOCBs) (6) ---
    ("Sonali Bank PLC", "https://www.sonalibank.com.bd/career.php"),
    ("Janata Bank PLC", "https://www.jb.com.bd/site/page/career"),
    ("Agrani Bank PLC", "https://www.agranibank.org/index.php/home/career"),
    ("Rupali Bank PLC", "https://www.rupalibank.com.bd"),
    ("BASIC Bank PLC", "https://www.basicbanklimited.com/career"),
    ("Bangladesh Development Bank (BDBL)", "https://www.bdbl.com.bd/career"),

    # --- Specialized Development Banks (SDBs) (3) ---
    ("Bangladesh Krishi Bank (BKB)", "https://www.krishibank.org.bd/career"),
    ("Rajshahi Krishi Unnayan Bank (RAKUB)", "https://rakub.org.bd/recruitment.php"),
    ("Probashi Kollyan Bank", "http://www.pkb.gov.bd/site/view/career_circular"),

    # --- Private Commercial Banks - Conventional (33) ---
    ("AB Bank PLC", "https://abbl.com/career"),
    ("Bangladesh Commerce Bank", "https://www.bcblbd.com/career"),
    ("Bank Asia PLC", "https://www.bankasia-bd.com/career"),
    ("BRAC Bank PLC", "https://www.bracbank.com/en/career"),
    ("Bengal Commercial Bank", "https://www.bgcb.com.bd/career"),
    ("Citizens Bank PLC", "https://www.citizensbankbd.com/career"),
    ("The City Bank PLC", "https://www.thecitybank.com/career"),
    ("Community Bank Bangladesh PLC", "https://www.communitybankbd.com/career"),
    ("Dhaka Bank PLC", "https://www.dhakabankltd.com/career"),
    ("Dutch-Bangla Bank (DBBL)", "https://www.dutchbanglabank.com/career/career-at-dbbl.html"),
    ("Eastern Bank PLC (EBL)", "https://www.ebl.com.bd/career"),
    ("IFIC Bank PLC", "https://www.ificbank.com.bd/career"),
    ("Jamuna Bank PLC", "https://www.jamunabankbd.com/career"),
    ("Meghna Bank PLC", "https://www.meghnabank.com.bd/career"),
    ("Mercantile Bank PLC", "https://www.mblbd.com/home/career"),
    ("Midland Bank PLC", "https://www.midlandbankbd.net/career"),
    ("Modhumoti Bank PLC", "https://www.modhumotibank.ltd/career"),
    ("Mutual Trust Bank (MTB)", "https://www.mutualtrustbank.com/career"),
    ("National Bank PLC", "https://www.nblbd.com/career"),
    ("NCC Bank PLC", "https://www.nccbank.com.bd/career.php"),
    ("NRB Bank PLC", "https://www.nrbbankbd.com/career"),
    ("NRBC Bank PLC", "https://www.nrbcommercialbank.com/career"),
    ("ONE Bank PLC", "https://www.onebank.com.bd/career"),
    ("Padma Bank PLC", "https://www.padmabankbd.com/career"),
    ("Premier Bank PLC", "https://www.premierbankltd.com/career"),
    ("Prime Bank PLC", "https://www.primebank.com.bd/career"),
    ("Pubali Bank PLC", "https://www.pubalibangla.com/career"),
    ("SBAC Bank PLC", "https://www.sbacbank.com/career"),
    ("Shimanto Bank PLC", "https://www.shimantobank.com/career"),
    ("Southeast Bank PLC", "https://www.southeastbank.com.bd/career"),
    ("Trust Bank PLC", "https://www.tblbd.com/career"),
    ("United Commercial Bank (UCB)", "https://www.ucb.com.bd/career"),
    ("Uttara Bank PLC", "https://www.uttarabank-bd.com/index.php/career"),

    # --- Private Commercial Banks - Islami Shariah Based (10) ---
    ("Islami Bank Bangladesh PLC (IBBL)", "https://www.islamibankbd.com/career.php"),
    ("Al-Arafah Islami Bank", "https://www.aibl.com.bd/career"),
    ("Social Islami Bank (SIBL)", "https://www.siblbd.com/career"),
    ("First Security Islami (FSIBL)", "https://www.fsiblbd.com/career"),
    ("Shahjalal Islami Bank (SJIBL)", "https://www.sjiblbd.com/career.php"),
    ("EXIM Bank", "https://www.eximbankbd.com/career"),
    ("Union Bank PLC", "https://www.unionbank.com.bd/career"),
    ("Global Islami Bank", "https://www.globalislamibankbd.com/career"),
    ("ICB Islamic Bank", "https://www.icbislamic-bank.com/career"),
    ("Standard Bank PLC (Islamic)", "https://www.standardbankbd.com/Career"),

    # --- Foreign Commercial Banks in BD (9) ---
    ("Standard Chartered Bangladesh", "https://www.sc.com/bd/careers/"),
    ("Commercial Bank of Ceylon BD", "https://www.combank.net/bangladesh/careers"),
    ("HSBC Bangladesh", "https://www.hsbc.com.bd/1/2/careers"),
    ("State Bank of India (BD)", "https://bd.statebank/careers"),
    ("Habib Bank Limited (HBL BD)", "https://www.hbl.com/bangladesh/careers"),
    ("Woori Bank BD", "https://go.wooribank.com/bd/en/bi/cs/rcrtiInfo.do"),
    ("Bank Alfalah (BD)", "https://www.bankalfalah.com/bd/careers/"),
    ("Citibank N.A. (BD)", "https://careers.citi.com/"), 
    ("National Bank of Pakistan (BD)", "https://www.nbp.com.pk/Careers/"),
    
    # --- Digital Banks (2) ---
    ("Nagad Digital Bank PLC", "https://nagad.com.bd/career"),
    ("Kori Digital Bank PLC", "https://www.kori.com.bd/"),

    # ==========================================
    # NON-SCHEDULED BANKS (5 TOTAL)
    # ==========================================
    ("Ansar-VDP Unnayan Bank", "http://www.ansarvdpbank.gov.bd/site/view/career_circular"),
    ("Karmasangsthan Bank", "http://www.karmasangsthanbank.gov.bd/site/view/career_circular"),
    ("Grameen Bank", "https://grameenbank.org.bd/career"),
    ("Jubilee Bank", "http://jubileebankbd.com/career"),
    ("Palli Sanchay Bank", "http://www.pallisanchaybank.gov.bd/site/page/career"),

    # ==========================================
    # NON-BANK FINANCIAL INSTITUTIONS (35 TOTAL)
    # ==========================================
    ("Agrani SME Financing", "http://www.agranisme.gov.bd/career"),
    ("Alliance Finance PLC", "https://www.lankanalliance.com/career"),
    ("Aviva Finance Limited", "https://www.avivafinance.com.bd/career"),
    ("Bangladesh Finance Limited", "https://www.bdfinance.com.bd/career"),
    ("BIFC", "https://bifcol.com/career/"),
    ("BIFFL", "https://biffl.org.bd/career"),
    ("Bay Leasing & Investment", "http://www.blilbd.com/career"),
    ("CVC Finance PLC", "https://www.cvcflbd.com/"),
    ("DBH Finance PLC", "https://www.dbhfinance.com/career"),
    ("Fareast Finance & Investment", "https://www.ffilbd.com/"),
    ("FAS Finance & Investment", "https://www.fasbd.com/"),
    ("First Finance Limited", "https://www.first-finance.com.bd/"),
    ("GSP Finance", "http://www.gspfinance.com/career"),
    ("Hajj Finance", "http://www.hajjfinance.net/career"),
    ("IDLC Finance PLC", "https://idlc.com/career.php"),
    ("IIDFC PLC", "http://www.iidfc.com/career"),
    ("IDCOL", "https://idcol.org/home/career"),
    ("International Leasing (ILFSL)", "http://www.ilfsl.com/career"),
    ("IPDC Finance Ltd", "https://www.ipdcbd.com/career"),
    ("Islamic Finance (IFIL)", "http://www.ifilbd.com/career"),
    ("LankaBangla Finance PLC", "https://www.lankabangla.com/career"),
    ("Meridian Finance", "http://www.meridianfinancebd.com/career"),
    ("MIDAS Financing PLC", "http://www.mfl.com.bd/career"),
    ("National Finance PLC", "http://www.nfl.com.bd/career"),
    ("National Housing Finance", "http://www.nationalhousingbd.com/career"),
    ("People's Leasing", "http://www.plfsbd.com/career"),
    ("Phoenix Finance", "http://phoenixfinance.com.bd/career"),
    ("Premier Leasing & Finance", "http://www.premierleasing.com.bd/career"),
    ("Prime Finance & Investment", "http://www.primefinancebd.com/career"),
    ("SABINCO", "http://www.sabinco.com.bd/career"),
    ("SFIL Finance PLC", "http://www.sfilbd.com/career"),
    ("UAE-Bangladesh (UBICO)", "https://ubinco.com/"),
    ("Union Capital Limited", "http://www.unicap-bd.com/career"),
    ("United Finance Limited", "http://www.ulc.com.bd/career"),
    ("Uttara Finance", "http://www.uttarafinance.biz/career"),
]

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
}

results = []
for name, url in banks_to_test:
    try:
        r = requests.get(url, headers=headers, verify=False, timeout=6, allow_redirects=True)
        results.append((name, url, r.status_code, len(r.text)))
        print(f"[{r.status_code}] {name} ({len(r.text)} bytes) -> {r.url[:60]}")
    except Exception as e:
        results.append((name, url, "ERR", str(e)[:40]))
        print(f"[ERR] {name} -> {str(e)[:50]}")

ok = [r for r in results if r[2] == 200]
print(f"\nSummary: {len(ok)} of {len(banks_to_test)} responded with HTTP 200 OK!")
