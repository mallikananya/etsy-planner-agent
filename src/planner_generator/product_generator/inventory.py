from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from planner_generator.planner_specs.models import BundleSpec, PageSpec, SectionSpec


@dataclass(frozen=True)
class PageInventoryItem:
    page: PageSpec
    category: str
    purpose: str
    emotional_role: str
    differentiation: str


@dataclass(frozen=True)
class ProductInventory:
    product_name: str
    audience: str
    items: List[PageInventoryItem]

    @property
    def pages(self) -> List[PageSpec]:
        return [item.page for item in self.items]

    def to_manifest(self) -> Dict[str, object]:
        categories: Dict[str, List[str]] = {}
        for item in self.items:
            categories.setdefault(item.category, []).append(item.page.id)
        return {
            "product_name": self.product_name,
            "audience": self.audience,
            "page_count": len(self.items),
            "categories": categories,
            "pages": [
                {
                    "id": item.page.id,
                    "title": item.page.title,
                    "page_type": item.page.page_type,
                    "category": item.category,
                    "purpose": item.purpose,
                    "emotional_role": item.emotional_role,
                    "differentiation": item.differentiation,
                }
                for item in self.items
            ],
        }


def build_soft_life_inventory(bundle: BundleSpec) -> ProductInventory:
    product_name = "Soft Life Wellness Planner"
    items: List[PageInventoryItem] = []

    def add(
        page_id: str,
        page_type: str,
        title: str,
        subtitle: str,
        category: str,
        purpose: str,
        emotional_role: str,
        differentiation: str,
        sections: List[SectionSpec],
        role: str = "",
    ) -> None:
        metadata = {
            "product_collection": "soft_life_wellness_planner",
            "page_role": role or page_type,
            "category": category,
            "purpose": purpose,
            "emotional_role": emotional_role,
            "differentiation": differentiation,
        }
        items.append(
            PageInventoryItem(
                page=PageSpec(page_id, page_type, title, subtitle, sections, metadata),
                category=category,
                purpose=purpose,
                emotional_role=emotional_role,
                differentiation=differentiation,
            )
        )

    add(
        "soft_life_cover",
        "cover",
        product_name,
        "A calm planning system for wellness, routines, reflection, and softer productivity.",
        "front matter",
        "Sets the premium stationery tone before the functional pages begin.",
        "aspirational entry point",
        "Full-bleed editorial cover, not a worksheet.",
        [_prompt("cover_note", "Opening Note", "This planner belongs to:", 2, 1.0)],
        "cover",
    )
    add(
        "planner_index",
        "planner_index",
        "Planner Index",
        "A simple map of what each section is for and when to use it.",
        "front matter",
        "Helps the buyer understand the planner as a curated system.",
        "orientation and confidence",
        "Groups pages by emotional job instead of listing templates.",
        [
            _list("start_here", "Start Here", ["Yearly and seasonal pages", "Monthly direction", "Weekly reset rhythm", "Daily ritual pages", "Wellness tracking and notes"], 1.1),
            _two("section_map", "Section Map", "Planning", "Wellness", 6, 1.3),
        ],
        "planner_index",
    )
    add(
        "gentle_planning_ritual",
        "guide",
        "Gentle Planning Ritual",
        "A low-pressure way to use the planner without turning wellness into another chore.",
        "front matter",
        "Shows how to return to the planner repeatedly.",
        "permission and ease",
        "Frames planning as care, not performance.",
        [
            _prompt("ritual", "Before You Plan", "What would make this season feel lighter?", 4, 1.0),
            _list("simple_flow", "Simple Flow", ["Choose a focus", "Name what needs care", "Plan the smallest useful step", "Review without judgment"], 1.0),
            _notes("personal_rules", "My Planning Rules", 5, 1.0),
        ],
        "guide",
    )
    add(
        "yearly_compass",
        "yearly_planner",
        "Yearly Compass",
        "An expansive page for the themes, values, and rhythms you want to return to.",
        "yearly planning",
        "Creates big-picture direction without overplanning the year.",
        "spacious intention",
        "Uses open reflection zones instead of a dense annual worksheet.",
        [
            _prompt("year_theme", "Theme Of The Year", "The feeling I am moving toward:", 4, 0.9),
            _quad("life_areas", "Life Areas", ["Body", "Home", "Work", "Relationships"], 4, 1.5),
            _two("anchors", "Anchors", "Keep Close", "Release", 5, 1.0),
        ],
        "yearly",
    )
    add(
        "seasonal_intentions",
        "seasonal_planner",
        "Seasonal Intentions",
        "A softer seasonal reset for priorities, energy, care, and home rhythms.",
        "seasonal planning",
        "Turns the big yearly vision into a near-term season.",
        "renewal",
        "Balances emotional check-in with useful planning structure.",
        [
            _quad("season_map", "This Season", ["Nourish", "Simplify", "Practice", "Protect"], 4, 1.4),
            _tracker("season_habits", "Gentle Habit Markers", 4, 7, 0.9),
            _prompt("season_note", "Season Note", "What deserves more room this season?", 4, 0.8),
        ],
        "seasonal",
    )
    add_divider(add, "monthly_divider", "Monthly Planning", "Choose direction before filling the calendar.", "monthly planning", "directional reset")
    for number in range(1, 4):
        suffix = f"{number:02d}"
        add(
            f"monthly_overview_{suffix}",
            "monthly_planner",
            f"Month {number} Overview",
            "Key dates, priorities, and the tone you want the month to hold.",
            "monthly planning",
            "Gives each month a directional center.",
            "clarity",
            "Combines calendar structure with reflective focus.",
            [
                _calendar(f"calendar_{suffix}", "Month At A Glance", 5, 1.5),
                _two(f"focus_{suffix}", "Focus + Care", "Priorities", "Care Anchors", 5, 0.9),
                _prompt(f"note_{suffix}", "Month Note", "What would make this month feel well-held?", 4, 0.7),
            ],
            "monthly",
        )
        add(
            f"monthly_ritual_map_{suffix}",
            "monthly_planner",
            f"Month {number} Ritual Map",
            "A monthly view of routines, reset days, and small moments of care.",
            "monthly planning",
            "Makes routines visible before the weeks get busy.",
            "steady rhythm",
            "Separates rituals from tasks so the page feels calmer.",
            [
                _tracker(f"ritual_grid_{suffix}", "Ritual Rhythm", 6, 7, 1.25),
                _quad(f"monthly_support_{suffix}", "Support Map", ["Morning", "Evening", "Home", "Body"], 3, 1.0),
                _list(f"anchors_{suffix}", "Non-Negotiable Anchors", ["Rest", "Movement", "Food", "Connection", "Quiet"], 0.8),
            ],
            "monthly",
        )
        add(
            f"monthly_reflection_{suffix}",
            "monthly_reflection",
            f"Month {number} Reflection",
            "Close the month gently and notice what supported your wellbeing.",
            "monthly planning",
            "Creates closure before moving into another month.",
            "soft completion",
            "Reflection-first composition with fewer boxes and more writing room.",
            [
                _prompt(f"felt_good_{suffix}", "What Felt Good", "Moments, choices, or support I want to remember:", 5, 1.1),
                _two(f"learned_{suffix}", "Notice + Adjust", "Keep", "Change", 5, 1.0),
                _prompt(f"next_month_{suffix}", "Carry Forward", "One gentle adjustment for next month:", 3, 0.6),
            ],
            "reflection",
        )

    add_divider(add, "weekly_divider", "Weekly Reset", "Ground the week before it asks too much of you.", "weekly planning", "grounded rhythm")
    for week in range(1, 7):
        add_week(add, week)

    add_divider(add, "daily_divider", "Daily Rituals", "Small plans for real days, not perfect days.", "daily planning", "intimate care")
    for day in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Weekend"]:
        add_daily(add, day)

    add_divider(add, "wellness_divider", "Wellness Library", "Track patterns, choose care, and leave room for notes.", "wellness support", "calm support")
    add_wellness_pages(add)

    return ProductInventory(product_name=product_name, audience=bundle.description, items=items)


