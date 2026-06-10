from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent
PROJECT_DIR = DATA_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.loaders import load_purchases_data, load_ads_data
from src.metrics import calculate_cac

PURCHASES_FILE = DATA_DIR / "source_data" / "purchases.csv"
ADS_DIR = DATA_DIR / "source_data"
OUTPUT_FILE = DATA_DIR / "calculations" / "cac.csv"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

purchases = load_purchases_data(PURCHASES_FILE)
ads = load_ads_data(ADS_DIR)
cac = calculate_cac(purchases, ads)

cac.to_csv(OUTPUT_FILE, index=False, mode="w")
print(f"Saved: {OUTPUT_FILE}")
print("Rows in CAC:", len(cac))
print(cac.head(20))