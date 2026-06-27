"""
Client Outreach Generator
Generates personalized, sample-first cold outreach to land paid AI-video / UGC
ad clients (local businesses + e-commerce brands). Covers Instagram DM, cold
email, SMS, in-person/walk-in pitch, and Upwork/Fiverr proposals, plus a
multi-touch follow-up sequence and objection handling.

The winning play baked in here: lead with a FREE sample video, then sell the pack.
Standard library only.
"""

from typing import Dict, List, Any


class OutreachGenerator:
    """Builds outreach messages tuned to convert with a sample-first offer."""

    def __init__(self, brief: Dict[str, Any]):
        """
        Args:
            brief: may contain business, contact_name, niche, city, pain,
                   result, your_name, offer, price, sample_link, calendar_link,
                   portfolio_link.
        """
        self.brief = brief or {}
        self.business = self.brief.get("business", "your business")
        self.contact = self.brief.get("contact_name", "there")
        self.niche = self.brief.get("niche", "your industry")
        self.city = self.brief.get("city", "your area")
        self.pain = self.brief.get("pain", "standing out on social media")
        self.result = self.brief.get("result", "more views and customers")
        self.your_name = self.brief.get("your_name", "Alex")
        self.offer = self.brief.get("offer", "5 scroll-stopping video ads")
        self.price = self.brief.get("price", 300)
        self.sample_link = self.brief.get("sample_link", "[your sample video link]")
        self.calendar_link = self.brief.get("calendar_link", "[your booking link]")
        self.portfolio = self.brief.get("portfolio_link", "[your portfolio link]")

    # ------------------------------------------------------------------ #
    # Channels
    # ------------------------------------------------------------------ #
    def instagram_dm(self) -> str:
        return (
            f"Hey {self.contact}! 👋 I came across {self.business} and your "
            f"{self.niche} stuff is great. I actually made you a quick sample "
            f"video ad (free, no strings): {self.sample_link}\n\n"
            f"I make short-form video ads that get {self.result}. If you like the "
            f"sample I can do {self.offer} for ${self.price}. Want me to send a "
            f"couple more concepts?"
        )

    def cold_email(self) -> Dict[str, str]:
        subject = f"made a free video ad for {self.business} 🎬"
        body = (
            f"Hi {self.contact},\n\n"
            f"I'll keep this short. I make scroll-stopping short-form video ads "
            f"for {self.niche} businesses in {self.city}, and I put together a "
            f"FREE sample for {self.business}:\n\n"
            f"  {self.sample_link}\n\n"
            f"No catch - I'd rather show you than pitch you. The goal of these is "
            f"simple: {self.result} without you having to film anything.\n\n"
            f"If you like it, I can deliver {self.offer} for ${self.price} this "
            f"week. Worth a quick look?\n\n"
            f"Best,\n{self.your_name}\n{self.portfolio}"
        )
        return {"subject": subject, "body": body}

    def sms(self) -> str:
        return (
            f"Hi {self.contact}, it's {self.your_name}. I made {self.business} a "
            f"free sample video ad - {self.sample_link}. Like it? I can do "
            f"{self.offer} for ${self.price}. Want more concepts?"
        )

    def walk_in_pitch(self) -> str:
        return (
            f"\"Hi, are you the owner? I'm {self.your_name} - I make short video "
            f"ads for {self.niche} businesses here in {self.city}. I actually "
            f"already made one for {self.business} to show you - mind if I show "
            f"you 15 seconds on my phone?\"\n"
            f"[show sample] \"If you like it, I can make you {self.offer} for "
            f"${self.price}. Want me to put a pack together?\""
        )

    def upwork_proposal(self) -> str:
        return (
            f"Hi {self.contact},\n\n"
            f"You need {self.offer} that actually convert - that's exactly what I "
            f"do. I produce UGC-style AI video ads fast (24-48h turnaround) so you "
            f"can test creatives without expensive shoots.\n\n"
            f"Here's a sample so you can judge the quality up front: {self.sample_link}\n"
            f"Portfolio: {self.portfolio}\n\n"
            f"I can start today. Happy to do a first batch so you can see the "
            f"results before scaling. When can we hop on a quick call? {self.calendar_link}\n\n"
            f"- {self.your_name}"
        )

    # ------------------------------------------------------------------ #
    # Follow-ups & objections
    # ------------------------------------------------------------------ #
    def follow_up_sequence(self) -> List[Dict[str, str]]:
        return [
            {
                "when": "Day 2 (no reply)",
                "message": (
                    f"Hey {self.contact}, did the sample video come through? "
                    f"Happy to tweak it to match {self.business}'s vibe - just say the word."
                ),
            },
            {
                "when": "Day 4 (no reply)",
                "message": (
                    f"No worries if now's not the time! Quick idea: I can send 2 "
                    f"more ad concepts for {self.business} so you've got options to "
                    f"test. Want them?"
                ),
            },
            {
                "when": "Day 7 (last touch)",
                "message": (
                    f"Last one from me 🙂 I'll hold a spot this week to make "
                    f"{self.business} {self.offer} for ${self.price}. Want me to "
                    f"grab it for you before it's gone?"
                ),
            },
        ]

    def objection_handlers(self) -> Dict[str, str]:
        return {
            "too expensive": (
                f"Totally fair - that's why I keep the first pack small. One ad "
                f"that lands pays for the whole batch. Want to start with 3 for less?"
            ),
            "we do it in-house": (
                f"Love that! I just speed things up - I can hand you ready-to-post "
                f"videos so your team skips the editing. Want a free one to test?"
            ),
            "not sure it works": (
                f"That's the point of the free sample - post it, watch the views, "
                f"then decide. Zero risk to you."
            ),
            "no time": (
                f"You don't need any - you don't film or edit anything. I deliver "
                f"finished videos ready to upload. Want me to just handle it?"
            ),
            "send info": (
                f"Sent! Short version: {self.offer} for ${self.price}, 48h "
                f"turnaround, free sample first: {self.sample_link}"
            ),
        }

    def generate_all(self) -> Dict[str, Any]:
        """Return the full outreach kit."""
        return {
            "instagram_dm": self.instagram_dm(),
            "cold_email": self.cold_email(),
            "sms": self.sms(),
            "walk_in_pitch": self.walk_in_pitch(),
            "upwork_proposal": self.upwork_proposal(),
            "follow_up_sequence": self.follow_up_sequence(),
            "objection_handlers": self.objection_handlers(),
            "outreach_targets_per_day": 25,
            "tip": (
                "Personalize the first line per business and ALWAYS attach a real "
                "sample. Sample-first outreach converts far better than a pitch."
            ),
        }


if __name__ == "__main__":
    brief = {
        "business": "Bella's Nail Bar",
        "contact_name": "Bella",
        "niche": "nail salon",
        "city": "Miami",
        "your_name": "Sam",
        "offer": "5 short-form video ads",
        "price": 300,
    }
    kit = OutreachGenerator(brief).generate_all()
    print(kit["instagram_dm"])
    print("\nEMAIL SUBJECT:", kit["cold_email"]["subject"])
