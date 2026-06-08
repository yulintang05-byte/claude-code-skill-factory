"""
News + macro-catalyst module for SPY.

Two layers, because a day trader needs both:

1. **Headlines (live, best-effort).** Pulls a handful of public market RSS feeds
   over ``urllib``. In locked-down environments outbound requests are blocked
   (Yahoo returns 403 here, for example), so this layer is wrapped in defensive
   error handling and simply reports "offline" rather than crashing.

2. **Scheduled macro catalysts (always available, offline).** A curated, static
   reference of the recurring high-impact events that actually move SPY -- FOMC,
   CPI, PCE, NFP, etc. -- with the time of day they hit and *why* they matter.
   This is the part you plan your trading day around; it never depends on the
   network.

Headlines are scored with a transparent, rule-based hawkish/dovish &
risk-on/risk-off keyword model. It is deliberately simple and auditable -- not a
black box, and not presented as predictive.
"""

from __future__ import annotations

import json
import re
import socket
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET


# Public market-news RSS endpoints (no key required). Many may be blocked.
RSS_FEEDS = {
    "Yahoo Finance (SPY)": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=SPY&region=US&lang=en-US",
    "Nasdaq Markets": "https://www.nasdaq.com/feed/rssoutbound?category=Markets",
    "CNBC Top News": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
    "MarketWatch Top": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
}

USER_AGENT = "Mozilla/5.0 (compatible; spy-day-trading-skill/1.0)"


# ---------------------------------------------------------------------------
# Recurring macro catalysts (static, offline reference)
# ---------------------------------------------------------------------------
# Times are US Eastern. SPY's biggest single-day moves cluster around these.
MACRO_CALENDAR: List[Dict[str, str]] = [
    {"event": "FOMC Rate Decision", "cadence": "8x/year (scheduled)", "time_et": "14:00",
     "impact": "extreme", "why": "Sets the fed funds rate; the 14:00 statement + 14:30 "
     "Powell presser routinely swing SPY 1-3% intraday. The single most important event."},
    {"event": "CPI (Consumer Price Index)", "cadence": "Monthly (~mid-month)", "time_et": "08:30",
     "impact": "extreme", "why": "The market's primary inflation read. A hot/cold surprise "
     "vs. consensus reprices rate expectations instantly; gaps and fast reversals are common."},
    {"event": "Core PCE", "cadence": "Monthly (~end of month)", "time_et": "08:30",
     "impact": "high", "why": "The Fed's *preferred* inflation gauge. Less volatile than CPI "
     "but watched closely for confirmation of the trend."},
    {"event": "Non-Farm Payrolls (Jobs Report)", "cadence": "Monthly (1st Friday)", "time_et": "08:30",
     "impact": "extreme", "why": "Headline jobs + wage growth + unemployment. Whipsaws the "
     "8:30 open; the knee-jerk move frequently reverses within the first hour."},
    {"event": "Initial Jobless Claims", "cadence": "Weekly (Thursday)", "time_et": "08:30",
     "impact": "medium", "why": "High-frequency labor pulse. Usually minor, but matters more "
     "when the market is laser-focused on labor softening."},
    {"event": "PPI (Producer Price Index)", "cadence": "Monthly", "time_et": "08:30",
     "impact": "high", "why": "Upstream inflation; often previews CPI and feeds PCE estimates."},
    {"event": "Retail Sales", "cadence": "Monthly", "time_et": "08:30",
     "impact": "high", "why": "Consumer-spending health; key for the 'soft landing' narrative."},
    {"event": "ISM Manufacturing / Services PMI", "cadence": "Monthly (1st & 3rd biz day)", "time_et": "10:00",
     "impact": "high", "why": "Forward-looking activity. The 10:00 release can reverse the "
     "opening move."},
    {"event": "GDP (Advance/Second/Third)", "cadence": "Quarterly", "time_et": "08:30",
     "impact": "medium", "why": "Backward-looking growth; matters most when recession fears run high."},
    {"event": "Michigan Consumer Sentiment", "cadence": "Twice monthly", "time_et": "10:00",
     "impact": "medium", "why": "Includes inflation *expectations*, which the Fed cites."},
    {"event": "Triple/Quadruple Witching", "cadence": "Quarterly (3rd Fri Mar/Jun/Sep/Dec)", "time_et": "16:00",
     "impact": "high", "why": "Options + futures expiry. Volume explodes and the close gets "
     "pinned/whipped around large open-interest strikes."},
    {"event": "Month/Quarter-End Rebalance", "cadence": "Last session of month/quarter", "time_et": "15:00-16:00",
     "impact": "medium", "why": "Pension/fund rebalancing flows distort the last hour."},
]

HAWKISH = ["hot inflation", "rate hike", "higher for longer", "hawkish", "sticky inflation",
           "stronger than expected", "beats", "surge", "jumps", "accelerat", "tightening"]
DOVISH = ["rate cut", "cooling", "dovish", "softer", "misses", "slows", "weaker than expected",
          "easing", "disinflation", "pause", "pivot"]
RISK_OFF = ["selloff", "plunge", "tumble", "crash", "war", "default", "downgrade", "recession",
            "bankruptcy", "contagion", "slump", "fear"]
