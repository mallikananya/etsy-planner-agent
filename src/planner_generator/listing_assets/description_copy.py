from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Sequence

from planner_generator.listing_assets.constraints import ETSY_DESCRIPTION_MAX_LENGTH, truncate_text
from planner_generator.market_intelligence.models import DifferentiationBrief, NicheBrief, ProductConcept
from planner_generator.planner_specs.models import BundleSpec
from planner_generator.theme_engine.models import Theme


@dataclass(frozen=True)
class DescriptionSection:
    key: str
    heading: str
    lines: List[str]

    def to_dict(self) -> Dict[str, object]:
        return {"key": self.key, "heading": self.heading, "lines": self.lines}


@dataclass(frozen=True)
class DescriptionCopy:
    text: str
    sections: List[DescriptionSection]
    brand_voice: str
    seo_keywords_used: List[str]


@dataclass(frozen=True)
class _Voice:
    name: str
    identity: str
    emotional_desire: str
    daily_shift: str
    signature_benefits: List[str]


def generate_listing_description(
    bundle: BundleSpec,
    theme: Theme,
    market_brief: NicheBrief | None = None,
    product_concept: ProductConcept | None = None,
    differentiation: DifferentiationBrief | None = None,
    objection_coverage: Dict[str, object] | None = None,
) -> DescriptionCopy:
    """Generate long-form Etsy description copy using a dedicated sales-page structure."""

    context = _DescriptionContext(bundle, theme, market_brief, product_concept, differentiation, objection_coverage or {})
    voice = _select_voice(context)
    sections = [
        _opening_hook(context, voice),
        _transformation_benefits(context, voice),
        _helps_you(context, voice),
        _key_features(context),
        _what_you_receive(context),
        _important_notes(context),
    ]
    text = "\n\n".join(_render_section(section, show_heading=index > 0) for index, section in enumerate(sections))
    return DescriptionCopy(
        text=truncate_text(text.strip(), ETSY_DESCRIPTION_MAX_LENGTH),
        sections=sections,
        brand_voice=voice.name,
        seo_keywords_used=_seo_keywords(context),
    )


class _DescriptionContext:
    def __init__(
        self,
        bundle: BundleSpec,
        theme: Theme,
        market_brief: NicheBrief | None,
        product_concept: ProductConcept | None,
        differentiation: DifferentiationBrief | None,
        objection_coverage: Dict[str, object],
    ) -> None:
        self.bundle = bundle
        self.theme = theme
        self.market_brief = market_brief
        self.product_concept = product_concept
        self.differentiation = differentiation
        self.objection_coverage = objection_coverage

    @property
    def product_name(self) -> str:
        if self.product_concept and self.product_concept.product_name:
            return _clean_product_name(self.product_concept.product_name, self.bundle.name)
        return _clean_product_name(self.bundle.name, self.bundle.name)

    @property
    def page_count(self) -> int:
        return int(self.bundle.metadata.get("page_count") or len(self.included_pages) or 0)

    @property
    def included_pages(self) -> List[str]:
        if self.product_concept and self.product_concept.included_page_titles:
            return _unique(self.product_concept.included_page_titles)
        return _unique([str(page) for page in self.bundle.metadata.get("included_pages", [])])

    @property
    def paper_sizes(self) -> List[str]:
        return [size.upper() if size.lower() == "a4" else "US Letter" for size in self.bundle.paper_sizes]

    @property
    def audience(self) -> str:
        if self.product_concept and self.product_concept.buyer_persona:
            return self.product_concept.buyer_persona
        if self.market_brief and self.market_brief.audience:
            return self.market_brief.audience
        return "women who want calm structure without making life feel rigid"

    @property
    def niche_text(self) -> str:
        parts = [
            self.product_name,
            self.bundle.name,
            self.bundle.description,
            self.market_brief.name if self.market_brief else "",
            self.market_brief.angle if self.market_brief else "",
            self.product_concept.promise if self.product_concept else "",
            " ".join(self.market_brief.primary_keywords if self.market_brief else []),
            " ".join(self.market_brief.long_tail_keywords if self.market_brief else []),
            " ".join(self.product_concept.page_strategy if self.product_concept else []),
        ]
        return " ".join(parts).lower()


def _opening_hook(context: _DescriptionContext, voice: _Voice) -> DescriptionSection:
    lines = [
        f"Create a planning ritual that feels like the life you are becoming.",
        (
            f"This {context.product_name} is designed for {voice.identity}: the version of you who wants "
            f"{voice.emotional_desire}, not another overwhelming stack of tasks."
        ),
        (
            "It is calm, elevated, and practical enough to use on an ordinary Tuesday, with pages that help you "
            "romanticize your routines while still giving your week real structure."
        ),
    ]
    return DescriptionSection("emotional_opening_hook", "Emotional Opening Hook", lines)


