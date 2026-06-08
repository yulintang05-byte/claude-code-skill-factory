# SPY Intraday Reversal Playbook

A cold, practical reference for how SPY actually behaves during the regular
session, with the emphasis on **reversals**. These are *tendencies*, not laws.
They shift with volatility regime (a calm 12-VIX tape behaves nothing like a
panic 30-VIX tape), and every one of them should be **backtested on current
data** before you risk money on it — that's what `analyze.py backtest` is for.

> The golden rule of reversals: **trade the confirmation, not the prediction.**
> Picking tops and bottoms in front of momentum is how accounts die. A reversal
> isn't real until price *proves* the old direction failed (a reclaim, a lower
> high after the push, a failed new high). Your edge is in the second chance,
> not the first guess.

---

## 1. The intraday clock (US Eastern)

SPY's character changes by time of day. Most of the day's reversals cluster at
predictable windows.

| Window | Character | Reversal relevance |
|---|---|---|
| **04:00–09:30 pre-market** | Thin, headline-driven | Sets overnight high/low (ONH/ONL) and pre-market high/low — key reference levels for the day |
| **09:30–10:00 opening drive** | Highest volatility & volume of the day | The opening range forms here; the **first failed move** often marks the session high/low |
| **10:00–11:00 morning trend** | Trend extends or first reversal hits | 10:00 econ data (ISM, sentiment) is a common reversal trigger |
| **11:00–11:30 first balance** | Momentum cools | Initial trend exhaustion; divergence shows up here |
| **11:30–13:30 lunch** | Low volume, choppy, mean-reverting | **Range/fade environment.** Breakouts here fail often; VWAP reversion works best |
| **13:30–14:00 afternoon wake-up** | Volume returns | The "lunch reversal" — the morning move often resumes OR cleanly reverses |
| **14:00 FOMC days** | Binary | On Fed days, 14:00 is the whole day. Everything before is noise |
| **14:00–15:00 trend leg** | Directional | The "real" afternoon trend establishes |
| **15:00–16:00 power hour** | Volume + volatility spike | Biggest reversals and squeezes; MOC imbalances drive the last 10 min |

**Practical takeaway:** fade-style reversals (VWAP stretch, band tags) are
highest-probability during **lunch**; momentum-failure reversals are richest in
the **opening hour** and **power hour**.

---

## 2. The reference levels that matter

Reversals happen *at levels*, not in the middle of nowhere. The engine's
`key_level_rejection` signal watches these. In rough order of importance:

1. **VWAP** — the intraday center of gravity and the single most important
   intraday level. Institutions benchmark to it. Price stretched 2+ ATR from
   VWAP is a mean-reversion candidate; price rejecting VWAP from below/above is
   a continuation/reversal decision point.
2. **Prior Day High / Low (PDH / PDL)** — the most-watched horizontal levels.
   First touch often rejects; a *failed* break (poke through then reclaim) is a
   premier reversal trigger.
3. **Overnight High / Low (ONH / ONL)** and **pre-market high/low** — define the
   overnight balance; breaks and failures here set the morning tone.
4. **Opening Range High/Low** (first 5/15/30 min) — the opening-range *reversal*
   (break that fails back inside) is one of the cleaner setups on SPY.
5. **Floor-trader pivots** (PP, R1–R3, S1–S3) — computed from prior session
   H/L/C; mechanical levels many desks still use. (`indicators.classic_pivots`.)
6. **Round numbers** — SPY whole/half dollars and the SPX/ES big figures
   (e.g., 5000, 5500) act as magnets and rejection points.
7. **Prior week / month high-low and value areas** — slower levels that matter
   on the higher timeframes.

The highest-probability reversals occur at **confluence** — where several of
these stack within an ATR of each other.

---

## 3. Trend day vs. range day (decide this first)

Whether reversals *work* depends entirely on the day type. Misreading this is
the #1 way fade traders get run over.

