from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from planner_generator.planner_specs.models import BundleSpec, PageSpec, SectionSpec


@dataclass(frozen=True)
class LifestylePageTemplate:
    title: str
    subtitle: str
    page_type: str
    sections: List[SectionSpec]


def build_lifestyle_pages(bundle: BundleSpec, fallback_pages: Iterable[PageSpec]) -> List[PageSpec]:
    """Create abundant lifestyle-led page sets from a compact bundle strategy.

    Static page specs remain useful for reusable components, but Etsy bundles need
    a stronger product point of view than repeating a small template set. This
    generator turns a product positioning strategy into a full printable bundle.
    """
    strategy = str(bundle.metadata.get("bundle_strategy", "")).strip().lower()
    if strategy != "soft_life_reset":
        return list(fallback_pages)

    target_count = int(bundle.metadata.get("generated_page_count", 50))
    templates = _soft_life_reset_templates()
    pages: List[PageSpec] = []
    collection = str(bundle.metadata.get("collection", "soft_life_reset"))
    for index, template in enumerate(templates[:target_count], start=1):
        page_id = _slug(template.title)
        pages.append(
            PageSpec(
                id=f"{page_id}_{index:02d}",
                page_type=template.page_type,
                title=template.title,
                subtitle=template.subtitle,
                sections=template.sections,
                metadata={
                    "collection": collection,
                    "aesthetic": "soft_life_editorial",
                    "brand_visible": False,
                    "page_number": index,
                },
            )
        )
    return pages


def _soft_life_reset_templates() -> List[LifestylePageTemplate]:
    templates = [
        _monthly("Monthly Reset", "A gentle overview for intentions, dates, and little anchors."),
        _monthly("Soft Monthly Overview", "Map the month with space for calm focus and notes to self."),
        _monthly("Clean Girl Month", "Simple planning space for routines, reminders, and slow living."),
        _monthly("Monthly Reflection", "Look back softly before choosing what comes next."),
        _weekly("Sunday Reset", "A quiet weekly ritual for resetting your space, mind, and priorities."),
        _weekly("Soft Weekly Planner", "An airy weekly layout for gentle priorities and simple structure."),
        _weekly("Minimal Weekly Reset", "A calm planning page for the week ahead."),
        _weekly("Weekly Overview", "See the week at a glance without over-planning it."),
        _two_column("Vertical Weekly Layout", "Soft structure for plans, reminders, and open notes.", "Week rhythm", "Notes to self"),
        _two_column("Horizontal Weekly Layout", "A spacious weekly spread for calm scheduling.", "Plans", "Gentle priorities"),
        _daily("Daily Reset", "A beautiful place to choose the tone of the day."),
        _daily("Soft Daily Planner", "Simple daily planning with breathing room."),
        _daily("Calm Focus Page", "A softer way to hold focus, tasks, and reminders."),
        _daily("Morning Intention", "Start the day with intention, softness, and clarity."),
        _daily("Evening Wind Down", "Close the day with reflection and little wins."),
        _notes("Things On My Mind", "A gentle page for clearing mental clutter."),
        _notes("Brain Dump", "Let everything land somewhere soft."),
        _notes("Notes To Self", "Open space for thoughts, reminders, and tender ideas."),
        _notes("Quiet Notes", "A clean lined page for slow thoughts."),
        _notes("Open Space", "Minimal writing space for whatever needs somewhere to go."),
        _checkbox("Tiny Wins", "Notice the small things that are quietly working.", ["A small win", "A kind choice", "Something finished", "Something released", "Something enjoyed", "Tomorrow's tiny step"]),
        _checkbox("Gentle Priorities", "Choose what matters without making the day heavy.", ["Most important", "Nice to do", "Can wait", "For me", "For home", "For later"]),
        _checkbox("Reset Routine", "A soft checklist for returning to yourself.", ["Clear a surface", "Refill water", "Light stretch", "Inbox glance", "Plan tomorrow", "Early night"]),
        _checkbox("Self-Care Menu", "Choose care that feels possible today.", ["Fresh air", "Slow shower", "Tidy corner", "Journal page", "Comfort meal", "Screen pause"]),
        _checkbox("Little Home Reset", "Small homemaking notes for a calmer space.", ["Kitchen reset", "Laundry touchpoint", "Floors", "Fresh sheets", "Trash out", "Flowers or candle"]),
        _tracker("Monthly Habit Tracker", "Track rituals softly, without perfection."),
        _tracker("Tiny Habits Tracker", "A calm grid for small repeatable rituals."),
        _tracker("Self-Care Tracker", "Notice care, rest, movement, and nourishment."),
        _tracker("Wellness Tracker", "A gentle month of tending to yourself."),
        _tracker("Mood + Energy Tracker", "Observe your rhythm with softness."),
        _prompt("Currently Loving", "A little lifestyle snapshot of what feels good right now.", "Currently loving..."),
        _prompt("Slow Living List", "Make room for simple pleasures and unhurried moments.", "This season, I want to make more space for..."),
        _prompt("Monthly Intentions", "Choose an emotional direction for the month.", "This month, I want to feel..."),
        _prompt("Soft Goals", "Hold goals with ease instead of pressure.", "A gentle goal I am growing toward..."),
        _prompt("Future Me Notes", "Write a kind note to the version of you who keeps going.", "Dear future me..."),
        _quadrant("Life Admin", "A calm place for the small things that keep life moving.", ["home", "money", "appointments", "errands"]),
        _quadrant("Soft Productivity", "Organize tasks without turning the page into a dashboard.", ["today", "this week", "waiting on", "later"]),
        _quadrant("Clean Girl Reset", "A light reset board for body, space, mind, and calendar.", ["body", "space", "mind", "calendar"]),
        _quadrant("Cozy Productivity", "Soft structure for getting things done kindly.", ["focus", "comfort", "must do", "could do"]),
        _meal("Soft Meal Plan", "Simple meals, grocery notes, and nourishing ideas."),
        _meal("Weekly Meals", "A minimal meal planning page that still feels pretty."),
        _meal("Nourish List", "Plan meals, snacks, and cozy staples."),
        _budget("Money Notes", "A softer money page for mindful spending notes."),
        _budget("Spending Snapshot", "Simple money awareness without spreadsheet energy."),
        _budget("Little Budget Reset", "A gentle check-in for bills, needs, and nice-to-haves."),
        _rating("Monthly Check-In", "A reflective page for noticing how life feels right now."),
        _rating("Wellness Check-In", "A calm scan of energy, rest, movement, and mood."),
        _rating("Soft Life Audit", "Notice what feels heavy, light, aligned, and ready to change."),
        _notes("Ideas + Inspirations", "A pretty page for plans, dreams, and saved ideas."),
        _notes("Blank Lined Notes", "Elegant open writing space for anything you need."),
    ]
    return templates


