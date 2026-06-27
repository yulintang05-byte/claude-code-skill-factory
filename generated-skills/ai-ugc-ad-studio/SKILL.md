---
name: ai-ugc-ad-studio
description: Generates complete AI video ad campaigns - scroll-stopping scripts, copy-paste prompts for Higgsfield/Sora/Veo/Kling/Runway, client outreach, pricing tiers, and a revenue plan - to start and run a UGC ad-creative side business
---

# AI UGC Ad Studio

A complete revenue engine for creators selling short-form AI video ads to e-commerce brands and local businesses. From one short brief, it produces everything you need to **make and sell ads**: the creative (scripts + AI video prompts), the sales (cold outreach + objection handling), and the business model (pricing + a concrete path to $500/week and $10k/month).

This skill is built around one proven play: use AI video tools (Higgsfield and friends) to make scroll-stopping ads fast, then sell them to people who already pay for marketing — **leading every pitch with a free sample**.

## Capabilities

- **AI video ad scripts**: Generates A/B-ready scripts using proven direct-response frameworks (AIDA, PAS, Hook-Retain-Reward, Before-After-Bridge) with scene-by-scene voiceover, on-screen text, and B-roll direction.
- **Hook generator**: Produces a spread of scroll-stopping hooks across 7 psychological angles (problem call-out, bold claim, curiosity, pattern interrupt, social proof, POV, question).
- **AI video prompt builder ("the promo generator")**: Converts each scene into copy-paste-ready prompts formatted specifically for **Higgsfield** (with camera-motion presets), **Sora**, **Google Veo**, **Kling**, and **Runway**, including aspect ratio, lighting, style, and negative prompts.
- **Client outreach kit**: Personalized Instagram DM, cold email, SMS, walk-in pitch, and Upwork/Fiverr proposal — all sample-first — plus a 3-touch follow-up sequence and objection handlers.
- **Pricing & offers**: Productized tiers (Starter Pack, Growth Retainer, Scale Partner) with niche-aware pricing and upsells.
- **Revenue plan**: Calculates exactly how many packs/retainers you need for $500/week and $10k/month, checks it against your delivery capacity, and lays out a 30-day ramp.
- **Toolchain cost estimator**: Compares the real cost of running the agency across cloud API (pay-per-use gateways like Muapi.ai/fal.ai), rented GPU (RunPod self-host), and owned GPU — with per-ad cost, monthly cost, profit margin, and GPU payback.
- **One-command kit**: The pipeline assembles all of the above into a single Markdown or JSON deliverable.

## Input Requirements

A single JSON brief (all fields optional — sensible defaults fill the gaps):

| Field | Purpose |
|-------|---------|
| `business`, `contact_name` | Who you're making ads for / pitching |
| `product`, `niche`, `category` | What's being sold |
| `audience`, `pain`, `result`, `benefits` | The angle the ads hammer on |
| `platform`, `visual_style` | Drives aspect ratio + look (TikTok/Reels/Shorts/YouTube) |
| `offer`, `price`, `discount`, `code`, `keyword` | The deal in scripts + outreach |
| `your_name`, `city` | Personalizes outreach |
| `videos_per_day`, `minutes_per_video`, `work_days_per_week` | Capacity for the revenue plan |
| `video_tools` | Subset of `higgsfield`, `sora`, `veo`, `kling`, `runway` |

See `sample_input.json` for a complete example.

## Output Formats

- **Markdown** (`--format md`): A ready-to-use campaign kit you can read, paste, and act on immediately.
- **JSON** (`--format json`): Structured data (see `expected_output.json`) for piping into other tools, spreadsheets, or automations.

Top-level output keys: `meta`, `hooks`, `ad_scripts`, `video_prompts`, `outreach`, `pricing_and_revenue`.

## How to Use

Conversationally with Claude:

> "Use the ai-ugc-ad-studio skill to build a full ad kit for my friend's coffee shop in Chicago — product is their cold brew, platform TikTok."

Or run the pipeline directly:

```bash
# Built-in demo
python pipeline.py --demo --format md

# From your own brief
python pipeline.py --input sample_input.json --format md --out my_kit.md

# Structured JSON for automation
python pipeline.py --input sample_input.json --format json --out kit.json

# Estimate what the toolchain costs at your volume (cloud vs rented vs owned GPU)
python toolchain_cost.py --ads-per-month 120 --pack-price 300 --ads-per-pack 5
```

## Scripts

- `ad_script_generator.py`: Hook library + framework-based script generation (`AdScriptGenerator`).
- `video_prompt_builder.py`: Scene → platform-specific AI video prompts (`VideoPromptBuilder`).
- `outreach_generator.py`: Sample-first cold outreach across channels (`OutreachGenerator`).
- `offer_pricing.py`: Pricing tiers + revenue/capacity planning (`OfferPricing`).
- `toolchain_cost.py`: Cost of running the agency across cloud/rented-GPU/owned-GPU paths (`ToolchainCostEstimator`).
- `pipeline.py`: Orchestrator + CLI that assembles the full kit (`AdStudioPipeline`).

Each module is standard-library only and runs standalone (`python <module>.py`) for a quick self-test.

## Best Practices

1. **Always lead with a free sample.** The outreach and pricing are designed around showing a real video before pitching — it dramatically raises reply and close rates.
2. **Test hooks, not whole videos.** Produce one script with 3–5 different hooks; the hook decides 80% of performance.
3. **Match aspect ratio to platform.** The builder defaults correctly (9:16 for TikTok/Reels/Shorts), but confirm before rendering.
4. **Sell retainers, not one-offs.** One-time packs get you to $500/week fast; retainers are what actually reach $10k/month.
5. **Personalize the first line** of every outreach message per business — everything after can be templated.
6. **Respect capacity.** Use real `videos_per_day` numbers so the revenue plan flags when a target outruns your delivery.

## Limitations

- This skill **generates assets and a plan; it does not render video or send messages.** Paste the prompts into Higgsfield/Sora/etc. and the outreach into your own accounts.
- Revenue figures are **planning aids based on your inputs, not income guarantees.** Results depend on outreach volume, niche, offer, and delivery quality.
- AI video tools, their features, and their prompt syntax change frequently — treat tool-specific phrasing as a strong starting point and adjust to the current UI.
- Always disclose AI-generated content where the platform, client, or law requires it, and only make ads for businesses and claims you can stand behind.

## Integration with Other Skills

- **content-trend-researcher** → feed trending angles/hooks into your briefs.
- **prompt-factory** → generate deeper custom prompts for specific scenes.
- **social-media-analyzer** → measure which hooks/ads actually performed, then iterate.

---

**Version**: 1.0.0
**Last Updated**: June 21, 2026
**Compatibility**: Claude.ai, Claude Code, Claude API (with Code Execution Tool)
