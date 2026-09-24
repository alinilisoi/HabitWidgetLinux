from datetime import date
import unittest

from todo_widget.models import Activity, Template, WeeklyPlan, monday_for


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.template = Template.create("Morning", [Activity.create("Walk"), Activity.create("Read")])

    def test_monday_for_handles_year_boundary(self):
        self.assertEqual(monday_for(date(2027, 1, 1)), date(2026, 12, 28))

    def test_plan_copies_template_and_isolates_daily_completion(self):
        plan = WeeklyPlan.from_template(date(2026, 9, 21), self.template)
        changed = plan.toggled(date(2026, 9, 21), self.template.activities[0].id)
        self.assertTrue(changed.is_done(date(2026, 9, 21), self.template.activities[0].id))
        self.assertFalse(changed.is_done(date(2026, 9, 22), self.template.activities[0].id))
        self.assertEqual(plan.activities, changed.activities)

    def test_duplicate_titles_are_rejected(self):
        with self.assertRaises(ValueError):
            Template.create("Duplicate", [Activity.create("Read"), Activity.create(" read ")])

    def test_round_trip(self):
        plan = WeeklyPlan.from_template(date(2026, 9, 21), self.template)
        self.assertEqual(WeeklyPlan.from_dict(plan.to_dict()), plan)