**Signs of a TREND day (fade reversals fail — don't fight it):**
- Wide opening range, strong directional first 30 min on heavy volume.
- Price stays on one side of VWAP and keeps making higher highs / lower lows.
- Shallow pullbacks that don't reclaim the prior swing.
- Breadth/internals (advancers vs decliners) strongly one-sided.
- *Strategy:* trade pullback continuations, not reversals. The only reversal that
  works on a trend day is the **end-of-trend exhaustion** late in the session.

**Signs of a RANGE day (reversals are the edge):**
- Narrow/overlapping opening range, two-sided early action.
- Price oscillates around VWAP, repeatedly tags and rejects the same H/L.
- Declining volume into midday.
- *Strategy:* fade the edges of the range back toward VWAP; mean reversion rules.

**Rule of thumb:** the first hour usually tells you. If the opening 60 minutes
makes a clean directional run and holds, assume trend until proven otherwise. If
it chops and reverses, assume range.

---

## 4. The reversal pattern catalog

These map to the detectors in `reversals.py`. Each is described with what it is,
why it works, and how it fails.

### 4.1 Failed breakout / failed breakdown ("the trap") — highest conviction
- **What:** price breaks a key level (PDH, ORH, round number), fails to follow
  through, and snaps back inside within a few bars.
- **Why it works:** breakout buyers/sellers are now trapped offside; their stops
  fuel the reversal. This is the single most reliable intraday reversal.
- **Confirmation:** a *close back inside* the level, ideally with a rejection
  wick. Entry on the reclaim, stop beyond the failed extreme.
- **Fails when:** it wasn't a real break (just a wick) or the breakout was on a
  genuine trend day with real volume — then it's a pullback, not a trap.

### 4.2 Double top / double bottom at a level
- **What:** two swing highs/lows at roughly the same price (within ~0.5 ATR).
- **Why:** the level has been defended twice; the second failure invites the
  reversal. (`double_extreme` detector.)
- **Confirmation:** break of the intervening swing (the "neckline").
- **Fails when:** the level is a magnet on a trend day and the third push breaks
  it. Reversals at a level get *weaker* with each retest, not stronger.

### 4.3 Divergence at an extreme
- **What:** price makes a higher high (or lower low) but RSI/MACD does not.
  (`rsi_divergence` detector.)
- **Why:** momentum is fading even as price extends; the move is running on
  fumes.
- **Confirmation:** divergence alone is *not* a signal — it's a condition. Wait
  for a price trigger (failed high, structure break). Divergence can persist for
  a long time in a strong trend.
- **Fails when:** traded standalone, in front of momentum. This is the most
  *abused* reversal tool.

### 4.4 VWAP-stretch mean reversion
- **What:** price extends 2+ ATR from session VWAP. (`vwap_stretch` detector.)
- **Why:** intraday price is mean-reverting to VWAP, especially on range days
  and during lunch.
- **Confirmation:** a stalling/reversal bar; target is VWAP itself.
- **Fails when:** a trend day — stretch from VWAP just keeps stretching. Pair
  with the day-type read in §3.

### 4.5 Band tag + reclaim (Bollinger reversion)
- **What:** price pierces the lower/upper band and closes back inside.
  (`bollinger_reversion` detector.)
- **Why:** statistical over-extension snapping back to the mean.
- **Fails when:** "walking the band" on a trend day (consecutive closes outside).

### 4.6 Exhaustion / climax reversal
- **What:** a volume + range spike into a level (capitulation or blow-off),
  often a wide bar with a big rejection wick.
- **Why:** the last buyers/sellers have committed; there's no one left to push.
- **Confirmation:** failure to make a new extreme on the next bars.
- **Fails when:** the climax is the *start* of a trend acceleration, not the end.

### 4.7 Candlestick triggers (the entry, not the thesis)
Engulfing bars, hammers, shooting stars, and pin bars (`candlestick` detector)
are **triggers** that confirm the patterns above. A hammer at PDL with RSI
divergence and a VWAP stretch is a setup; a hammer in the middle of nowhere is
noise.

---

## 5. Reversal time-of-day tendencies

- **Opening reversal (~09:45–10:15):** the initial drive exhausts; the first
  swing high/low of the day frequently caps the session.
- **Lunch reversal (~12:00):** a fade of the morning move as volume dries up.
- **Afternoon reversal (~13:30–14:00):** volume returns and either resumes or
  cleanly reverses the morning. Watch 10:00 and 14:00 data.
- **Power-hour reversal (~15:00):** the day's trend often makes its final push
  and reverses, or squeezes violently into the close.
- **MOC imbalance (15:50–16:00):** market-on-close order imbalances can shove
  the last ten minutes hard in one direction.

---

## 6. How to grade a reversal setup (confluence checklist)

The engine does this numerically, but here's the human version. Count the boxes:

- [ ] At a **named level** (VWAP / PDH-PDL / pivot / round number)?
- [ ] **Day type** supports it (range day for fades; exhaustion for trend-end)?
- [ ] **Momentum divergence** present (RSI/MACD not confirming)?
- [ ] A **price trigger** has fired (failed break, structure break, reversal bar)?
- [ ] **Volume** confirms (climax into the level, or drying up at the extreme)?
- [ ] In a **favorable time window** (open / lunch / power hour)?
- [ ] **No major macro release** about to detonate in the next 30 min?

Three+ boxes = a setup worth the engine's 60+ score. One box = noise. The score
is *quality*, never a probability — §"honest framing" in `SKILL.md`.

---

## 7. Risk management for reversal trading (non-negotiable)

Reversals are lower win-rate, higher reward-to-risk than trend trades. The math
only works if you respect the risk:

1. **Define risk before entry.** Stop goes beyond the failed extreme (the point
   that proves you wrong). The engine uses 1.5× ATR by default.
2. **Risk ≤ 1% of the account per trade.** Reversals fail often; survive the
   losing streak. The backtester reports `max_consecutive_losses` — size for it.
3. **Demand asymmetry.** Aim for ≥ 2R. A 40% win rate at 2R is profitable; a 40%
   win rate at 1R is not.
4. **Take partials at the first target** (often VWAP or the 1R level), trail the
   rest. Reversals that work tend to work fast.
5. **Time-stop intraday.** If it hasn't worked within your expected window, the
   thesis is stale. Day-trade flat by the close — no hoping into tomorrow.
6. **One macro event can void every level.** Flatten or stand aside into FOMC,
   CPI, NFP. The first post-release move is a coin flip that frequently reverses.

---

## 8. What this playbook is not

It is not a promise that reversals "work." It is a map of *tendencies* that have
shown up repeatedly in SPY's intraday structure. Whether any of them is an edge
**for you, on today's tape, after your costs** is an empirical question with
exactly one honest answer: the backtest. Run it.