def _section(section_id: str, section_type: str, title: str, weight: float, **fields: object) -> SectionSpec:
    return SectionSpec(id=section_id, type=section_type, title=title, weight=weight, fields=dict(fields))


def _monthly(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(
        title,
        subtitle,
        "monthly",
        [
            _section("calendar", "calendar_grid", "month at a glance", 2.1, weeks=5),
            _section("intentions", "prompt_box", "intentions", 0.9, prompt="I want this month to feel...", line_count=3),
            _section("notes", "two_column", "little anchors", 1.0, left_title="gentle priorities", right_title="notes to self", line_count=5),
        ],
    )


def _weekly(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(
        title,
        subtitle,
        "weekly",
        [
            _section("reset", "checkbox_list", "this week's reset", 0.8, items=["clear space", "choose focus", "plan meals", "check calendar", "make time for rest"]),
            _section("week", "two_column", "soft structure", 1.7, left_title="gentle priorities", right_title="small reminders", line_count=8),
            _section("reflection", "prompt_box", "weekly reflection", 0.8, prompt="What would make this week feel lighter?", line_count=4),
        ],
    )


def _daily(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(
        title,
        subtitle,
        "daily",
        [
            _section("intention", "prompt_box", "today's intention", 0.7, prompt="Today I want to feel...", line_count=3),
            _section("flow", "two_column", "plans + notes", 1.8, left_title="gentle priorities", right_title="notes to self", line_count=9),
            _section("close", "checkbox_list", "close the day", 0.8, items=["tiny win", "something released", "tomorrow's first step"]),
        ],
    )


def _notes(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(title, subtitle, "notes", [_section("notes", "notes_box", "open notes", 1.0, line_count=18)])


def _checkbox(title: str, subtitle: str, items: List[str]) -> LifestylePageTemplate:
    return LifestylePageTemplate(title, subtitle, "checklist", [_section("list", "checkbox_list", "soft checklist", 1.0, items=items)])


def _tracker(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(
        title,
        subtitle,
        "tracker",
        [
            _section("tracker", "tracker_grid", "monthly rhythm", 1.7, rows=8, columns=14),
            _section("notes", "prompt_box", "notes", 0.6, prompt="What am I noticing?", line_count=3),
        ],
    )


def _prompt(title: str, subtitle: str, prompt: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(title, subtitle, "journal", [_section("prompt", "prompt_box", "journal prompt", 1.0, prompt=prompt, line_count=14)])


def _quadrant(title: str, subtitle: str, labels: List[str]) -> LifestylePageTemplate:
    return LifestylePageTemplate(title, subtitle, "board", [_section("board", "quadrant_board", "soft board", 1.0, labels=labels)])


def _meal(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(
        title,
        subtitle,
        "meal_planner",
        [
            _section("meals", "two_column", "nourish", 1.5, left_title="simple meals", right_title="grocery notes", line_count=8),
            _section("comforts", "checkbox_list", "little staples", 0.7, items=["breakfast", "lunch", "dinner", "snacks", "prep one thing"]),
        ],
    )


def _budget(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(
        title,
        subtitle,
        "money",
        [
            _section("notes", "prompt_box", "money intention", 0.6, prompt="This month I want my spending to feel...", line_count=3),
            _section("rows", "amount_rows", "mindful money notes", 1.4, rows=8, label_title="note", amount_title="amount", total_title="paid"),
        ],
    )


def _rating(title: str, subtitle: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(
        title,
        subtitle,
        "reflection",
        [
            _section("scales", "rating_scale", "how it feels", 0.9, labels=["energy", "ease", "rest", "focus", "joy"], steps=5),
            _section("notes", "prompt_box", "notes to self", 1.1, prompt="What do I want more of?", line_count=7),
        ],
    )


def _two_column(title: str, subtitle: str, left: str, right: str) -> LifestylePageTemplate:
    return LifestylePageTemplate(title, subtitle, "weekly", [_section("columns", "two_column", "weekly space", 1.0, left_title=left, right_title=right, line_count=14)])


def _slug(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "_" for char in value]
    return "_".join("".join(chars).split("_")).strip("_")
