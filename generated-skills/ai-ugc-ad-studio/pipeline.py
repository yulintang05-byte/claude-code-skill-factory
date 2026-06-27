"""
AI UGC Ad Studio - Pipeline Orchestrator
One brief in -> a complete, ready-to-use campaign kit out:
  1. Ad scripts (multiple A/B variants)
  2. Platform-ready AI video prompts (Higgsfield + alternatives)
  3. Client outreach kit (DM, email, SMS, follow-ups, objections)
  4. Pricing tiers + revenue plan ($500/week and $10k/month math)
  5. A 30-day action plan

Usage:
    python pipeline.py --demo
    python pipeline.py --input sample_input.json --format md
    python pipeline.py --input sample_input.json --format json --out kit.json

Standard library only.
"""

from typing import Dict, List, Any, Optional
import argparse
import json
import sys

try:  # Allow running both as a module and as a script from the folder.
    from ad_script_generator import AdScriptGenerator
    from video_prompt_builder import VideoPromptBuilder
    from outreach_generator import OutreachGenerator
    from offer_pricing import OfferPricing
except ImportError:  # pragma: no cover - fallback for package-style import
    from .ad_script_generator import AdScriptGenerator
    from .video_prompt_builder import VideoPromptBuilder
    from .outreach_generator import OutreachGenerator
    from .offer_pricing import OfferPricing


