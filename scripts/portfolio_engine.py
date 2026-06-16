from __future__ import annotations

import csv
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fetch_prices import fetch_price_for_holding

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORTS = ROOT / "reports"


@dataclass
class ValuedHolding:
    symbol: str
    asset_type: str
    qty: float
    avg_price: float
    current_price: float
    invested_value: float
    current_value: float
    pnl: float
    pnl_pct: float
    price_source: str = ""
    source_id: str = ""


def read_csv_dicts(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_cash_balance() -> float:
    cash_path = DATA / "cash.csv"
    with cash_path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
        if not rows:
            return 0.0
        # support either:
        # Cash
        # 11394
        # or cash_balance,11394
        if len(rows) == 1 and len(rows[0]) == 2:
            return float(rows[0][1])
        if len(rows) >= 2:
            try:
                return float(rows[1][0])
            except Exception:
                pass
        return float(rows[0][-1])


def read_cashflows_total() -> float:
    path = DATA / "cashflows.csv"
    if not path.exists():
        return 0.0

    total = 0.0
    with path.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        for r in rows:
            try:
                total += float(r["Amount"])
            except Exception:
                continue
    return total


def previous_snapshot_value() -> float | None:
    path = DATA / "portfolio_snapshot.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return float(data.get("total_value"))
    except Exception:
        return None


def build_snapshot() -> dict:
    holdings_path = DATA / "holdings.csv"
    raw_holdings = read_csv_dicts(holdings_path)
    cash_balance = read_cash_balance()
    total_contributed = read_cashflows_total()

    valued: list[ValuedHolding] = []
    for row in raw_holdings:
        qty = float(row.get("qty") or 0)
        avg_price = float(row.get("avg_price") or 0)
        current_price = fetch_price_for_holding(row)

        # Fallback to avg price if fetch fails
        if current_price is None:
            current_price = avg_price

        invested_value = qty * avg_price
        current_value = qty * current_price
        pnl = current_value - invested_value
        pnl_pct = (pnl / invested_value * 100.0) if invested_value else 0.0

        valued.append(
            ValuedHolding(
                symbol=row.get("symbol", ""),
                asset_type=row.get("asset_type", ""),
                qty=qty,
                avg_price=avg_price,
                current_price=current_price,
                invested_value=invested_value,
                current_value=current_value,
                pnl=pnl,
                pnl_pct=pnl_pct,
                price_source=row.get("price_source", ""),
                source_id=row.get("source_id", ""),
            )
        )

    holdings_value = sum(h.current_value for h in valued)
    total_value = holdings_value + cash_balance
    overall_pnl = total_value - total_contributed
    daily_change = None

    prev = previous_snapshot_value()
    if prev is not None:
        daily_change = total_value - prev

    snapshot = {
        "generated_at_ist": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "total_contributed": round(total_contributed, 2),
        "cash_balance": round(cash_balance, 2),
        "holdings_value": round(holdings_value, 2),
        "total_value": round(total_value, 2),
        "overall_pnl": round(overall_pnl, 2),
        "overall_return_pct": round((overall_pnl / total_contributed * 100.0) if total_contributed else 0.0, 2),
        "daily_change": None if daily_change is None else round(daily_change, 2),
        "invested_war_chest": round(total_contributed - cash_balance, 2),
        "holdings": [asdict(h) for h in valued],
    }

    # Save snapshot for later comparison
    (DATA / "portfolio_snapshot.json").write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Save valued holdings CSV for easy inspection
    valued_csv = DATA / "valued_holdings.csv"
    with valued_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "symbol",
                "asset_type",
                "qty",
                "avg_price",
                "current_price",
                "invested_value",
                "current_value",
                "pnl",
                "pnl_pct",
                "price_source",
                "source_id",
            ]
        )
        for h in valued:
            writer.writerow(
                [
                    h.symbol,
                    h.asset_type,
                    f"{h.qty:.8f}".rstrip("0").rstrip("."),
                    f"{h.avg_price:.2f}",
                    f"{h.current_price:.2f}",
                    f"{h.invested_value:.2f}",
                    f"{h.current_value:.2f}",
                    f"{h.pnl:.2f}",
                    f"{h.pnl_pct:.2f}",
                    h.price_source,
                    h.source_id,
                ]
            )

    return snapshot


if __name__ == "__main__":
    snap = build_snapshot()
    print(json.dumps(snap, indent=2, ensure_ascii=False))