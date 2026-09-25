from datetime import date
from pathlib import Path
import tempfile
import unittest

from todo_widget.bridge import apply_template, create_template, set_locked, summary, toggle, week_view
from todo_widget.models import Activity, Template, WeeklyPlan
from todo_widget.storage import Store


class BridgeTests(unittest.TestCase):
    def test_summary_and_toggle_share_the_week_store(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary))
            activity = Activity.create("Walk")
            template = Template.create("Daily", [activity])
            plan = WeeklyPlan.from_template(date(2026, 9, 21), template)
            store.save_weeks({plan.week_start: plan})
            store.save_locked(True)
            before = summary(store, date(2026, 9, 21))
            self.assertEqual(before["progress"], 0)
            after = toggle(store, activity.id, date(2026, 9, 21))
            self.assertEqual(after["progress"], 1)
            self.assertTrue(after["items"][0]["done"])

            view = week_view(store, date(2026, 9, 21), date(2026, 9, 21))
            self.assertEqual(len(view["days"]), 7)
            self.assertEqual(view["days"][0]["date"], "2026-09-21")
            self.assertEqual(view["activities"][0]["title"], "Walk")
            self.assertEqual(view["selectedDate"], "2026-09-21")
            self.assertTrue(view["items"][0]["done"])
            self.assertFalse(set_locked(store, False, date(2026, 9, 21))["locked"])

    def test_apply_template_replaces_week_when_unlocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary))
            walk = Activity.create("Walk")
            read = Activity.create("Read")
            morning = Template.create("Morning", [walk])
            evening = Template.create("Evening", [read])
            store.save_templates([morning, evening])
            store.save_weeks({WeeklyPlan.from_template(date(2026, 9, 21), morning).week_start: WeeklyPlan.from_template(date(2026, 9, 21), morning)})
            store.save_locked(True)
            with self.assertRaisesRegex(ValueError, "Unlock"):
                apply_template(store, evening.id, date(2026, 9, 21), date(2026, 9, 21))
            store.save_locked(False)
            view = apply_template(store, evening.id, date(2026, 9, 21), date(2026, 9, 21))
            self.assertEqual(view["templateId"], evening.id)
            self.assertEqual(view["activities"][0]["title"], "Read")
            self.assertEqual([item["name"] for item in view["templates"]], ["Morning", "Evening"])

    def test_create_template_when_unlocked(self):
        with tempfile.TemporaryDirectory() as temporary:
            store = Store(Path(temporary))
            store.save_locked(True)
            with self.assertRaisesRegex(ValueError, "Unlock"):
                create_template(store, "Morning", ["Walk"], date(2026, 9, 21), date(2026, 9, 21))
            store.save_locked(False)
            created = create_template(store, "Morning", ["Walk"], date(2026, 9, 21), date(2026, 9, 21))
            self.assertEqual([item["name"] for item in created["templates"]], ["Morning"])
            self.assertFalse(created["hasPlan"])
            applied = create_template(
                store, "Evening", ["Read"], date(2026, 9, 21), date(2026, 9, 21), apply=True
            )
            self.assertTrue(applied["hasPlan"])
            self.assertEqual(applied["activities"][0]["title"], "Read")
            self.assertEqual([item["name"] for item in applied["templates"]], ["Morning", "Evening"])
