import tempfile
import unittest
from pathlib import Path

from todo_widget.models import Activity, Template, WeeklyPlan
from todo_widget.storage import Store


class StoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary))
            template = Template.create("Daily", [Activity.create("Stretch")])
            store.save_templates([template])
            plan = WeeklyPlan.from_template(__import__("datetime").date(2026, 9, 21), template)
            store.save_weeks({plan.week_start: plan})
            store.save_locked(False)
            self.assertEqual(store.load_templates(), [template])
            self.assertEqual(store.load_weeks()[plan.week_start], plan)
            self.assertFalse(store.load_locked())

    def test_invalid_json_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "templates.json").write_text("not json", encoding="utf-8")
            store = Store(root)
            self.assertEqual(store.load_templates(), [])
            self.assertIsNotNone(store.warning)
            self.assertTrue(list(root.glob("templates.json.invalid-*")))

    def test_invalid_schema_is_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "weeks.json").write_text('{"weeks": "not a list"}', encoding="utf-8")
            store = Store(root)
            self.assertEqual(store.load_weeks(), {})
            self.assertTrue(list(root.glob("weeks.json.invalid-*")))