RISK_ON = ["rally", "soars", "record high", "all-time high", "surges", "optimism", "relief",
           "rebound", "melt-up", "goldilocks"]


@dataclass
class Headline:
    title: str
    source: str
    published: str = ""
    link: str = ""
    sentiment: str = "neutral"
    score: int = 0


@dataclass
class NewsReport:
    online: bool
    fetched_at: str
    headlines: List[Headline] = field(default_factory=list)
    macro_calendar: List[Dict[str, str]] = field(default_factory=list)
    net_sentiment: str = "neutral"
    notes: List[str] = field(default_factory=list)


def _score_text(text: str) -> (int, str):  # type: ignore[syntax]
    t = text.lower()
    score = 0
    score += sum(2 for kw in RISK_ON if kw in t)
    score -= sum(2 for kw in RISK_OFF if kw in t)
    score += sum(1 for kw in DOVISH if kw in t)   # dovish ~ supportive for equities
    score -= sum(1 for kw in HAWKISH if kw in t)
    label = "neutral"
    if score >= 2:
        label = "risk-on / supportive"
    elif score <= -2:
        label = "risk-off / pressure"
    return score, label


def _fetch_feed(name: str, url: str, timeout: float = 6.0) -> List[Headline]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    headlines: List[Headline] = []
    for item in items[:15]:
        title_el = item.find("title") or item.find("{http://www.w3.org/2005/Atom}title")
        link_el = item.find("link") or item.find("{http://www.w3.org/2005/Atom}link")
        date_el = item.find("pubDate") or item.find("{http://www.w3.org/2005/Atom}updated")
        title = (title_el.text or "").strip() if title_el is not None else ""
        if not title:
            continue
        link = ""
        if link_el is not None:
            link = (link_el.text or link_el.get("href") or "").strip()
        score, label = _score_text(title)
        headlines.append(Headline(
            title=title, source=name,
            published=(date_el.text or "").strip() if date_el is not None else "",
            link=link, sentiment=label, score=score,
        ))
    return headlines


def fetch_news(max_headlines: int = 20, timeout: float = 6.0) -> NewsReport:
    """Best-effort live headlines + the always-available macro calendar."""
    socket.setdefaulttimeout(timeout)
    headlines: List[Headline] = []
    notes: List[str] = []
    online = False

    for name, url in RSS_FEEDS.items():
        try:
            got = _fetch_feed(name, url, timeout)
            if got:
                online = True
                headlines.extend(got)
        except Exception as exc:  # noqa: BLE001 - any network/parse failure -> offline
            notes.append(f"{name}: unavailable ({type(exc).__name__})")

    headlines.sort(key=lambda h: abs(h.score), reverse=True)
    headlines = headlines[:max_headlines]

    if not online:
        notes.insert(0, "Live headlines are blocked or unreachable in this environment "
                        "(common in locked-down sessions). Using the offline macro calendar. "
                        "Run this skill locally with network access for live news.")

    total = sum(h.score for h in headlines)
    net = "neutral"
    if total >= 3:
        net = "risk-on / supportive"
    elif total <= -3:
        net = "risk-off / pressure"

    return NewsReport(
        online=online,
        fetched_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        headlines=headlines,
        macro_calendar=MACRO_CALENDAR,
        net_sentiment=net,
        notes=notes,
    )


def render_report(report: NewsReport) -> str:
    lines: List[str] = []
    lines.append("=" * 70)
    lines.append(f"SPY NEWS & CATALYSTS  |  {report.fetched_at}  |  "
                 f"{'LIVE' if report.online else 'OFFLINE (calendar only)'}")
    lines.append("=" * 70)

    if report.headlines:
        lines.append(f"\nTOP HEADLINES (net tone: {report.net_sentiment})")
        lines.append("-" * 70)
        for h in report.headlines:
            tag = {"risk-on / supportive": "[+]", "risk-off / pressure": "[-]"}.get(h.sentiment, "[ ]")
            lines.append(f"{tag} {h.title}")
            lines.append(f"     {h.source}  {h.published}")
    else:
        lines.append("\nNo live headlines available.")

    lines.append("\nRECURRING HIGH-IMPACT CATALYSTS (US Eastern) -- plan your day around these")
    lines.append("-" * 70)
    for ev in report.macro_calendar:
        lines.append(f"[{ev['impact'].upper():7s}] {ev['time_et']} ET  {ev['event']}  "
                     f"({ev['cadence']})")
        lines.append(f"            -> {ev['why']}")

    if report.notes:
        lines.append("\nNOTES")
        lines.append("-" * 70)
        for note in report.notes:
            lines.append(f"  - {note}")

    lines.append("\n" + "=" * 70)
    lines.append("Reminder: news creates volatility, not direction you can count on. The "
                 "first move after a release frequently reverses. This is information, "
                 "not a trade signal.")
    lines.append("=" * 70)
    return "\n".join(lines)


def to_json(report: NewsReport) -> str:
    return json.dumps({
        "online": report.online,
        "fetched_at": report.fetched_at,
        "net_sentiment": report.net_sentiment,
        "headlines": [vars(h) for h in report.headlines],
        "macro_calendar": report.macro_calendar,
        "notes": report.notes,
    }, indent=2)


if __name__ == "__main__":
    print(render_report(fetch_news()))
