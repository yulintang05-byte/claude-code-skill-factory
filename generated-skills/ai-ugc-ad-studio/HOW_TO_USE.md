# How to Use the AI UGC Ad Studio Skill

Hey Claude—I just added the "ai-ugc-ad-studio" skill. Can you build me a complete AI video ad kit for [business] so I can start landing clients?

This guide shows you exactly how to use it — both conversationally with Claude and via the command line.

---

## Quick Start

The fastest way to see what it does:

```bash
cd ai-ugc-ad-studio
python pipeline.py --demo --format md
```

This prints a full campaign kit (hooks, scripts, AI video prompts, outreach, pricing, and a 30-day plan) for a demo skincare brand.

---

## Example Invocations (with Claude)

**Example 1 — Full kit for a local business:**
> Hey Claude—use the "ai-ugc-ad-studio" skill to build a complete ad kit for "Bella's Nail Bar" in Miami. Product is their gel manicures, platform is Instagram Reels, and I want to charge $300 for 5 ads.

**Example 2 — E-commerce product ads:**
> Hey Claude—use "ai-ugc-ad-studio" to generate 3 TikTok ad scripts and Higgsfield prompts for a Vitamin-C serum aimed at women in their 30s.

**Example 3 — Just the outreach:**
> Hey Claude—using "ai-ugc-ad-studio", write me sample-first cold DMs and a 3-touch follow-up sequence to pitch video ads to dentists in my city.

**Example 4 — Just the money plan:**
> Hey Claude—use "ai-ugc-ad-studio" to show me exactly how many clients I need at $350/pack to hit $500/week and $10k/month, given I can make 8 videos a day.

---

## Running It Yourself (CLI)

### 1. Build a kit from your own brief

Create a JSON brief (copy `sample_input.json` and edit it):

```bash
python pipeline.py --input my_brief.json --format md --out my_kit.md
```

### 2. Get structured JSON (for spreadsheets / automation)

```bash
python pipeline.py --input my_brief.json --format json --out kit.json
```

### 3. Control how many script variants

```bash
python pipeline.py --input my_brief.json --scripts 5 --format md
```

### 4. Use individual modules

```bash
python ad_script_generator.py     # hooks + a sample script
python video_prompt_builder.py    # Higgsfield + Sora prompts for one scene
python outreach_generator.py      # a sample DM + email subject
python offer_pricing.py           # pricing + the $500/week and $10k/month math
```

---

## What to Provide

Everything is optional (defaults fill the gaps), but the more you give, the better the output:

- **The business**: `business`, `contact_name`, `city`
- **The product**: `product`, `niche`, `category`
- **The angle**: `audience`, `pain`, `result`, `benefits` (list)
- **The platform/look**: `platform` (TikTok/Reels/Shorts/YouTube), `visual_style` (`ugc`, `cinematic`, `premium`, `vibrant`)
- **The offer**: `offer`, `price`, `discount`, `code`, `keyword`
- **You**: `your_name`
- **Capacity** (for the revenue plan): `videos_per_day`, `minutes_per_video`, `work_days_per_week`
- **Tools**: `video_tools` — any of `higgsfield`, `sora`, `veo`, `kling`, `runway`

---

## What You'll Get

- A set of **hooks** to test first (the hook decides most of the performance)
- Multiple **ad scripts** (different frameworks/angles) with voiceover, on-screen text, and B-roll
- **Copy-paste AI video prompts** per scene, formatted for each tool you chose
- A **sample-first outreach kit** (DM, email, SMS, walk-in, Upwork) + follow-ups + objection handling
- **Pricing tiers** and a **revenue plan** showing the exact path to $500/week and $10k/month
- A **30-day action plan**

---

## A Realistic Workflow (Day 1 → first sale)

1. Pick 3 local businesses or e-com brands. Run the pipeline for each.
2. Take the **Hook** scene's Higgsfield prompt → make one quick sample video per business.
3. Send the generated **sample-first DM/email** with that video attached (aim for 25/day).
4. When someone replies, use the **pricing tier** + **objection handlers** to close a Starter Pack.
5. Deliver fast, get a testimonial, then pitch the **Growth Retainer** — that's the road to $10k/month.

---

## Notes & Honest Limits

- The skill **creates assets; it doesn't render video or send messages.** Paste prompts into your AI video tool and outreach into your own accounts.
- Revenue numbers are **planning aids, not guarantees.**
- AI video tools change often — adjust tool-specific phrasing to the current UI.
- Only make ads for businesses/claims you can stand behind, and disclose AI content where required.
