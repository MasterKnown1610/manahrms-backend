"""
Product modules that exist in this backend (v1 API). Used for subscription plan feature flags.

Keys must match what you store in subscription_plans.features (boolean map).
Keep in sync with app/api/router.py.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_CEILING
from typing import Any, Optional

# Rough blended cost assumption (INR) per AI chat query at high usage — tune from your OpenAI bill.
_EST_AI_COST_INR_PER_QUERY = Decimal("0.65")
_DEFAULT_TARGET_GROSS_MARGIN_PCT = Decimal("62")  # (price - variable) / price


PRODUCT_MODULES: list[dict[str, Any]] = [
    {
        "key": "employees",
        "label": "Employees",
        "description": "Employee directory, profiles, org structure",
        "category": "Core HR",
    },
    {
        "key": "departments",
        "label": "Departments",
        "description": "Departments and org units",
        "category": "Core HR",
    },
    {
        "key": "tasks",
        "label": "Tasks",
        "description": "Task management and assignments",
        "category": "Work",
    },
    {
        "key": "projects",
        "label": "Projects",
        "description": "Projects and project members",
        "category": "Work",
    },
    {
        "key": "attendance",
        "label": "Attendance",
        "description": "Attendance tracking and records",
        "category": "Core HR",
    },
    {
        "key": "leaves",
        "label": "Leaves",
        "description": "Leave requests and balances",
        "category": "Core HR",
    },
    {
        "key": "dashboard",
        "label": "Dashboard",
        "description": "HR dashboard and summaries",
        "category": "Insights",
    },
    {
        "key": "ai_chat",
        "label": "ManaHRMS AI",
        "description": "AI assistant (uses vector / knowledge sync under the hood)",
        "category": "AI",
    },
    {
        "key": "chat",
        "label": "Team chat",
        "description": "Internal messaging and chat rooms",
        "category": "Collaboration",
    },
    {
        "key": "meetings",
        "label": "Meetings",
        "description": "Meetings and participants",
        "category": "Collaboration",
    },
    {
        "key": "events",
        "label": "Events",
        "description": "Company events and calendar events",
        "category": "Collaboration",
    },
    {
        "key": "calendar",
        "label": "Calendar",
        "description": "Unified calendar (meetings + events)",
        "category": "Collaboration",
    },
    {
        "key": "subscriptions",
        "label": "Billing & plans",
        "description": "Company subscription purchase and management (Razorpay)",
        "category": "Platform",
    },
]

MODULE_KEYS: frozenset[str] = frozenset(m["key"] for m in PRODUCT_MODULES)


def default_features_all_false() -> dict[str, bool]:
    return {m["key"]: False for m in PRODUCT_MODULES}


def sanitize_plan_features(features: Optional[dict]) -> Optional[dict]:
    """Keep only implemented module keys; coerce values to bool."""
    if features is None:
        return None
    out: dict[str, bool] = {}
    for k, v in features.items():
        if k in MODULE_KEYS:
            out[k] = bool(v)
    return out


def list_unknown_feature_keys(features: Optional[dict]) -> list[str]:
    if not features:
        return []
    return [k for k in features if k not in MODULE_KEYS]


def estimate_pricing_floor(
    *,
    ai_queries_limit: int,
    target_gross_margin_pct: Decimal = _DEFAULT_TARGET_GROSS_MARGIN_PCT,
    assumed_cost_per_ai_query_inr: Decimal = _EST_AI_COST_INR_PER_QUERY,
    absolute_floor_inr: Decimal = Decimal("29"),
) -> dict[str, Any]:
    """
    Sales-style floor: if every included AI query were used, variable cost should not exceed
    (1 - margin) * price  =>  price >= variable / (1 - margin).

    Does not include infra, support, or payment fees — treat as a sanity check, not full COGS.
    """
    if ai_queries_limit <= 0:
        suggested = absolute_floor_inr
        variable = Decimal("0")
    else:
        variable = Decimal(ai_queries_limit) * assumed_cost_per_ai_query_inr
        one_minus_m = (Decimal("100") - target_gross_margin_pct) / Decimal("100")
        if one_minus_m <= 0:
            one_minus_m = Decimal("0.38")
        raw = variable / one_minus_m
        suggested = max(raw.quantize(Decimal("1"), rounding=ROUND_CEILING), absolute_floor_inr)

    yearly_from_monthly = (suggested * Decimal("12") * Decimal("0.82")).quantize(
        Decimal("0.01")
    )  # ~18% prepay discount

    return {
        "assumed_max_ai_variable_cost_inr_per_user_month": str(variable.quantize(Decimal("0.01"))),
        "target_gross_margin_percent": str(target_gross_margin_pct),
        "suggested_minimum_price_per_user_monthly_inr": str(suggested),
        "suggested_yearly_per_user_inr_if_18pct_prepay_discount": str(yearly_from_monthly),
    }


def pricing_playbook_text() -> dict[str, Any]:
    return {
        "currency": "INR",
        "assumptions": (
            f"AI variable cost model uses ~₹{_EST_AI_COST_INR_PER_QUERY} per query at full usage; "
            "replace with your real OpenAI + embedding average from billing."
        ),
        "margin_target_percent": str(_DEFAULT_TARGET_GROSS_MARGIN_PCT),
        "sales_notes": [
            "Higher ai_queries_limit needs a higher per-seat price or tighter module bundle.",
            "Yearly price is often set to 10–12× monthly; 10× rewards cash upfront, 12× rewards loyalty.",
            "minimum_seats on Growth/Scale protects revenue on small teams.",
            "Add payment gateway (~2%) and support time into price after this AI floor check.",
        ],
    }