def _transformation_benefits(context: _DescriptionContext, voice: _Voice) -> DescriptionSection:
    keyword_phrase = _natural_keyword_phrase(context)
    lines = [
        (
            f"Instead of planning from pressure, this {keyword_phrase} helps you move through your days with "
            f"{voice.daily_shift}."
        ),
        (
            "Use it to gather the loose pieces of your life, choose what matters first, create softer routines, "
            "and return to your goals without the heavy feeling of starting over."
        ),
        _differentiation_sentence(context),
    ]
    return DescriptionSection("transformation_benefits", "Transformation Benefits", lines)


def _helps_you(context: _DescriptionContext, voice: _Voice) -> DescriptionSection:
    benefits = _unique(
        voice.signature_benefits
        + [
            "Create intentional routines that feel supportive",
            "Reduce overwhelm with gentle structure",
            "Stay aligned with your goals without chasing perfection",
            "Romanticize your daily planning ritual",
            "Build calm consistency around the life you want",
        ]
    )[:7]
    return DescriptionSection("helps_you", "This planner helps you", [f"- {benefit}" for benefit in benefits])


def _key_features(context: _DescriptionContext) -> DescriptionSection:
    features = _unique(
        _feature_lines_for_niche(context)
        + [
            f"{context.page_count} planner pages" if context.page_count else "Planner page collection",
            "Daily, weekly, routine, reflection, wellness, and notes-style layouts",
            "Goal planning, habit tracking, self-care, and reset pages",
            "Complete printable PDFs plus individual page PDFs",
            "US Letter and A4 formats",
            "PDF files that can be imported into common note-taking apps",
            "Instant digital download through Etsy after purchase",
        ]
    )
    return DescriptionSection("key_features", "Key Features", [f"- {feature}" for feature in features[:10]])


def _what_you_receive(context: _DescriptionContext) -> DescriptionSection:
    included = [
        f"Complete {size} PDF" for size in context.paper_sizes
    ] + [
        "Individual page PDFs for flexible printing",
        "A customer ZIP with the primary planner files",
        "Reusable pages you can print again for personal use",
        "A polished neutral design system with warm editorial styling",
    ]
    if context.page_count:
        included.insert(0, f"{context.page_count} total planner pages")
    if context.included_pages:
        included.append("Included page categories: " + ", ".join(context.included_pages[:10]))
    return DescriptionSection("what_you_receive", "What You Receive", [f"- {item}" for item in included])


def _important_notes(context: _DescriptionContext) -> DescriptionSection:
    lines = [
        "- This is a digital product. No physical planner will be shipped.",
        "- Files are delivered through Etsy after purchase.",
        "- This is a printable PDF planner, not an editable Canva, Word, or spreadsheet template.",
        "- PDF files may be imported into common annotation apps for digital handwriting; app compatibility can vary by device.",
        "- Print colors may vary slightly depending on your monitor, printer, paper, and ink settings.",
        "- For best results, print at actual size / 100% scale unless your printer requires fit-to-page.",
        "- Personal use only. Please do not resell, redistribute, share, or claim the files as your own.",
        "- Because this is an instant digital download, refunds and exchanges may be limited once files are accessed, unless required by Etsy policy or local law.",
    ]
    return DescriptionSection("important_notes", "Important Notes", lines)


def _select_voice(context: _DescriptionContext) -> _Voice:
    text = context.niche_text
    if _has(text, ["corporate", "career", "work", "deadline", "professional"]):
        return _Voice(
            name="polished_work_reset",
            identity="the ambitious woman who wants her work week to feel composed instead of consuming",
            emotional_desire="clear priorities, protected energy, and a softer reset after busy days",
            daily_shift="more clarity, cleaner boundaries, and a quiet sense of control over the work week",
            signature_benefits=[
                "Reset your work week without carrying every task in your head",
                "Create calm boundaries between ambition, rest, and everyday life",
                "Turn scattered priorities into a focused weekly rhythm",
            ],
        )
    if _has(text, ["burnout", "recovery", "self care", "wellness", "nervous", "energy", "mental"]):
        return _Voice(
            name="soft_wellness_recovery",
            identity="the woman rebuilding her routines with tenderness, clarity, and self-trust",
            emotional_desire="more calm, more energy awareness, and habits that support her instead of punish her",
            daily_shift="gentle momentum, emotional steadiness, and permission to plan at a human pace",
            signature_benefits=[
                "Protect your energy with softer check-ins",
                "Build wellness routines without all-or-nothing pressure",
                "Make room for reflection, rest, and realistic consistency",
            ],
        )
    if _has(text, ["budget", "money", "finance", "savings", "payday"]):
        return _Voice(
            name="calm_money_clarity",
            identity="the woman who wants her money to feel clear, intentional, and less emotionally loaded",
            emotional_desire="a calmer relationship with money and a simple rhythm for making the next right decision",
            daily_shift="more visibility, less avoidance, and steady confidence around everyday finances",
            signature_benefits=[
                "See your money clearly without making budgeting feel harsh",
                "Create gentle check-ins around spending, saving, and priorities",
                "Turn financial overwhelm into small next steps",
            ],
        )
    if _has(text, ["student", "study", "academic", "school", "assignment"]):
        return _Voice(
            name="elevated_student_focus",
            identity="the student who wants her semester to feel organized, focused, and beautifully manageable",
            emotional_desire="less last-minute stress and more confidence moving through deadlines",
            daily_shift="cleaner focus, visible priorities, and a steadier study rhythm",
            signature_benefits=[
                "Organize deadlines before they become urgent",
                "Create study routines that feel clear and repeatable",
                "Hold school, life, and rest in one calm planning system",
            ],
        )
    if _has(text, ["adhd", "brain dump", "focus", "executive"]):
        return _Voice(
            name="gentle_focus_support",
            identity="the woman who needs structure that lowers friction instead of demanding perfection",
            emotional_desire="a softer way to capture tasks, choose next steps, and return to focus",
            daily_shift="less mental clutter, more visible choices, and a realistic path back into motion",
            signature_benefits=[
                "Move tasks out of your head and into a calmer system",
                "Create tiny next steps when everything feels equally loud",
                "Use structure that supports attention without shame",
            ],
        )
    return _Voice(
        name="soft_life_editorial",
        identity="the woman creating more intention, beauty, and steadiness in her everyday routines",
        emotional_desire="a softer life with practical structure and rituals that feel like self-respect",
        daily_shift="more calm, more clarity, and a planning rhythm that feels easy to return to",
        signature_benefits=[
            "Create a softer rhythm for your week",
            "Make planning feel beautiful, grounded, and easy to begin",
            "Bring your goals, routines, and self-care into one calm place",
        ],
    )


