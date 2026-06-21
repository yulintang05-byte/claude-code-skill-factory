"""
AI UGC Ad Script Generator
Generates scroll-stopping short-form video ad scripts (hook -> body -> CTA)
using proven direct-response frameworks. Built for AI-video creators selling
ad creative to e-commerce brands and local businesses.

No external dependencies (standard library only) so it runs anywhere.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


class AdScriptGenerator:
    """Generates UGC-style short-form video ad scripts from a simple brief."""

    # Proven hook templates grouped by psychological angle. Tokens are filled
    # from the brief: {audience}, {pain}, {product}, {result}, {timeframe},
    # {category}, {niche}.
    HOOK_LIBRARY: Dict[str, List[str]] = {
        "problem_callout": [
            "If you're a {audience} still struggling with {pain}, stop scrolling.",
            "{audience}: this is why you keep dealing with {pain}.",
            "The real reason you can't fix {pain}? Nobody told you this.",
        ],
        "bold_claim": [
            "This {product} replaced 3 things I used to pay for.",
            "I stopped {pain} in {timeframe} with one {category}.",
            "This is the {product} everyone in {niche} is quietly using.",
        ],
        "curiosity": [
            "I wasn't going to share this {product}... but here we go.",
            "Nobody in {niche} talks about this, so I will.",
            "I tested every {category} so you don't have to. One won.",
        ],
        "pattern_interrupt": [
            "Stop buying {category} until you watch this.",
            "Delete your last {category} order. Do this instead.",
            "Throw out your {category}. Seriously.",
        ],
        "social_proof": [
            "I didn't believe the reviews on this {product}... until day 3.",
            "10,000 {audience} can't be wrong about this {product}.",
            "My {audience} friends keep asking where I got this {product}.",
        ],
        "pov_relatable": [
            "POV: you finally found a {product} that actually {result}.",
            "POV: it's {timeframe} and you already {result}.",
            "That feeling when a {product} just... {result}.",
        ],
        "question": [
            "What if you could {result} in {timeframe}?",
            "Why is no one talking about how to {result}?",
            "Want to {result} without the usual {pain}?",
        ],
    }

    # Framework -> ordered beats. Each beat is (label, intent).
    FRAMEWORKS: Dict[str, List[Dict[str, str]]] = {
        "AIDA": [
            {"label": "Attention", "intent": "hook"},
            {"label": "Interest", "intent": "relate_problem"},
            {"label": "Desire", "intent": "product_benefit_proof"},
            {"label": "Action", "intent": "cta"},
        ],
        "PAS": [
            {"label": "Problem", "intent": "problem"},
            {"label": "Agitate", "intent": "agitate"},
            {"label": "Solution", "intent": "product_benefit_proof"},
            {"label": "Action", "intent": "cta"},
        ],
        "HRR": [  # Hook - Retain - Reward
            {"label": "Hook", "intent": "hook"},
            {"label": "Retain", "intent": "demo"},
            {"label": "Reward", "intent": "result_payoff"},
            {"label": "Action", "intent": "cta"},
        ],
        "BAB": [  # Before - After - Bridge
            {"label": "Before", "intent": "problem"},
            {"label": "After", "intent": "result_payoff"},
            {"label": "Bridge", "intent": "product_benefit_proof"},
            {"label": "Action", "intent": "cta"},
        ],
    }

    CTA_LIBRARY: List[str] = [
        "Tap the link to get yours before it sells out.",
        "Comment \"{keyword}\" and I'll DM you the link.",
        "Link in bio - {offer}.",
        "Use code {code} for {discount}% off today only.",
        "Click the link and see why everyone's switching.",
    ]

    def __init__(self, brief: Dict[str, Any]):
        """
        Initialize with a campaign brief.

        Args:
            brief: Dict that may contain: business, product, niche, audience,
                   pain, result, benefits (list), timeframe, category, tone,
                   offer, discount, code, keyword, duration_seconds, platform.
        """
        self.brief = brief or {}
        self.business = self.brief.get("business", "the brand")
        self.product = self.brief.get("product", "this product")
        self.niche = self.brief.get("niche", "this space")
        self.audience = self.brief.get("audience", "people like you")
        self.pain = self.brief.get("pain", "the usual headaches")
        self.result = self.brief.get("result", "get real results")
        self.benefits = self.brief.get("benefits") or self._default_benefits()
        self.timeframe = self.brief.get("timeframe", "a few days")
        self.category = self.brief.get("category", "product")
        self.tone = self.brief.get("tone", "energetic, authentic, conversational")
        self.offer = self.brief.get("offer", "limited launch pricing")
        self.discount = self.brief.get("discount", 15)
        self.code = self.brief.get("code", "SAVE15")
        self.keyword = self.brief.get("keyword", "LINK")
        self.duration = int(self.brief.get("duration_seconds", 30))
        self.platform = self.brief.get("platform", "TikTok")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _default_benefits(self) -> List[str]:
        return [
            "saves time",
            "looks premium",
            "actually works the first try",
        ]

    def _fill(self, text: str) -> str:
        """Token-fill a template safely (missing tokens left readable)."""
        tokens = {
            "audience": self.audience,
            "pain": self.pain,
            "product": self.product,
            "result": self.result,
            "timeframe": self.timeframe,
            "category": self.category,
            "niche": self.niche,
            "offer": self.offer,
            "discount": self.discount,
            "code": self.code,
            "keyword": self.keyword,
            "business": self.business,
        }
        out = text
        for key, value in tokens.items():
            out = out.replace("{" + key + "}", str(value))
        return out

    def generate_hooks(self, count: int = 5) -> List[Dict[str, str]]:
        """Return a spread of hooks across different angles (most important asset)."""
        hooks: List[Dict[str, str]] = []
        # Round-robin across angles so variety is guaranteed.
        angles = list(self.HOOK_LIBRARY.keys())
        idx = 0
        while len(hooks) < count and idx < count * len(angles):
            angle = angles[idx % len(angles)]
            variant = (idx // len(angles)) % len(self.HOOK_LIBRARY[angle])
            text = self._fill(self.HOOK_LIBRARY[angle][variant])
            if all(h["text"] != text for h in hooks):
                hooks.append({"angle": angle, "text": text})
            idx += 1
        return hooks

    # ------------------------------------------------------------------ #
    # Beat rendering
    # ------------------------------------------------------------------ #
    def _render_beat(self, intent: str, hook_text: str) -> str:
        benefit_line = ", ".join(self.benefits[:3])
        renderers = {
            "hook": hook_text,
            "relate_problem": self._fill(
                "Look, every {audience} knows the pain of {pain}. I was there too."
            ),
            "problem": self._fill(
                "Here's the problem: {pain} - and most {category} options make it worse."
            ),
            "agitate": self._fill(
                "Keep ignoring it and you waste money, time, and patience every single week."
            ),
            "product_benefit_proof": self._fill(
                f"Then I found {self.product}. It {benefit_line}. "
                "No fluff - it just works."
            ),
            "demo": self._fill(
                f"Watch - I use {self.product} once and you can already see the difference."
            ),
            "result_payoff": self._fill(
                "And just like that - {result}. This is the part nobody believes."
            ),
            "cta": self._fill(self.CTA_LIBRARY[0]),
        }
        return renderers.get(intent, "")

    def generate_script(self, framework: str = "AIDA", hook: Optional[str] = None) -> Dict[str, Any]:
        """
        Build one complete script for the chosen framework.

        Returns a structured script with scene beats, voiceover, on-screen text,
        b-roll suggestion, estimated duration, and caption/hashtags.
        """
        framework = framework if framework in self.FRAMEWORKS else "AIDA"
        beats_spec = self.FRAMEWORKS[framework]
        hook_text = hook or self.generate_hooks(1)[0]["text"]

        per_beat = max(2, round(self.duration / max(1, len(beats_spec))))
        scenes: List[Dict[str, Any]] = []
        for i, beat in enumerate(beats_spec):
            line = self._render_beat(beat["intent"], hook_text)
            scenes.append({
                "beat": beat["label"],
                "seconds": per_beat,
                "voiceover": line,
                "on_screen_text": self._on_screen_text(beat["intent"], line),
                "b_roll": self._b_roll(beat["intent"]),
            })

        return {
            "framework": framework,
            "platform": self.platform,
            "target_duration_seconds": self.duration,
            "hook": hook_text,
            "scenes": scenes,
            "full_voiceover": " ".join(s["voiceover"] for s in scenes),
            "caption": self._caption(),
            "hashtags": self._hashtags(),
            "cta_options": [self._fill(c) for c in self.CTA_LIBRARY],
        }

    def _on_screen_text(self, intent: str, line: str) -> str:
        """Punchy caption overlay (shorter than the voiceover)."""
        mapping = {
            "hook": line,
            "cta": self._fill("{offer} 👇"),
            "result_payoff": self._fill("{result} ✅"),
            "product_benefit_proof": "this changed everything",
        }
        return mapping.get(intent, " ".join(line.split()[:6]) + "...")

    def _b_roll(self, intent: str) -> str:
        mapping = {
            "hook": "Close-up talking-to-camera, fast pattern-interrupt cut",
            "relate_problem": "Relatable B-roll of the frustration / messy 'before'",
            "problem": "The problem shown literally (the 'before' state)",
            "agitate": "Quick montage of failed alternatives",
            "product_benefit_proof": f"Hero product shot of {self.product}, satisfying reveal",
            "demo": f"Hands-on demo using {self.product}",
            "result_payoff": "The 'after' - happy result, smile, transformation",
            "cta": "Product + offer on screen, tap-the-link gesture",
        }
        return mapping.get(intent, "Supporting B-roll")

    def _caption(self) -> str:
        return self._fill(
            f"{self.product} for {self.audience} who are done with {self.pain}. "
            f"{self.offer} 🔥"
        )

    def _hashtags(self) -> List[str]:
        base = ["#tiktokmademebuyit", "#ugc", "#fyp", "#smallbusiness"]
        niche_tag = "#" + "".join(ch for ch in self.niche.lower() if ch.isalnum())
        return base + ([niche_tag] if len(niche_tag) > 1 else [])

    def generate_variants(self, count: int = 3) -> List[Dict[str, Any]]:
        """Generate N scripts across different frameworks + hooks for A/B testing."""
        frameworks = list(self.FRAMEWORKS.keys())
        hooks = self.generate_hooks(max(count, 3))
        variants = []
        for i in range(count):
            fw = frameworks[i % len(frameworks)]
            hk = hooks[i % len(hooks)]["text"]
            script = self.generate_script(framework=fw, hook=hk)
            script["variant_id"] = f"V{i + 1}"
            script["angle"] = hooks[i % len(hooks)]["angle"]
            variants.append(script)
        return variants


if __name__ == "__main__":
    demo_brief = {
        "business": "GlowDrip Skincare",
        "product": "GlowDrip Vitamin-C serum",
        "niche": "skincare",
        "audience": "busy women in their 30s",
        "pain": "dull, tired-looking skin",
        "result": "visibly brighter skin",
        "benefits": ["brightens in 7 days", "absorbs in seconds", "no sticky residue"],
        "timeframe": "7 days",
        "category": "serum",
        "offer": "20% off first order",
        "discount": 20,
        "code": "GLOW20",
        "duration_seconds": 30,
        "platform": "TikTok",
    }
    gen = AdScriptGenerator(demo_brief)
    print("HOOKS:")
    for h in gen.generate_hooks(5):
        print(f"  [{h['angle']}] {h['text']}")
    print("\nSCRIPT (AIDA):")
    script = gen.generate_script("AIDA")
    for scene in script["scenes"]:
        print(f"  {scene['beat']} ({scene['seconds']}s): {scene['voiceover']}")
