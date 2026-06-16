from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from portfolio_engine import build_snapshot

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"


def fmt_money(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"₹{v:,.2f}"


def render_report(session: str, snap: dict) -> str:
    holdings = snap["holdings"]

    sorted_by_pnl = sorted(holdings, key=lambda x: x["pnl"], reverse=True)
    winners = sorted_by_pnl[:3]
    losers = sorted_by_pnl[-3:][::-1]

    daily_change = snap["daily_change"]
    daily_change_str = fmt_money(daily_change)
    if daily_change is not None and daily_change >= 0:
        daily_label = f"+{daily_change_str}"
    else:
        daily_label = daily_change_str

    overall_pnl = snap["overall_pnl"]
    overall_pnl_str = fmt_money(overall_pnl)
    if overall_pnl >= 0:
        overall_pnl_label = f"+{overall_pnl_str}"
    else:
        overall_pnl_label = overall_pnl_str

    lines = []
    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %b %Y")

    header = "MORNING PORTFOLIO REPORT" if session == "morning" else "EOD PORTFOLIO REPORT"
    lines.append(f"# DAY REPORT — {header}")
    lines.append(f"**Date:** {today}")
    lines.append("")

    lines.append("## 1. EOD Portfolio Snapshot" if session == "eod" else "## 1. Portfolio Snapshot")
    lines.append("")
    lines.append(f"Closing Portfolio Value: {fmt_money(snap['total_value'])}")
    lines.append(f"Initial Capital Base: {fmt_money(snap['total_contributed'])}")
    lines.append(f"Net Daily Movement: {daily_label}")
    lines.append(f"Total Return (Since Day 1): {snap['overall_return_pct']:.2f}%")
    lines.append(f"Cash Balance (Broker Ledger): {fmt_money(snap['cash_balance'])}")
    lines.append(f"Invested War Chest: {fmt_money(snap['invested_war_chest'])}")
    lines.append("")

    lines.append("## 2. Real Market / Portfolio Performance")
    lines.append("")
    lines.append(
        "This report is generated from the live valuation engine. "
        "If a market price could not be fetched, the system falls back to the last known usable value."
    )
    lines.append("")

    lines.append("### Top Winners")
    for h in winners:
        lines.append(
            f"- {h['symbol']}: {fmt_money(h['pnl'])} ({h['pnl_pct']:.2f}%)"
        )
    lines.append("")
    lines.append("### Top Losers")
    for h in losers:
        lines.append(
            f"- {h['symbol']}: {fmt_money(h['pnl'])} ({h['pnl_pct']:.2f}%)"
        )
    lines.append("")

    lines.append("## 3. Holdings Ledger (Fully Reconciled)")
    lines.append("")
    lines.append("| Asset | Type | Qty | Avg Entry | Current | Invested | Current Value | P/L | P/L % |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for h in holdings:
        lines.append(
            f"| {h['symbol']} | {h['asset_type']} | {h['qty']:.8f}".rstrip("0").rstrip(".")
            + f" | {fmt_money(h['avg_price'])} | {fmt_money(h['current_price'])} | "
            + f"{fmt_money(h['invested_value'])} | {fmt_money(h['current_value'])} | "
            + f"{fmt_money(h['pnl'])} | {h['pnl_pct']:.2f}% |"
        )
    lines.append("")

    lines.append("## 4. Tactical Manager Summary")
    lines.append("")
    lines.append("Action: HOLD all positions.")
    lines.append("Reason: The engine is currently in valuation-only mode; trading logic will be added after the reporting pipeline is stable.")
    lines.append(f"Conviction: 10/10 for accuracy, 0/10 for forced trading.")
    lines.append("")

    lines.append("## 5. Risk Assessment")
    lines.append("")
    lines.append("- Portfolio risk: Medium")
    lines.append("- Main threats: price-feed failures, stale NAVs, and inconsistent source mappings")
    lines.append("- Protection: cash reserve, arbitrage, liquid sleeve, and source fallbacks")
    lines.append("")

    lines.append("## 6. Next Action")
    lines.append("")
    lines.append("If this report looks correct, the next phase is to add a rule-based decision engine for BUY / SELL / HOLD.")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", choices=["morning", "eod"], default="eod")
    args = parser.parse_args()

    snap = build_snapshot()
    report = render_report(args.session, snap)

    today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")
    out = REPORTS / f"{today}-{args.session}.md"
    out.write_text(report, encoding="utf-8")

    print(f"Wrote {out}")


if __name__ == "__main__":
    main()