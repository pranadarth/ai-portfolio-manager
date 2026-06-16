from __future__ import annotations

import json
import os
import re
from typing import Any

from groq import Groq


DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def _format_holdings(snapshot: dict) -> str:
    holdings = snapshot.get("holdings", [])
    lines = []
    for h in sorted(holdings, key=lambda x: x.get("pnl", 0.0), reverse=True):
        lines.append(
            "- {symbol} | {asset_type} | Qty {qty} | Entry ₹{avg_price:.2f} | "
            "Current ₹{current_price:.2f} | P/L ₹{pnl:.2f} ({pnl_pct:.2f}%)".format(
                symbol=h.get("symbol", ""),
                asset_type=h.get("asset_type", ""),
                qty=float(h.get("qty", 0.0)),
                avg_price=float(h.get("avg_price", 0.0)),
                current_price=float(h.get("current_price", 0.0)),
                pnl=float(h.get("pnl", 0.0)),
                pnl_pct=float(h.get("pnl_pct", 0.0)),
            )
        )
    return "\n".join(lines)


def _extract_json(text: str) -> dict[str, Any]:
    """
    Groq should return JSON only, but this parser is defensive.
    """
    if not text:
        return {}

    cleaned = text.strip()

    # Remove code fences if the model ignores instructions.
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try to recover the first JSON object from the response.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}

    return {}


def _fallback_decision(snapshot: dict) -> dict[str, Any]:
    return {
        "regime": "neutral",
        "headline": "Fallback mode active: AI decision engine could not generate a structured response.",
        "actions": [
            {
                "ticker": "ALL",
                "decision": "HOLD",
                "amount_inr": 0,
                "reason": "Fallback safety mode. Preserve current positions until a valid model response is available.",
                "conviction": 10,
                "risk": "Low",
                "expected_edge": "Capital preservation",
            }
        ],
        "watchlist": [],
        "portfolio_commentary": "No AI recommendation available. Portfolio remains unchanged.",
    }


def get_ai_decision(snapshot: dict) -> dict[str, Any]:
    """
    Recommendation-only engine.

    It returns structured suggestions but does not modify the ledger.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _fallback_decision(snapshot)

    client = Groq(api_key=api_key)

    portfolio_text = _format_holdings(snapshot)
    total_value = float(snapshot.get("total_value", 0.0))
    cash_balance = float(snapshot.get("cash_balance", 0.0))
    overall_pnl = float(snapshot.get("overall_pnl", 0.0))
    overall_return_pct = float(snapshot.get("overall_return_pct", 0.0))

    prompt = f"""
You are an autonomous AI Portfolio Manager operating from India.

Your job is to analyze the portfolio and return recommendation-only output.
Do NOT write markdown.
Do NOT explain your reasoning outside the JSON.
Do NOT include code fences.
Return strict JSON only.

Core rules:
- Higher long-term aggresive returns are preferred.
- Cash is a valid position.
- Never force trades.
- Prefer preservation during uncertainty.
- Concentrate only when conviction is high.
- Avoid naked option gambling.
- If no strong edge exists, return HOLD.

Return this JSON schema:

{{
  "regime": "risk_on | neutral | risk_off",
  "headline": "one-line summary",
  "actions": [
    {{
      "ticker": "string",
      "decision": "BUY | SELL | HOLD",
      "amount_inr": number,
      "reason": "string",
      "conviction": number,
      "risk": "Low | Medium | High",
      "expected_edge": "string"
    }}
  ],
  "watchlist": ["string", "string"],
  "portfolio_commentary": "string"
}}

Portfolio snapshot:
- Total value: ₹{total_value:.2f}
- Cash: ₹{cash_balance:.2f}
- Overall P/L: ₹{overall_pnl:.2f}
- Return %: {overall_return_pct:.2f}%

Holdings:
{portfolio_text}
""".strip()

    try:
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", DEFAULT_MODEL),
            messages=[
                {
                    "role": "system",
                    "content": "Return strict JSON only. No markdown, no code fences, no extra commentary.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=900,
        )

        content = response.choices[0].message.content or ""
        parsed = _extract_json(content)

        if not parsed:
            return _fallback_decision(snapshot)

        # Normalize keys so the report code can rely on them.
        parsed.setdefault("regime", "neutral")
        parsed.setdefault("headline", "")
        parsed.setdefault("actions", [])
        parsed.setdefault("watchlist", [])
        parsed.setdefault("portfolio_commentary", "")
        return parsed

    except Exception:
        return _fallback_decision(snapshot)