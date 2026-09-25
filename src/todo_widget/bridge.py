"""Command bridge used by the Plasma widget to safely access local plan data."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date

from .models import Activity, Template, WeeklyPlan, monday_for
from .storage import Store, StoreError


def template_list(store: Store) -> list[dict]:
    """Return templates the Plasma widget can apply when unlocked."""
    return [
        {"id": template.id, "name": template.name, "activityCount": len(template.activities)}
        for template in store.load_templates()
    ]


def week_view(store: Store, week_start: date, today: date, selected_day: date | None = None) -> dict:
    """Return an immutable weekly snapshot suitable for the Plasma widget."""
    plan = store.load_weeks().get(week_start.isoformat())
    locked = store.load_locked()
    templates = template_list(store)
    days = [week_start.fromordinal(week_start.toordinal() + offset) for offset in range(7)]
    selected_day = selected_day or (today if monday_for(today) == week_start else week_start)
    if selected_day not in days:
        raise ValueError("The selected day is outside this weekly plan.")
    if plan is None:
        return {
            "hasPlan": False, "locked": locked, "items": [], "activities": [], "completions": {},
            "progress": 0, "weekStart": week_start.isoformat(), "today": today.isoformat(), "selectedDate": selected_day.isoformat(),
            "templateId": None, "templates": templates,
            "days": [{"date": day.isoformat(), "label": day.strftime("%a\n%-d")} for day in days],
        }
    items = [{"id": activity.id, "title": activity.title, "done": plan.is_done(selected_day, activity.id)} for activity in plan.activities]
    progress = sum(plan.is_done(today, activity.id) for activity in plan.activities) / len(plan.activities) if plan.activities else 0
    return {
        "hasPlan": True, "locked": locked, "items": items,
        "activities": [{"id": activity.id, "title": activity.title} for activity in plan.activities],
        "completions": {day: list(ids) for day, ids in plan.completions.items()},
        "progress": progress, "weekStart": plan.week_start, "today": today.isoformat(), "selectedDate": selected_day.isoformat(),
        "templateId": plan.template_id, "templates": templates,
        "days": [{"date": day.isoformat(), "label": day.strftime("%a\n%-d")} for day in days],
    }


def summary(store: Store, today: date) -> dict:
    return week_view(store, monday_for(today), today)


def toggle(store: Store, activity_id: str, today: date) -> dict:
    weeks = store.load_weeks()
    key = monday_for(today).isoformat()
    plan = weeks.get(key)
    if plan is None:
        raise ValueError("No plan exists for this week.")
    weeks[key] = plan.toggled(today, activity_id)
    store.save_weeks(weeks)
    return summary(store, today)


def set_locked(store: Store, locked: bool, today: date) -> dict:
    store.save_locked(locked)
    return summary(store, today)


def apply_template(store: Store, template_id: str, week_start: date, today: date, selected_day: date | None = None) -> dict:
    """Replace this week's plan with the chosen template. Requires the widget to be unlocked."""
    if store.load_locked():
        raise ValueError("Unlock the widget to change the template.")
    template = next((item for item in store.load_templates() if item.id == template_id), None)
    if template is None:
        raise ValueError("Unknown template.")
    weeks = store.load_weeks()
    plan = WeeklyPlan.from_template(week_start, template)
    weeks[plan.week_start] = plan
    store.save_weeks(weeks)
    return week_view(store, week_start, today, selected_day)


def create_template(
    store: Store,
    name: str,
    activity_titles: list[str],
    week_start: date,
    today: date,
    apply: bool = False,
) -> dict:
    """Create a reusable template. Optionally apply it to the viewed week. Requires unlock."""
    if store.load_locked():
        raise ValueError("Unlock the widget to change the template.")
    template = Template.create(name, [Activity.create(title) for title in activity_titles])
    templates = store.load_templates()
    templates.append(template)
    store.save_templates(templates)
    if apply:
        return apply_template(store, template.id, week_start, today)
    return week_view(store, week_start, today)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Data bridge for the Weekly Todo Plasma widget")
    parser.add_argument("action", choices=("summary", "week", "day", "toggle", "lock", "apply", "create"))
    parser.add_argument("activity_id", nargs="?")
    parser.add_argument("week_start", nargs="?")
    args = parser.parse_args(argv)
    try:
        store = Store()
        today = date.today()
        if args.action == "summary":
            result = summary(store, today)
        elif args.action == "week":
            start = monday_for(date.fromisoformat(args.activity_id or ""))
            result = week_view(store, start, today)
        elif args.action == "day":
            selected = date.fromisoformat(args.activity_id or "")
            result = week_view(store, monday_for(selected), today, selected)
        elif args.action == "lock":
            if args.activity_id not in ("on", "off"):
                raise ValueError("Lock state must be 'on' or 'off'.")
            result = set_locked(store, args.activity_id == "on", today)
        elif args.action == "apply":
            if not args.activity_id:
                raise ValueError("A template id is required.")
            start = monday_for(date.fromisoformat(args.week_start)) if args.week_start else monday_for(today)
            result = apply_template(store, args.activity_id, start, today)
        elif args.action == "create":
            payload = json.loads(args.activity_id or "")
            if not isinstance(payload, dict):
                raise ValueError("A template payload is required.")
            titles = payload.get("activities") or []
            if not isinstance(titles, list) or not all(isinstance(item, str) for item in titles):
                raise ValueError("Activities must be a list of titles.")
            raw_week = payload.get("weekStart") or None
            start = monday_for(date.fromisoformat(str(raw_week))) if raw_week else monday_for(today)
            result = create_template(
                store,
                str(payload.get("name", "")),
                titles,
                start,
                today,
                bool(payload.get("apply")),
            )
        else:
            result = toggle(store, args.activity_id or "", today)
        print(json.dumps(result))
        return 0
    except (StoreError, ValueError) as error:
        print(json.dumps({"error": str(error)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
