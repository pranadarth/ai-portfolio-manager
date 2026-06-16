from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

CONTRIBUTION_AMOUNT = 35000.0
CONTRIBUTION_DAY = 2  # original rule


def read_cash_balance() -> float:
    path = DATA / "cash.csv"
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        if len(rows) >= 2:
            return float(rows[1][0])
        return float(rows[0][-1])


def write_cash_balance(amount: float) -> None:
    path = DATA / "cash.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Cash"])
        writer.writerow([f"{amount:.2f}"])


def monthly_already_added(yyyymm: str) -> bool:
    path = DATA / "cashflows.csv"
    if not path.exists():
        return False

    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        for r in rows:
            if r.get("Type", "").lower() == "monthly" and r.get("Date", "").startswith(yyyymm):
                return True
    return False


def append_cashflow(date_str: str, amount: float) -> None:
    path = DATA / "cashflows.csv"
    exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists or path.stat().st_size == 0:
            writer.writerow(["Date", "Type", "Amount"])
        writer.writerow([date_str, "Monthly", f"{amount:.2f}"])


def main():
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    if now.day != CONTRIBUTION_DAY:
        print("Not contribution day; exiting.")
        return

    yyyymm = now.strftime("%Y-%m")
    if monthly_already_added(yyyymm):
        print("Monthly contribution already added for this month.")
        return

    cash = read_cash_balance()
    cash += CONTRIBUTION_AMOUNT
    write_cash_balance(cash)
    append_cashflow(now.strftime("%Y-%m-%d"), CONTRIBUTION_AMOUNT)
    print(f"Added {CONTRIBUTION_AMOUNT:.2f}. New cash balance: {cash:.2f}")


if __name__ == "__main__":
    main()