def _feature_lines_for_niche(context: _DescriptionContext) -> List[str]:
    text = context.niche_text
    lines: List[str] = []
    if _has(text, ["corporate", "career", "work"]):
        lines.extend(["Work week reset pages", "Priority planning and routine support", "Brain dump space for mental offloading"])
    if _has(text, ["burnout", "wellness", "self care", "nervous", "energy"]):
        lines.extend(["Wellness check-ins and self-care prompts", "Mood, energy, and reflection pages", "Gentle reset layouts"])
    if _has(text, ["budget", "money", "finance", "payday"]):
        lines.extend(["Budget and payday planning pages", "Money clarity check-ins", "Goal and savings planning support"])
    if _has(text, ["student", "study", "academic", "school"]):
        lines.extend(["Assignment and deadline planning", "Study routine support", "Monthly and weekly overview pages"])
    if _has(text, ["adhd", "brain dump", "focus"]):
        lines.extend(["Brain dump and task capture pages", "Simple next-step planning", "Low-friction focus support"])
    return lines


def _natural_keyword_phrase(context: _DescriptionContext) -> str:
    keywords = _seo_keywords(context)
    if keywords:
        phrase = keywords[0]
        if "planner" not in phrase.lower():
            phrase = f"{phrase} planner"
        return phrase
    return "printable planner"


def _seo_keywords(context: _DescriptionContext) -> List[str]:
    if not context.market_brief:
        return _clean_keywords([str(tag) for tag in context.bundle.metadata.get("tags", [])])[:5]
    values = context.market_brief.primary_keywords + context.market_brief.long_tail_keywords + context.market_brief.seo_tags
    return _clean_keywords(values)[:8]


def _differentiation_sentence(context: _DescriptionContext) -> str:
    if context.differentiation and context.differentiation.differentiators:
        clean = context.differentiation.differentiators[0].rstrip(".")
        return f"What makes it feel different: {clean.lower()}."
    return "The result is a planning system that feels abundant and premium without becoming cluttered, cold, or difficult to use."


def _render_section(section: DescriptionSection, show_heading: bool) -> str:
    body = "\n".join(section.lines)
    if not show_heading:
        return body
    return f"{section.heading}\n{body}"


def _clean_product_name(value: str, fallback: str) -> str:
    source = fallback if "," in value or " pdf" in value.lower() or " instant download" in value.lower() else value
    replacements = [
        " printable",
        " planner pdf",
        " pdf",
        " instant download",
        " digital download",
        " daily weekly",
        " habit tracker",
        " self care planner",
    ]
    cleaned = source
    for phrase in replacements:
        cleaned = cleaned.replace(phrase.title(), "").replace(phrase.upper(), "").replace(phrase, "")
    cleaned = cleaned.replace(",", " ")
    words = [word for word in cleaned.split() if word.lower() not in {"printable", "download", "instant"}]
    cleaned = " ".join(words).strip()
    return cleaned or fallback


def _clean_keywords(values: Sequence[str]) -> List[str]:
    keywords: List[str] = []
    for value in values:
        cleaned = " ".join(str(value).replace(",", " ").split()).strip().lower()
        if not cleaned or len(cleaned) > 42:
            continue
        if any(skip in cleaned for skip in ["instant download", "daily weekly planner pdf"]):
            continue
        keywords.append(cleaned)
    return _unique(keywords)


def _has(text: str, terms: Sequence[str]) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower())
    tokens = set(normalized.split())
    for term in terms:
        phrase = re.sub(r"[^a-z0-9]+", " ", term.lower()).strip()
        if not phrase:
            continue
        if " " in phrase and phrase in normalized:
            return True
        if phrase in tokens:
            return True
    return False


def _unique(values: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = " ".join(str(value).strip().split())
        key = normalized.lower()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result