def add_divider(add, page_id: str, title: str, subtitle: str, category: str, emotional_role: str) -> None:
    add(
        page_id,
        "section_divider",
        title,
        subtitle,
        category,
        "Creates a visual pause and marks a new planning mode.",
        emotional_role,
        "Section divider creates rhythm in the raw PDF.",
        [_prompt(f"{page_id}_note", "Section Intention", "Before this section, I want to remember:", 3, 1.0)],
        "section_divider",
    )


def add_week(add, week: int) -> None:
    suffix = f"{week:02d}"
    add(
        f"week_{suffix}_wellness_map",
        "weekly_planner",
        f"Week {week} Wellness Map",
        "Priorities, appointments, care anchors, and enough room to adapt.",
        "weekly planning",
        "Sets the weekly direction in one grounded view.",
        "grounded planning",
        "Balances calendar thinking with care and energy.",
        [
            _list(f"priorities_{suffix}", "Top Priorities", ["", "", "", ""], 0.8),
            _two(f"plans_{suffix}", "Plans + Care", "Plans", "Care", 7, 1.25),
            _tracker(f"habits_{suffix}", "Habit Rhythm", 5, 7, 0.95),
        ],
        "weekly",
    )
    add(
        f"week_{suffix}_soft_productivity",
        "weekly_planner",
        f"Week {week} Soft Productivity",
        "A softer task page for focus, energy, and realistic next steps.",
        "weekly planning",
        "Supports productivity without harsh urgency.",
        "capacity-aware action",
        "Tasks are sorted by energy and importance instead of a long flat list.",
        [
            _quad(f"capacity_{suffix}", "Capacity Board", ["Must", "Can Wait", "Ask For Help", "Let Go"], 4, 1.4),
            _prompt(f"first_step_{suffix}", "First Gentle Step", "The smallest step that would create movement:", 4, 0.7),
            _notes(f"notes_{suffix}", "Loose Ends", 5, 0.8),
        ],
        "weekly",
    )
    add(
        f"week_{suffix}_nourishment",
        "weekly_planner",
        f"Week {week} Nourishment",
        "Meals, movement, grocery notes, and restorative plans without pressure.",
        "weekly planning",
        "Keeps wellness practical and repeatable.",
        "nourishment",
        "Combines meal planning and movement as supportive choices.",
        [
            _two(f"meals_{suffix}", "Simple Meals", "Breakfast / Lunch", "Dinner / Snacks", 7, 1.15),
            _list(f"movement_{suffix}", "Movement Menu", ["Walk", "Stretch", "Strength", "Yoga", "Rest", "Fresh air"], 0.8),
            _notes(f"grocery_{suffix}", "Tiny Grocery List", 7, 0.95),
        ],
        "weekly",
    )
    add(
        f"week_{suffix}_reflection",
        "weekly_reflection",
        f"Week {week} Reflection",
        "Notice what worked, what softened, and what needs a lighter plan.",
        "weekly planning",
        "Gives the week a calm closing ritual.",
        "gentle review",
        "Reflection page has more whitespace and fewer structural demands.",
        [
            _prompt(f"complete_{suffix}", "What Felt Complete", "Wins, relief, progress, or quiet moments:", 5, 1.0),
            _prompt(f"support_{suffix}", "What Supported Me", "Choices, people, routines, or boundaries that helped:", 5, 1.0),
            _two(f"carry_{suffix}", "Carry Forward", "Keep", "Soften", 4, 0.8),
        ],
        "reflection",
    )