class AdStudioPipeline:
    """Runs every generator and assembles a single campaign kit."""

    def __init__(self, brief: Dict[str, Any]):
        self.brief = brief or {}

    def run(
        self,
        num_scripts: int = 3,
        video_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        video_tools = video_tools or self.brief.get(
            "video_tools", ["higgsfield", "sora", "kling"]
        )

        # 1. Scripts
        script_gen = AdScriptGenerator(self.brief)
        hooks = script_gen.generate_hooks(7)
        variants = script_gen.generate_variants(num_scripts)

        # 2. Video prompts for the strongest (first) variant
        prompt_builder = VideoPromptBuilder(self.brief)
        video_prompts = prompt_builder.build_from_script(variants[0], tools=video_tools)

        # 3. Outreach
        outreach = OutreachGenerator(self.brief).generate_all()

        # 4. Pricing + revenue plan
        pricing = OfferPricing(self.brief).generate_all()

        return {
            "meta": {
                "business": self.brief.get("business", "the brand"),
                "product": self.brief.get("product", "the product"),
                "niche": self.brief.get("niche", "general"),
                "platform": self.brief.get("platform", "TikTok"),
                "video_tools": video_tools,
            },
            "hooks": hooks,
            "ad_scripts": variants,
            "video_prompts": video_prompts,
            "outreach": outreach,
            "pricing_and_revenue": pricing,
        }

    # ------------------------------------------------------------------ #
    # Rendering
    # ------------------------------------------------------------------ #
    @staticmethod
    def to_markdown(kit: Dict[str, Any]) -> str:
        m = kit["meta"]
        lines: List[str] = []
        lines.append(f"# 🎬 AI UGC Ad Kit - {m['business']}")
        lines.append("")
        lines.append(
            f"**Product:** {m['product']}  |  **Niche:** {m['niche']}  |  "
            f"**Platform:** {m['platform']}  |  **Tools:** {', '.join(m['video_tools'])}"
        )
        lines.append("")

        # Hooks
        lines.append("## 1. Scroll-Stopping Hooks (test these first)")
        for i, h in enumerate(kit["hooks"], 1):
            lines.append(f"{i}. _({h['angle']})_ {h['text']}")
        lines.append("")

        # Scripts
        lines.append("## 2. Ad Scripts (A/B variants)")
        for v in kit["ad_scripts"]:
            lines.append(
                f"### {v['variant_id']} - {v['framework']} framework "
                f"({v['target_duration_seconds']}s, angle: {v.get('angle','-')})"
            )
            lines.append(f"**Hook:** {v['hook']}")
            for s in v["scenes"]:
                lines.append(
                    f"- **{s['beat']} ({s['seconds']}s)** - {s['voiceover']}  "
                    f"\n  - On-screen: _{s['on_screen_text']}_  \n  - B-roll: {s['b_roll']}"
                )
            lines.append(f"**Caption:** {v['caption']}")
            lines.append(f"**Hashtags:** {' '.join(v['hashtags'])}")
            lines.append("")

        # Video prompts
        lines.append("## 3. AI Video Prompts (copy-paste ready)")
        for scene in kit["video_prompts"]:
            lines.append(f"### Scene: {scene['beat']}")
            for tool, prompt in scene["prompts"].items():
                lines.append(f"**{tool.title()}**")
                lines.append("```")
                lines.append(prompt)
                lines.append("```")
            lines.append("")

        # Outreach
        o = kit["outreach"]
        lines.append("## 4. Client Outreach Kit (sample-first = higher reply rate)")
        lines.append(f"**Instagram DM:**\n\n> {o['instagram_dm']}")
        lines.append("")
        lines.append(
            f"**Cold Email**\n\n*Subject:* {o['cold_email']['subject']}\n\n"
            f"```\n{o['cold_email']['body']}\n```"
        )
        lines.append(f"**SMS:** {o['sms']}")
        lines.append("")
        lines.append(f"**Walk-in pitch:**\n\n{o['walk_in_pitch']}")
        lines.append("")
        lines.append("**Follow-up sequence:**")
        for f in o["follow_up_sequence"]:
            lines.append(f"- *{f['when']}*: {f['message']}")
        lines.append("")
        lines.append("**Objection handling:**")
        for obj, ans in o["objection_handlers"].items():
            lines.append(f"- *\"{obj}\"* -> {ans}")
        lines.append("")

        # Pricing + revenue
        p = kit["pricing_and_revenue"]
        lines.append("## 5. Pricing & Path to Revenue")
        lines.append("**Packages:**")
        for t in p["pricing_tiers"]:
            lines.append(
                f"- **{t['name']}** - ${t['price']} ({t['billing']}): "
                f"{'; '.join(t['deliverables'])} _- {t['best_for']}_"
            )
        rp = p["revenue_plan"]
        lines.append("")
        lines.append(f"**$500/week:** {rp['weekly_500_path']['note']}")
        lines.append("**$10k/month options:**")
        for path in rp["monthly_10k_paths"]:
            lines.append(f"- **{path['model']}** - {path['what']} ({path['why']})")
        if rp.get("capacity_warning"):
            lines.append(f"\n> ⚠️ {rp['capacity_warning']}")
        lines.append("")
        lines.append("**30-Day Plan:**")
        for step in p["thirty_day_plan"]:
            lines.append(f"- **{step['phase']}**: {step['focus']}")
        lines.append("")
        lines.append(f"> _{p['disclaimer']}_")
        return "\n".join(lines)


DEMO_BRIEF: Dict[str, Any] = {
    "business": "GlowDrip Skincare",
    "contact_name": "Maya",
    "product": "GlowDrip Vitamin-C serum",
    "niche": "skincare",
    "city": "Austin",
    "audience": "busy women in their 30s",
    "pain": "dull, tired-looking skin",
    "result": "visibly brighter skin in a week",
    "benefits": ["brightens in 7 days", "absorbs in seconds", "no sticky residue"],
    "timeframe": "7 days",
    "category": "serum",
    "tone": "energetic, authentic",
    "offer": "5 short-form video ads",
    "price": 350,
    "discount": 20,
    "code": "GLOW20",
    "keyword": "GLOW",
    "your_name": "Sam",
    "platform": "TikTok",
    "visual_style": "ugc",
    "videos_per_day": 8,
    "video_tools": ["higgsfield", "sora", "kling"],
}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="AI UGC Ad Studio pipeline")
    parser.add_argument("--input", help="Path to a brief JSON file")
    parser.add_argument("--demo", action="store_true", help="Run with the built-in demo brief")
    parser.add_argument("--format", choices=["md", "json"], default="md")
    parser.add_argument("--scripts", type=int, default=3, help="Number of ad-script variants")
    parser.add_argument("--out", help="Write output to this file instead of stdout")
    args = parser.parse_args(argv)

    if args.demo:
        brief = DEMO_BRIEF
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as fh:
            brief = json.load(fh)
    else:
        parser.error("Provide --input <file.json> or --demo")
        return 2

    kit = AdStudioPipeline(brief).run(num_scripts=args.scripts)
    output = (
        json.dumps(kit, indent=2, ensure_ascii=False)
        if args.format == "json"
        else AdStudioPipeline.to_markdown(kit)
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"Wrote campaign kit to {args.out}")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
