from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from .models import Template, WeeklyPlan


class StoreError(RuntimeError):
    pass


class Store:
    """Small local JSON store; invalid files are preserved before fresh data is used."""

    def __init__(self, directory: Path | None = None):
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        self.directory = directory or base / "weekly-todo-widget"
        self.warning: str | None = None

    def _path(self, name: str) -> Path:
        return self.directory / name

    def _read(self, name: str, default: object) -> object:
        path = self._path(name)
        if not path.exists():
            return default
        try:
            with path.open(encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
            return self._recover_invalid(name, default, exc)

    def _recover_invalid(self, name: str, default: object, exc: Exception) -> object:
        """Keep the original readable when JSON parses but its schema is not usable."""
        path = self._path(name)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = path.with_name(f"{path.name}.invalid-{stamp}")
        try:
            shutil.copy2(path, backup)
        except OSError as copy_error:
            raise StoreError(f"Could not preserve invalid {name}: {copy_error}") from exc
        self.warning = f"Invalid {name} was preserved as {backup.name}; starting with empty data."
        return default

    def _write(self, name: str, value: object) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        target = self._path(name)
        fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=self.directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(temporary, target)
        except OSError as exc:
            try:
                Path(temporary).unlink(missing_ok=True)
            finally:
                raise StoreError(f"Could not save {name}: {exc}") from exc

    def load_templates(self) -> list[Template]:
        raw = self._read("templates.json", {"templates": []})
        if not isinstance(raw, dict) or not isinstance(raw.get("templates", []), list):
            return self._recover_invalid("templates.json", [], ValueError("invalid structure"))
        try:
            return [Template.from_dict(item) for item in raw["templates"]]
        except (KeyError, TypeError, ValueError) as exc:
            return self._recover_invalid("templates.json", [], exc)

    def save_templates(self, templates: list[Template]) -> None:
        self._write("templates.json", {"templates": [template.to_dict() for template in templates]})

    def load_weeks(self) -> dict[str, WeeklyPlan]:
        raw = self._read("weeks.json", {"weeks": []})
        if not isinstance(raw, dict) or not isinstance(raw.get("weeks", []), list):
            return self._recover_invalid("weeks.json", {}, ValueError("invalid structure"))
        try:
            plans = [WeeklyPlan.from_dict(item) for item in raw["weeks"]]
        except (KeyError, TypeError, ValueError) as exc:
            return self._recover_invalid("weeks.json", {}, exc)
        return {plan.week_start: plan for plan in plans}

    def save_weeks(self, weeks: dict[str, WeeklyPlan]) -> None:
        self._write("weeks.json", {"weeks": [plan.to_dict() for _, plan in sorted(weeks.items())]})

    def load_locked(self) -> bool:
        raw = self._read("settings.json", {"locked": True})
        if not isinstance(raw, dict) or ("locked" in raw and not isinstance(raw["locked"], bool)):
            return self._recover_invalid("settings.json", True, ValueError("invalid structure"))
        return bool(raw.get("locked", True))

    def save_locked(self, locked: bool) -> None:
        self._write("settings.json", {"locked": locked})
