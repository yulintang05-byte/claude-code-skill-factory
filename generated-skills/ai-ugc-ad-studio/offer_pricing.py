"""
Offer & Revenue Model
Builds productized pricing tiers for an AI-video / UGC ad service and computes
the concrete path to revenue goals ($500/week and $10k/month): how many clients
or packs you need, and whether your delivery capacity supports it.

All numbers are illustrative planning aids, not income guarantees.
Standard library only.
"""

from typing import Dict, List, Any


class OfferPricing:
    """Pricing tiers + revenue/capacity planning."""

    # Suggested per-pack price ranges by niche (USD). Used for guidance only.
    NICHE_PRICE_HINTS: Dict[str, int] = {
        "ecommerce": 350,
        "skincare": 350,
        "restaurant": 250,
        "fitness": 300,
        "real estate": 400,
        "dental": 400,
        "law": 500,
        "saas": 600,
        "local": 250,
        "default": 300,
    }

    def __init__(self, brief: Dict[str, Any]):
        """
        Args:
            brief: may contain niche, videos_per_day (your capacity),
                   minutes_per_video, work_days_per_week.
        """
        self.brief = brief or {}
        self.niche = str(self.brief.get("niche", "default")).lower()
        self.videos_per_day = float(self.brief.get("videos_per_day", 8))
        self.minutes_per_video = float(self.brief.get("minutes_per_video", 25))
        self.work_days_per_week = float(self.brief.get("work_days_per_week", 5))

    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
        """Divide safely, avoiding division-by-zero."""
        if denominator == 0:
            return default
        return numerator / denominator

    def base_price(self) -> int:
        """Suggested base per-pack price for this niche."""
        for key, price in self.NICHE_PRICE_HINTS.items():
            if key in self.niche:
                return price
        return self.NICHE_PRICE_HINTS["default"]

    # ------------------------------------------------------------------ #
    # Productized tiers
    # ------------------------------------------------------------------ #
    def tiers(self) -> List[Dict[str, Any]]:
        base = self.base_price()
        return [
            {
                "name": "Starter Pack",
                "price": base,
                "billing": "one-time",
                "deliverables": [
                    "5 short-form video ads (15-30s)",
                    "2 hook variations each",
                    "captions + hashtags",
                    "48-hour turnaround",
                ],
                "best_for": "first-time clients / fast cash",
            },
            {
                "name": "Growth Retainer",
                "price": round(base * 4.2),
                "billing": "per month",
                "deliverables": [
                    "15 video ads / month",
                    "weekly drops (test & iterate)",
                    "trend-based concepts",
                    "priority turnaround",
                ],
                "best_for": "recurring revenue (the $10k engine)",
            },
            {
                "name": "Scale Partner",
                "price": round(base * 8.0),
                "billing": "per month",
                "deliverables": [
                    "30+ video ads / month",
                    "full content calendar + posting",
                    "monthly performance report",
                    "dedicated creative",
                ],
                "best_for": "established brands / agencies",
            },
        ]

    def upsells(self) -> List[Dict[str, Any]]:
        base = self.base_price()
        return [
            {"name": "Rush 24h delivery", "price": round(base * 0.3)},
            {"name": "Extra hook variations (x5)", "price": round(base * 0.25)},
            {"name": "Posting + scheduling", "price": 150, "billing": "per month"},
            {"name": "Monthly performance report", "price": 99, "billing": "per month"},
        ]

    # ------------------------------------------------------------------ #
    # Revenue planning
    # ------------------------------------------------------------------ #
    def weekly_capacity_videos(self) -> float:
        return self.videos_per_day * self.work_days_per_week

    def revenue_plan(
        self, weekly_target: float = 500, monthly_target: float = 10000
    ) -> Dict[str, Any]:
        """Compute concrete paths to the weekly and monthly targets."""
        base = self.base_price()
        tiers = self.tiers()
        starter = tiers[0]["price"]
        retainer = tiers[1]["price"]

        # Weekly target via one-time starter packs.
        packs_per_week = self.safe_divide(weekly_target, starter)
        # Monthly target via retainers (recurring) vs one-time packs.
        retainers_needed = self.safe_divide(monthly_target, retainer)
        packs_per_month = self.safe_divide(monthly_target, starter)

        weekly_cap = self.weekly_capacity_videos()
        videos_needed_weekly = packs_per_week * 5  # 5 videos per starter pack
        capacity_ok = weekly_cap >= videos_needed_weekly

        return {
            "assumptions": {
                "base_pack_price": base,
                "starter_pack_price": starter,
                "growth_retainer_price": retainer,
                "videos_per_starter_pack": 5,
                "your_weekly_video_capacity": weekly_cap,
                "minutes_per_video": self.minutes_per_video,
            },
            "weekly_500_path": {
                "starter_packs_to_close_per_week": round(packs_per_week, 1),
                "videos_to_produce_per_week": round(videos_needed_weekly, 1),
                "capacity_sufficient": capacity_ok,
                "note": (
                    f"Close ~{int(round(packs_per_week))} starter pack(s)/week at "
                    f"${starter} to clear ${int(weekly_target)}/week."
                ),
            },
            "monthly_10k_paths": [
                {
                    "model": "Recurring (recommended)",
                    "what": f"{int(round(retainers_needed))} Growth Retainers @ ${retainer}/mo",
                    "why": "Recurring revenue compounds; less re-selling each month.",
                },
                {
                    "model": "One-time volume",
                    "what": f"{int(round(packs_per_month))} starter packs @ ${starter}",
                    "why": "Faster to start, but you resell from zero every month.",
                },
                {
                    "model": "Hybrid (realistic)",
                    "what": (
                        f"{max(1, int(round(retainers_needed / 2)))} retainers + "
                        f"~{int(round(packs_per_month / 3))} starter packs"
                    ),
                    "why": "Stable base from retainers, topped up with one-off packs.",
                },
            ],
            "capacity_warning": (
                None if capacity_ok else
                "Your stated capacity is below what the weekly target needs - "
                "raise videos_per_day, batch with AI tools, or raise prices."
            ),
        }

    def thirty_day_plan(self) -> List[Dict[str, str]]:
        """A concrete 30-day ramp."""
        return [
            {"phase": "Days 1-2", "focus": "Make 3-5 sample ads + set up a simple portfolio/link."},
            {"phase": "Days 3-7", "focus": "Send 25 sample-first outreaches/day. Close first 2-3 starter packs (~$500-900)."},
            {"phase": "Days 8-14", "focus": "Deliver fast, collect testimonials, pitch Growth Retainer to happy clients."},
            {"phase": "Days 15-21", "focus": "Convert 2-3 clients to retainers. Keep 25 outreaches/day."},
            {"phase": "Days 22-30", "focus": "Stack retainers toward $10k MRR; raise prices as your portfolio grows."},
        ]

    def generate_all(self) -> Dict[str, Any]:
        return {
            "pricing_tiers": self.tiers(),
            "upsells": self.upsells(),
            "revenue_plan": self.revenue_plan(),
            "thirty_day_plan": self.thirty_day_plan(),
            "disclaimer": (
                "Figures are planning aids based on your inputs, not income "
                "guarantees. Actual results depend on outreach volume, niche, "
                "offer quality, and delivery."
            ),
        }


if __name__ == "__main__":
    op = OfferPricing({"niche": "skincare", "videos_per_day": 8})
    plan = op.revenue_plan()
    print("Base price:", op.base_price())
    print("Weekly $500 path:", plan["weekly_500_path"]["note"])
    for path in plan["monthly_10k_paths"]:
        print(f"  {path['model']}: {path['what']}")
