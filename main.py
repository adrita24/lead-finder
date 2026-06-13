import os, sys, logging
from dotenv import load_dotenv
from pipeline import run_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)

def main():
    load_dotenv()
    apify_token = os.getenv("APIFY_API_TOKEN", "").strip()
    prospeo_key = os.getenv("PROSPEO_API_KEY", "").strip()
    if not apify_token or not prospeo_key:
        print("Set APIFY_API_TOKEN and PROSPEO_API_KEY in .env")
        sys.exit(1)

    leads = run_pipeline(apify_token, prospeo_key)

    print("\n" + "="*50)
    print("OPEN TO WORK LEADS")
    print("="*50)
    for lead in leads:
        print(f"\n{lead}\n" + "-"*50)
    print(f"\nTOTAL LEADS FOUND: {len(leads)}")

if __name__ == "__main__":
    main()