def add_daily(add, day: str) -> None:
    page_id = f"daily_{day.lower()}"
    add(
        page_id,
        "daily_planner",
        f"{day} Daily Ritual",
        "An intimate daily page for focus, care, and a realistic plan.",
        "daily planning",
        "Makes each day feel intentional without overloading it.",
        "intimacy",
        "Daily pages use a lighter journal rhythm and fewer hard boxes.",
        [
            _prompt(f"{page_id}_intention", "Today's Intention", "How do I want to move through today?", 3, 0.65),
            _rating(f"{page_id}_checkin", "Morning Check-In", ["Energy", "Mood", "Focus", "Ease"], 5, 0.75),
            _two(f"{page_id}_plan", "Plan", "Schedule", "Tiny Tasks", 8, 1.3),
            _list(f"{page_id}_care", "Care Anchors", ["Water", "Meal", "Movement", "Pause"], 0.65),
            _prompt(f"{page_id}_close", "Evening Note", "What can I release tonight?", 3, 0.65),
        ],
        "daily",
    )


def add_wellness_pages(add) -> None:
    add(
        "mood_energy_patterns",
        "tracker",
        "Mood + Energy Patterns",
        "A weekly check-in for noticing patterns without judging them.",
        "wellness support",
        "Supports emotional awareness and nervous-system care.",
        "self-understanding",
        "Tracker includes reflection prompts so it does not feel clinical.",
        [
            _rating("energy_rating", "Daily Rating", ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], 5, 1.0),
            _tracker("pattern_grid", "Pattern Notes", 6, 7, 1.1),
            _prompt("helped", "What Helped", "Which choices made life feel lighter this week?", 5, 0.9),
        ],
        "tracker",
    )
    add(
        "habit_garden",
        "habit_tracker",
        "Habit Garden",
        "A soft habit tracker for care practices, routines, and gentle momentum.",
        "wellness support",
        "Makes habits feel seasonal and supportive.",
        "gentle consistency",
        "Tracker language is intentionally softer than a performance grid.",
        [
            _tracker("habit_grid", "Care Practices", 8, 14, 1.55),
            _two("habit_notes", "Notes", "Working", "Needs Ease", 5, 0.85),
        ],
        "tracker",
    )
    add(
        "self_care_menu",
        "reference",
        "Self-Care Menu",
        "Choose care that fits the day instead of forcing a perfect routine.",
        "wellness support",
        "A reusable reference page for low-energy and high-energy care.",
        "choice and permission",
        "Care is organized by capacity so it is actually usable.",
        [
            _list("quick_care", "Five-Minute Care", ["Drink water", "Open a window", "Stretch neck", "Write one line", "Take five breaths"], 0.9),
            _list("deeper_care", "Deeper Care", ["Long walk", "Warm shower", "Cook slowly", "Call someone kind", "Early bedtime"], 0.9),
            _two("personal_menu", "My Menu", "When I Have Energy", "When I Need Ease", 6, 1.1),
        ],
        "reference",
    )
    add(
        "lined_notes",
        "notes",
        "Notes",
        "Open space for ideas, lists, loose ends, and quiet reflection.",
        "notes",
        "Gives the buyer breathing room beyond structured pages.",
        "spaciousness",
        "A premium lined notes page closes the planner calmly.",
        [_notes("notes", "Notes", 24, 1.0)],
        "notes",
    )


