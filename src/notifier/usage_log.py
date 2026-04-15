import csv
from datetime import datetime

from .constants import CONFIG_DIR
from .plan_usage import PlanUsage

USAGE_CSV_PATH = CONFIG_DIR / "usage.csv"
HEADER = [
    "timestamp",
    "five_hour_pct",
    "five_hour_resets_at",
    "seven_day_pct",
    "seven_day_resets_at",
]


def append_usage_row(usage: PlanUsage) -> None:
    if usage.error:
        return
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    write_header = not USAGE_CSV_PATH.exists()
    with open(USAGE_CSV_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(HEADER)
        w.writerow([
            datetime.now().isoformat(timespec="seconds"),
            f"{usage.five_hour:.2f}" if usage.five_hour >= 0 else "",
            usage.five_hour_resets_at,
            f"{usage.seven_day:.2f}" if usage.seven_day >= 0 else "",
            usage.seven_day_resets_at,
        ])
