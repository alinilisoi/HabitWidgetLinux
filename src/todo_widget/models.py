from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, timedelta
from typing import Any
from uuid import uuid4


def monday_for(day: date) -> date:
    """Return the ISO (Monday-starting) week containing *day*."""
    return day - timedelta(days=day.weekday())


def new_id() -> str:
    return str(uuid4())


@dataclass(frozen=True)
class Activity:
    id: str
    title: str

    @classmethod
    def create(cls, title: str) -> "Activity":
        title = title.strip()
        if not title:
            raise ValueError("An activity title cannot be blank.")
        return cls(new_id(), title)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Activity":
        item = cls(str(raw["id"]), str(raw["title"]).strip())
        if not item.title:
            raise ValueError("An activity title cannot be blank.")
        return item

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    activities: tuple[Activity, ...]

    @classmethod
    def create(cls, name: str, activities: list[Activity] | tuple[Activity, ...] = ()) -> "Template":
        return cls(new_id(), cls._validated_name(name), cls._validated_activities(activities))

    @staticmethod
    def _validated_name(name: str) -> str:
        name = name.strip()
        if not name:
            raise ValueError("A template name cannot be blank.")
        return name

    @staticmethod
    def _validated_activities(items: list[Activity] | tuple[Activity, ...]) -> tuple[Activity, ...]:
        activities = tuple(items)
        titles = [item.title.casefold() for item in activities]
        if len(titles) != len(set(titles)):
            raise ValueError("A template cannot contain duplicate activity titles.")
        return activities

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Template":
        return cls(
            str(raw["id"]),
            cls._validated_name(str(raw["name"])),
            cls._validated_activities(tuple(Activity.from_dict(item) for item in raw.get("activities", []))),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "activities": [item.to_dict() for item in self.activities]}

    def renamed(self, name: str) -> "Template":
        return Template(self.id, self._validated_name(name), self.activities)

    def with_activities(self, activities: list[Activity]) -> "Template":
        return Template(self.id, self.name, self._validated_activities(activities))


@dataclass(frozen=True)
class WeeklyPlan:
    week_start: str
    template_id: str | None
    activities: tuple[Activity, ...]
    completions: dict[str, tuple[str, ...]]

    @classmethod
    def from_template(cls, start: date, template: Template) -> "WeeklyPlan":
        return cls(start.isoformat(), template.id, tuple(template.activities), {})

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "WeeklyPlan":
        start = date.fromisoformat(str(raw["weekStart"]))
        if monday_for(start) != start:
            raise ValueError("Weekly plan must start on a Monday.")
        activities = tuple(Activity.from_dict(item) for item in raw.get("activities", []))
        activity_ids = {item.id for item in activities}
        completions: dict[str, tuple[str, ...]] = {}
        for key, values in raw.get("completions", {}).items():
            completed_date = date.fromisoformat(str(key))
            if not start <= completed_date <= start + timedelta(days=6):
                raise ValueError("Completion falls outside its weekly plan.")
            completed = tuple(str(value) for value in values)
            if not set(completed).issubset(activity_ids):
                raise ValueError("Completion references an unknown activity.")
            completions[completed_date.isoformat()] = completed
        return cls(start.isoformat(), raw.get("templateId"), activities, completions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "weekStart": self.week_start,
            "templateId": self.template_id,
            "activities": [item.to_dict() for item in self.activities],
            "completions": {day: list(ids) for day, ids in self.completions.items()},
        }

    def is_done(self, day: date, activity_id: str) -> bool:
        return activity_id in self.completions.get(day.isoformat(), ())

    def toggled(self, day: date, activity_id: str) -> "WeeklyPlan":
        start = date.fromisoformat(self.week_start)
        if not start <= day <= start + timedelta(days=6):
            raise ValueError("The selected day is outside this week.")
        if activity_id not in {item.id for item in self.activities}:
            raise ValueError("Unknown activity.")
        completions = dict(self.completions)
        current = set(completions.get(day.isoformat(), ()))
        if activity_id in current:
            current.remove(activity_id)
        else:
            current.add(activity_id)
        if current:
            completions[day.isoformat()] = tuple(sorted(current))
        else:
            completions.pop(day.isoformat(), None)
        return WeeklyPlan(self.week_start, self.template_id, self.activities, completions)
