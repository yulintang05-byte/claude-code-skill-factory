"""
Toolchain Cost Estimator
Estimates what it actually costs to RUN an AI video ad agency across the three
real generation paths, so you can see per-ad cost, monthly cost, and profit
margin against your pack price.

The three paths reflect how tools like "Open Generative AI / Open-Higgsfield"
(Anil Matcha's repo) actually work:
  - cloud_api   : free open-source UI, but generation is PAID per-use via a
                  gateway like Muapi.ai / fal.ai (this is what "no subscription"
                  really means - usage-based, not free)
  - rented_gpu  : truly self-hosted open models (Wan 2.2 / Hunyuan / LTX via
                  ComfyUI or Wan2GP) on a rented cloud GPU (RunPod/vast.ai)
  - owned_gpu   : same, on your own GPU - near-zero marginal cost after capex

All prices are editable assumptions reflecting mid-2026 public rates, NOT
guarantees. Standard library only.
"""

from typing import Dict, List, Any
import math
import argparse
import json
import sys


class ToolchainCostEstimator:
    """Compares per-ad and monthly cost across cloud vs rented vs owned GPU."""

    # ---- Editable price assumptions (mid-2026 public ballparks) ---- #
    DEFAULTS: Dict[str, float] = {
        # Cloud per-use (Muapi.ai / fal.ai gateways)
        "cloud_per_sec_budget": 0.10,    # Wan 2.2 720p i2v (~$1.00 / 10s)
        "cloud_per_sec_premium": 0.40,   # Veo / Kling / Sora-class via API
        "cloud_image": 0.03,             # one Flux/SDXL still
        # Rented GPU (RunPod)
        "runpod_4090_community_hr": 0.34,
        "runpod_4090_secure_hr": 0.59,
        "h100_hr": 2.69,
        # Owned GPU
        "owned_gpu_capex": 1800.0,       # RTX 4090-class card
        "electricity_per_gpu_hr": 0.08,  # ~450W at ~$0.17/kWh
        # Throughput (consumer 4090, quality model like Wan 2.2 14B)
        "minutes_per_5s_clip_4090": 7.0,
        # Optional fixed monthly costs
        "editing_tool_monthly": 0.0,     # CapCut/DaVinci free by default
        "music_tool_monthly": 0.0,       # free libraries by default
        "domain_monthly": 1.0,           # ~$12/yr portfolio domain
    }

    def __init__(self, brief: Dict[str, Any] = None):
        b = brief or {}
        self.prices = {**self.DEFAULTS, **(b.get("prices") or {})}
        self.ads_per_month = float(b.get("ads_per_month", 120))
        self.seconds_per_ad = float(b.get("seconds_per_ad", 30))
        self.clip_seconds = float(b.get("clip_seconds", 5))
        self.retry_overhead = float(b.get("retry_overhead", 2.5))  # rejects/variants
        self.images_per_ad = float(b.get("images_per_ad", 6))
        self.pack_price = float(b.get("pack_price", 300))
        self.ads_per_pack = float(b.get("ads_per_pack", 5))
        self.gpu_rate_kind = b.get("gpu_rate", "community")  # community|secure

    @staticmethod
    def safe_divide(num: float, den: float, default: float = 0.0) -> float:
        return default if den == 0 else num / den

    # ------------------------------------------------------------------ #
    # Derived production volume
    # ------------------------------------------------------------------ #
    def _gen_seconds_per_ad(self) -> float:
        """Total seconds generated per finished ad, incl. rejects/variations."""
        return self.seconds_per_ad * self.retry_overhead

    def _clips_per_ad(self) -> int:
        return max(1, math.ceil(self._gen_seconds_per_ad() / self.clip_seconds))

    def _gpu_hours_per_ad(self) -> float:
        return self._clips_per_ad() * self.prices["minutes_per_5s_clip_4090"] / 60.0

    def _gpu_hourly(self) -> float:
        if self.gpu_rate_kind == "secure":
            return self.prices["runpod_4090_secure_hr"]
        return self.prices["runpod_4090_community_hr"]

    # ------------------------------------------------------------------ #
    # Per-ad cost by path
    # ------------------------------------------------------------------ #
    def per_ad_cloud(self, premium: bool = False) -> float:
        rate = self.prices["cloud_per_sec_premium"] if premium else self.prices["cloud_per_sec_budget"]
        video = self._gen_seconds_per_ad() * rate
        images = self.images_per_ad * self.prices["cloud_image"]
        return round(video + images, 2)

    def per_ad_rented_gpu(self) -> float:
        # Start frames generated on the same GPU -> no separate image cost.
        return round(self._gpu_hours_per_ad() * self._gpu_hourly(), 2)

    def per_ad_owned_gpu(self) -> float:
        return round(self._gpu_hours_per_ad() * self.prices["electricity_per_gpu_hr"], 2)

    # ------------------------------------------------------------------ #
    # Monthly + margin
    # ------------------------------------------------------------------ #
    def _fixed_monthly(self) -> float:
        return (
            self.prices["editing_tool_monthly"]
            + self.prices["music_tool_monthly"]
            + self.prices["domain_monthly"]
        )

    def _revenue_per_ad(self) -> float:
        return self.safe_divide(self.pack_price, self.ads_per_pack)

    def _summarize(self, per_ad: float, capex: float = 0.0) -> Dict[str, Any]:
        monthly = round(per_ad * self.ads_per_month + self._fixed_monthly(), 2)
        rev_per_ad = self._revenue_per_ad()
        margin = self.safe_divide(rev_per_ad - per_ad, rev_per_ad) * 100
        return {
            "cost_per_ad": round(per_ad, 2),
            "monthly_cost": monthly,
            "one_time_capex": round(capex, 2),
            "revenue_per_ad": round(rev_per_ad, 2),
            "profit_margin_pct": round(margin, 1),
        }

    def compare(self) -> Dict[str, Any]:
        cloud_budget = self._summarize(self.per_ad_cloud(premium=False))
        cloud_premium = self._summarize(self.per_ad_cloud(premium=True))
        rented = self._summarize(self.per_ad_rented_gpu())
        owned = self._summarize(self.per_ad_owned_gpu(), capex=self.prices["owned_gpu_capex"])

        # Payback for buying a GPU vs the cloud-budget path.
        monthly_saving = cloud_budget["monthly_cost"] - owned["monthly_cost"]
        payback_months = self.safe_divide(self.prices["owned_gpu_capex"], monthly_saving)

        return {
            "inputs": {
                "ads_per_month": self.ads_per_month,
                "seconds_per_finished_ad": self.seconds_per_ad,
                "retry_overhead_x": self.retry_overhead,
                "generated_seconds_per_ad": round(self._gen_seconds_per_ad(), 1),
                "clips_per_ad": self._clips_per_ad(),
                "gpu_hours_per_ad": round(self._gpu_hours_per_ad(), 2),
                "gpu_rate_kind": self.gpu_rate_kind,
                "pack_price": self.pack_price,
                "ads_per_pack": self.ads_per_pack,
            },
            "paths": {
                "cloud_api_budget_models": cloud_budget,
                "cloud_api_premium_models": cloud_premium,
                "rented_gpu_selfhost": rented,
                "owned_gpu_selfhost": owned,
            },
            "owned_gpu_payback_months": (
                round(payback_months, 1) if monthly_saving > 0 else None
            ),
            "recommendation": self._recommend(),
            "disclaimer": (
                "Prices are editable mid-2026 public ballparks, not guarantees. "
                "Per-ad compute is tiny vs your pack price - your real cost is "
                "TIME (outreach + editing), so start cheap and scale the toolchain "
                "only when volume justifies it. Verify each model's commercial-use "
                "license before selling client work."
            ),
        }

    def _recommend(self) -> str:
        n = self.ads_per_month
        if n <= 40:
            return (
                "STARTING OUT (<=40 ads/mo): use the cloud/pay-as-you-go path "
                "(e.g. Muapi/fal credits, budget models like Wan 2.2 / Seedance / "
                "LTX). ~$10-30 to make all your samples and first deliveries. "
                "Zero setup, no GPU to manage."
            )
        if n <= 100:
            return (
                "GROWING (40-100 ads/mo): move heavy generation to a RENTED GPU "
                "(RunPod 4090 ~$0.34/hr) running ComfyUI/Wan2GP. Cuts per-ad cost "
                "~10x vs cloud while staying flexible."
            )
        return (
            "AT VOLUME (100+ ads/mo): buy your own GPU (RTX 4090/5090). It "
            "typically pays for itself in ~2 months vs cloud, then marginal cost "
            "is just electricity."
        )

    def to_markdown(self) -> str:
        data = self.compare()
        i = data["inputs"]
        lines = ["# 💸 AI Ad Agency - Toolchain Cost Estimate", ""]
        lines.append(
            f"Assuming **{int(i['ads_per_month'])} ads/month**, {int(i['seconds_per_finished_ad'])}s each, "
            f"{i['retry_overhead_x']}x retry overhead → ~{i['generated_seconds_per_ad']}s "
            f"({i['clips_per_ad']} clips) generated per finished ad."
        )
        lines.append("")
        lines.append("| Path | Cost / ad | Monthly | One-time | Margin* |")
        lines.append("|------|-----------|---------|----------|---------|")
        label = {
            "cloud_api_budget_models": "Cloud API – budget models (Wan/Seedance/LTX)",
            "cloud_api_premium_models": "Cloud API – premium models (Veo/Kling/Sora)",
            "rented_gpu_selfhost": "Rented GPU self-host (RunPod 4090)",
            "owned_gpu_selfhost": "Owned GPU self-host (your RTX 4090)",
        }
        for key, p in data["paths"].items():
            capex = f"${p['one_time_capex']:,.0f}" if p["one_time_capex"] else "—"
            lines.append(
                f"| {label[key]} | ${p['cost_per_ad']:.2f} | ${p['monthly_cost']:,.0f} "
                f"| {capex} | {p['profit_margin_pct']:.0f}% |"
            )
        lines.append("")
        lines.append(f"*Margin vs your price of ${data['inputs']['pack_price']:.0f} "
                     f"for {int(data['inputs']['ads_per_pack'])} ads "
                     f"(${data['paths']['cloud_api_budget_models']['revenue_per_ad']:.0f}/ad revenue).")
        if data["owned_gpu_payback_months"]:
            lines.append("")
            lines.append(f"**Buy-a-GPU payback:** ~{data['owned_gpu_payback_months']} months "
                         f"vs the cloud-budget path.")
        lines.append("")
        lines.append(f"**Recommendation:** {data['recommendation']}")
        lines.append("")
        lines.append(f"> _{data['disclaimer']}_")
        return "\n".join(lines)


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(description="AI ad agency toolchain cost estimator")
    parser.add_argument("--ads-per-month", type=float, default=120)
    parser.add_argument("--seconds-per-ad", type=float, default=30)
    parser.add_argument("--retry-overhead", type=float, default=2.5)
    parser.add_argument("--pack-price", type=float, default=300)
    parser.add_argument("--ads-per-pack", type=float, default=5)
    parser.add_argument("--gpu-rate", choices=["community", "secure"], default="community")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    args = parser.parse_args(argv)

    est = ToolchainCostEstimator({
        "ads_per_month": args.ads_per_month,
        "seconds_per_ad": args.seconds_per_ad,
        "retry_overhead": args.retry_overhead,
        "pack_price": args.pack_price,
        "ads_per_pack": args.ads_per_pack,
        "gpu_rate": args.gpu_rate,
    })
    if args.format == "json":
        print(json.dumps(est.compare(), indent=2))
    else:
        print(est.to_markdown())
    return 0


if __name__ == "__main__":
    sys.exit(main())
