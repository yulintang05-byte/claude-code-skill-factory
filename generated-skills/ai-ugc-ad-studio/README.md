# AI UGC Ad Studio

**Turn AI video tools into a paid service.** This skill generates a complete, ready-to-use campaign kit for selling short-form AI video ads to e-commerce brands and local businesses — the creative, the sales messages, and the business model — from a single short brief.

It's built around one proven play: make scroll-stopping ads fast with **Higgsfield / Sora / Veo / Kling / Runway**, then sell them by **leading every pitch with a free sample**.

---

## What You Get

From one brief, the pipeline produces:

1. **Hooks** — a spread of scroll-stopping hooks across 7 angles.
2. **Ad scripts** — A/B variants using AIDA / PAS / Hook-Retain-Reward / Before-After-Bridge, with scene-by-scene voiceover, on-screen text, and B-roll.
3. **AI video prompts** — copy-paste-ready prompts for **Higgsfield** (with camera-motion presets), Sora, Veo, Kling, and Runway.
4. **Outreach kit** — sample-first DM, email, SMS, walk-in pitch, Upwork proposal, follow-ups, and objection handlers.
5. **Pricing + revenue plan** — productized tiers and the exact math for **$500/week and $10k/month**, plus a 30-day ramp.
6. **Toolchain cost estimator** — what generation actually costs (cloud pay-per-use vs self-hosted GPU), per-ad cost, margin, and GPU payback.

---

## Installation

Copy the folder into your Claude Code skills directory:

```bash
# Personal (all projects)
cp -r generated-skills/ai-ugc-ad-studio ~/.claude/skills/

# Or project-level
cp -r generated-skills/ai-ugc-ad-studio .claude/skills/
```

Restart Claude Code (or reload skills). The skill loads automatically when your task involves AI video ads, UGC content, or selling ad-creative services.

**Requirements**: Python 3.8+ (standard library only — no `pip install` needed).

---

## Quick Start

```bash
cd ai-ugc-ad-studio

# See it work instantly with the built-in demo
python pipeline.py --demo --format md

# Run it on your own brief
python pipeline.py --input sample_input.json --format md --out my_kit.md

# Get structured JSON instead (for spreadsheets / automation)
python pipeline.py --input sample_input.json --format json --out kit.json
```

Or just ask Claude:

> "Use the ai-ugc-ad-studio skill to build a full ad kit for a nail salon in Miami called Bella's Nail Bar."

---

## File Overview

| File | Role |
|------|------|
| `SKILL.md` | Skill definition and documentation |
| `pipeline.py` | Orchestrator + CLI — one command builds the whole kit |
| `ad_script_generator.py` | Hooks + framework-based ad scripts |
| `video_prompt_builder.py` | Scene → Higgsfield/Sora/Veo/Kling/Runway prompts |
| `outreach_generator.py` | Sample-first client outreach across channels |
| `offer_pricing.py` | Pricing tiers + revenue/capacity planning |
| `toolchain_cost.py` | Cost of running the agency: cloud API vs rented GPU vs owned GPU |
| `sample_input.json` | Example brief |
| `expected_output.json` | Example JSON output |
| `HOW_TO_USE.md` | Detailed usage examples |

---

## Honest Disclaimer

This skill **generates assets and a plan — it does not render video or send messages for you.** Paste prompts into your AI video tool and outreach into your own accounts. Revenue figures are **planning aids based on your inputs, not income guarantees**; results depend on your outreach volume, niche, offer, and delivery. Only advertise businesses and claims you can stand behind, and disclose AI-generated content where required.

---

**Version**: 1.0.0 · **Compatibility**: Claude.ai, Claude Code, Claude API (Code Execution Tool)