def _prompt(section_id: str, title: str, prompt: str, lines: int, weight: float) -> SectionSpec:
    return SectionSpec(section_id, "prompt_box", title, weight, {"prompt": prompt, "line_count": lines})


def _notes(section_id: str, title: str, lines: int, weight: float) -> SectionSpec:
    return SectionSpec(section_id, "notes_box", title, weight, {"line_count": lines})


def _list(section_id: str, title: str, items: List[str], weight: float) -> SectionSpec:
    return SectionSpec(section_id, "checkbox_list", title, weight, {"items": items, "count": len(items)})


def _two(section_id: str, title: str, left: str, right: str, lines: int, weight: float) -> SectionSpec:
    return SectionSpec(section_id, "two_column", title, weight, {"left_title": left, "right_title": right, "line_count": lines})


def _quad(section_id: str, title: str, labels: List[str], lines: int, weight: float) -> SectionSpec:
    return SectionSpec(section_id, "quadrant_board", title, weight, {"labels": labels, "line_count": lines})


def _tracker(section_id: str, title: str, rows: int, columns: int, weight: float) -> SectionSpec:
    return SectionSpec(section_id, "tracker_grid", title, weight, {"rows": rows, "columns": columns})


def _calendar(section_id: str, title: str, weeks: int, weight: float) -> SectionSpec:
    return SectionSpec(section_id, "calendar_grid", title, weight, {"weeks": weeks})


def _rating(section_id: str, title: str, labels: List[str], steps: int, weight: float) -> SectionSpec:
    return SectionSpec(section_id, "rating_scale", title, weight, {"labels": labels, "steps": steps})
