import unittest

from todo_widget.app import completion_color


class AppHelperTests(unittest.TestCase):
    def test_completion_color_uses_progress_gradient(self):
        self.assertEqual(completion_color(0), "#e01b24")
        self.assertEqual(completion_color(1 / 3), "#ff7800")
        self.assertEqual(completion_color(2 / 3), "#f6d32d")
        self.assertEqual(completion_color(1), "#26a269")
