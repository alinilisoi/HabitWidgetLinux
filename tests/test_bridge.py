from datetime import date
from pathlib import Path
import tempfile
import unittest

from todo_widget.bridge import set_locked, summary, toggle, week_view
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
