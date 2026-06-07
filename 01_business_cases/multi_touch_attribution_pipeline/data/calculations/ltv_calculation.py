from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent
PROJECT_DIR = DATA_DIR.parent
sys.path.insert(0, str(PROJECT_DIR))

from src.loaders import load_purchases_data
from src.metrics import calculate_ltv

PURCHASES_FILE = DATA_DIR / "purchases" / "purchases.csv"
OUTPUT_FILE = DATA_DIR / "calculations" / "ltv.csv"
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

purchases = load_purchases_data(PURCHASES_FILE)
ltv = calculate_ltv(purchases)

ltv.to_csv(OUTPUT_FILE, index=False)
print(f"Saved: {OUTPUT_FILE}")
print("Rows in LTV:", len(ltv))
print(ltv.head(20))