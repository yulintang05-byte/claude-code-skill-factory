"""
AI Video Prompt Builder ("the promo generator")
Converts an ad concept / script into copy-paste-ready text-to-video and
image-to-video prompts, formatted for the major AI video tools:
Higgsfield, Sora, Google Veo, Kling, and Runway.

Each scene becomes a structured "shot spec" that is then rendered in the
exact phrasing each tool responds to best.

Standard library only.
"""

from typing import Dict, List, Any, Optional


class VideoPromptBuilder:
    """Builds platform-specific AI video prompts from scene specs."""

    # Aspect ratio defaults per platform.
    PLATFORM_ASPECT: Dict[str, str] = {
        "TikTok": "9:16",
        "Reels": "9:16",
        "Instagram": "9:16",
        "Shorts": "9:16",
        "YouTube": "16:9",
        "Facebook": "1:1",
    }

    # Higgsfield is known for its cinematic camera-motion presets. These map an
    # intent to a recommended Higgsfield motion preset.
    HIGGSFIELD_MOTION: Dict[str, str] = {
        "hook": "Crash Zoom In",
        "reveal": "Super Dolly In",
        "product": "360 Orbit",
        "demo": "Robo Arm",
        "result": "Dolly Out",
        "energy": "FPV Drone",
        "drama": "Bullet Time",
        "default": "Super Dolly In",
    }

    STYLE_PRESETS: Dict[str, str] = {
        "ugc": "authentic iPhone-shot UGC look, natural handheld, realistic lighting",
        "cinematic": "cinematic, shallow depth of field, film grain, color graded",
        "premium": "premium commercial product film, glossy, studio lighting",
        "vibrant": "vibrant, punchy colors, high energy, bright",
    }

    def __init__(self, brief: Dict[str, Any]):
        """
        Args:
            brief: shares fields with the script brief (product, business,
                   audience, platform, visual_style, color_grade, etc.)
        """
        self.brief = brief or {}
        self.product = self.brief.get("product", "the product")
        self.business = self.brief.get("business", "the brand")
        self.audience = self.brief.get("audience", "the customer")
        self.platform = self.brief.get("platform", "TikTok")
        self.aspect = self.brief.get(
            "aspect_ratio", self.PLATFORM_ASPECT.get(self.platform, "9:16")
        )
        self.style_key = self.brief.get("visual_style", "ugc")
        self.style = self.STYLE_PRESETS.get(self.style_key, self.STYLE_PRESETS["ugc"])
        self.color_grade = self.brief.get("color_grade", "warm, natural skin tones")
        self.setting = self.brief.get("setting", "a bright, modern home setting")
        self.actor = self.brief.get(
            "actor", f"a relatable {self.audience} as the on-camera creator"
        )

    # ------------------------------------------------------------------ #
    # Shot spec construction
    # ------------------------------------------------------------------ #
    def _intent_to_motion_key(self, beat_label: str, intent_hint: str) -> str:
        label = (beat_label or "").lower()
        hint = (intent_hint or "").lower()
        if "hook" in label or "attention" in label:
            return "hook"
        if "product" in hint or "bridge" in label or "desire" in label:
            return "product"
        if "demo" in hint or "retain" in label or "interest" in label:
            return "demo"
        if "result" in hint or "after" in label or "reward" in label:
            return "result"
        if "action" in label or "cta" in hint:
            return "reveal"
        return "default"

    def build_shot_spec(
        self,
        scene_description: str,
        beat_label: str = "Scene",
        duration_s: int = 5,
        intent_hint: str = "",
    ) -> Dict[str, Any]:
        """Create a tool-agnostic shot specification for one scene."""
        motion_key = self._intent_to_motion_key(beat_label, intent_hint)
        return {
            "beat": beat_label,
            "subject": self.actor,
            "action": scene_description,
            "setting": self.setting,
            "product": self.product,
            "shot_type": "medium close-up" if motion_key == "hook" else "dynamic product shot",
            "camera_move": self.HIGGSFIELD_MOTION.get(motion_key, "Super Dolly In"),
            "motion_key": motion_key,
            "lighting": "soft natural window light" if self.style_key == "ugc" else "studio key + rim light",
            "style": self.style,
            "color_grade": self.color_grade,
            "aspect_ratio": self.aspect,
            "duration_s": duration_s,
            "negative": "blurry, distorted hands, watermark, text artifacts, low quality, deformed product",
        }

    # ------------------------------------------------------------------ #
    # Per-tool renderers
    # ------------------------------------------------------------------ #
    def render_higgsfield(self, spec: Dict[str, Any]) -> str:
        return (
            f"[HIGGSFIELD - image-to-video / text-to-video]\n"
            f"Scene: {spec['subject']} in {spec['setting']}. {spec['action']} "
            f"Featuring {spec['product']}.\n"
            f"Camera motion preset: {spec['camera_move']} (high motion strength).\n"
            f"Shot: {spec['shot_type']}. Lighting: {spec['lighting']}. "
            f"Style: {spec['style']}, {spec['color_grade']}.\n"
            f"Aspect ratio: {spec['aspect_ratio']}. Duration: {spec['duration_s']}s.\n"
            f"Tip: upload a hero product/creator image first, then apply the "
            f"'{spec['camera_move']}' preset for the cinematic move.\n"
            f"Negative: {spec['negative']}"
        )

    def render_sora(self, spec: Dict[str, Any]) -> str:
        return (
            f"[SORA]\n"
            f"A {spec['duration_s']}-second {spec['aspect_ratio']} vertical clip. "
            f"{spec['subject']} in {spec['setting']}. {spec['action']} "
            f"The {spec['product']} is clearly featured. "
            f"Camera performs a {spec['camera_move'].lower()} move. "
            f"{spec['lighting']}, {spec['style']}, {spec['color_grade']}. "
            f"Realistic motion, natural performance, no on-screen text."
        )

    def render_veo(self, spec: Dict[str, Any]) -> str:
        return (
            f"[GOOGLE VEO]\n"
            f"Subject: {spec['subject']}.\n"
            f"Action: {spec['action']}\n"
            f"Scene: {spec['setting']}, {spec['product']} featured.\n"
            f"Camera: {spec['camera_move']}, {spec['shot_type']}.\n"
            f"Lighting & style: {spec['lighting']}, {spec['style']}, {spec['color_grade']}.\n"
            f"Audio: natural ambient sound + upbeat background music.\n"
            f"Aspect: {spec['aspect_ratio']}. Duration: {spec['duration_s']}s."
        )

    def render_kling(self, spec: Dict[str, Any]) -> str:
        return (
            f"[KLING]\n"
            f"{spec['subject']}, {spec['action']} {spec['product']} in {spec['setting']}. "
            f"Camera: {spec['camera_move']}. {spec['style']}, {spec['lighting']}, "
            f"{spec['color_grade']}. Smooth realistic motion. "
            f"Aspect {spec['aspect_ratio']}, {spec['duration_s']}s. "
            f"Negative prompt: {spec['negative']}"
        )

    def render_runway(self, spec: Dict[str, Any]) -> str:
        return (
            f"[RUNWAY GEN-3/4]\n"
            f"{spec['shot_type']}: {spec['subject']} - {spec['action']} "
            f"{spec['product']} in {spec['setting']}. "
            f"Camera direction: {spec['camera_move'].lower()}. "
            f"{spec['style']}, {spec['lighting']}, {spec['color_grade']}. "
            f"{spec['aspect_ratio']}, {spec['duration_s']}s."
        )

    def render_all(self, spec: Dict[str, Any]) -> Dict[str, str]:
        return {
            "higgsfield": self.render_higgsfield(spec),
            "sora": self.render_sora(spec),
            "veo": self.render_veo(spec),
            "kling": self.render_kling(spec),
            "runway": self.render_runway(spec),
        }

    # ------------------------------------------------------------------ #
    # Script -> full prompt set
    # ------------------------------------------------------------------ #
    def build_from_script(
        self, script: Dict[str, Any], tools: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Turn a generated script (from AdScriptGenerator) into a per-scene set of
        video prompts.

        Args:
            script: output of AdScriptGenerator.generate_script()
            tools: subset of ['higgsfield','sora','veo','kling','runway'].
                   Defaults to Higgsfield + Sora + Kling (best for UGC ads).
        """
        tools = tools or ["higgsfield", "sora", "kling"]
        results: List[Dict[str, Any]] = []
        for scene in script.get("scenes", []):
            spec = self.build_shot_spec(
                scene_description=scene.get("b_roll", scene.get("voiceover", "")),
                beat_label=scene.get("beat", "Scene"),
                duration_s=int(scene.get("seconds", 5)),
                intent_hint=scene.get("beat", ""),
            )
            rendered = self.render_all(spec)
            results.append({
                "beat": scene.get("beat"),
                "shot_spec": spec,
                "prompts": {t: rendered[t] for t in tools if t in rendered},
            })
        return results


if __name__ == "__main__":
    brief = {
        "product": "GlowDrip Vitamin-C serum",
        "audience": "busy women in their 30s",
        "platform": "TikTok",
        "visual_style": "ugc",
    }
    builder = VideoPromptBuilder(brief)
    spec = builder.build_shot_spec(
        "Creator holds the serum up to the camera and applies one drop, smiling.",
        beat_label="Hook",
        duration_s=5,
    )
    print(builder.render_higgsfield(spec))
    print("\n" + builder.render_sora(spec))
