from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from .models import Activity, Template, WeeklyPlan, monday_for
from .storage import Store, StoreError


APP_ID = "io.github.weeklytodowidget"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def completion_color(progress: float) -> str:
    """Return a continuous red → orange → yellow → green completion color."""
    progress = max(0.0, min(1.0, progress))
    stops = ((0.0, (224, 27, 36)), (1 / 3, (255, 120, 0)), (2 / 3, (246, 211, 45)), (1.0, (38, 162, 105)))
    for left, right in zip(stops, stops[1:]):
        if progress <= right[0]:
            amount = (progress - left[0]) / (right[0] - left[0])
            rgb = tuple(round(left[1][index] + (right[1][index] - left[1][index]) * amount) for index in range(3))
            return "#{:02x}{:02x}{:02x}".format(*rgb)
    return "#26a269"


class ActivityRow(Gtk.ListBoxRow):
    def __init__(self, activity: Activity, done: bool, editable: bool, on_toggle):
        super().__init__()
        self.activity = activity
        self.on_toggle = on_toggle
        self.set_activatable(editable)
        self.add_css_class("activity-row")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_top=8, margin_bottom=8,
                      margin_start=12, margin_end=12)
        self.check = Gtk.CheckButton()
        self.check.set_active(done)
        self.check.set_sensitive(editable)
        self.check.set_tooltip_text("Mark complete" if not done else "Mark incomplete")
        self.check.connect("toggled", self._on_checked)
        title = Gtk.Label(label=activity.title, xalign=0, hexpand=True, wrap=True)
        title.add_css_class("dim-label" if done else "title-4")
        box.append(self.check)
        box.append(title)
        self.set_child(box)
        if editable:
            swipe = Gtk.GestureSwipe.new()
            swipe.connect("swipe", self._on_swipe)
            self.add_controller(swipe)

    def _on_checked(self, _button):
        if self.check.get_sensitive():
            self.on_toggle(self.activity.id)

    def _on_swipe(self, _gesture, offset_x, _offset_y):
        if offset_x > 60:
            self.on_toggle(self.activity.id)


class TemplateEditor(Gtk.Window):
    def __init__(self, parent: "TodoWindow"):
        super().__init__(title="Manage templates", transient_for=parent, modal=True, default_width=620, default_height=480)
        self.parent = parent
        self.selected_id: str | None = parent.templates[0].id if parent.templates else None
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=16, margin_bottom=16,
                        margin_start=16, margin_end=16)
        self.set_child(outer)
        controls = Gtk.Box(spacing=8)
        add = Gtk.Button(label="New template")
        add.connect("clicked", self._new_template)
        rename = Gtk.Button(label="Rename")
        rename.connect("clicked", self._rename_template)
        delete = Gtk.Button(label="Delete")
        delete.connect("clicked", self._confirm_delete)
        controls.append(add); controls.append(rename); controls.append(delete)
        outer.append(controls)
        split = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        self.template_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE, width_request=220)
        self.template_list.connect("row-selected", self._selected)
        split.set_start_child(self.template_list)
        self.detail = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_start=16)
        split.set_end_child(self.detail)
        outer.append(split)
        self.refresh()

    def current(self) -> Template | None:
        return next((item for item in self.parent.templates if item.id == self.selected_id), None)

    def refresh(self):
        while child := self.template_list.get_first_child(): self.template_list.remove(child)
        for template in self.parent.templates:
            row = Gtk.ListBoxRow()
            row.template_id = template.id
            row.set_child(Gtk.Label(label=template.name, xalign=0, margin_top=8, margin_bottom=8, margin_start=8))
            self.template_list.append(row)
            if template.id == self.selected_id: self.template_list.select_row(row)
        self._refresh_detail()

    def _selected(self, _list, row):
        if row:
            self.selected_id = row.template_id
            self._refresh_detail()

    def _refresh_detail(self):
        while child := self.detail.get_first_child(): self.detail.remove(child)
        template = self.current()
        if not template:
            self.detail.append(Gtk.Label(label="Create a reusable template to begin.", xalign=0))
            return
        heading = Gtk.Label(label=template.name, xalign=0)
        heading.add_css_class("title-3")
        self.detail.append(heading)
        activities = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, vexpand=True)
        for activity in template.activities:
            row = Gtk.ListBoxRow()
            line = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=5, margin_bottom=5,
                           margin_start=8, margin_end=8)
            line.append(Gtk.Label(label=activity.title, xalign=0, hexpand=True))
            remove = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove activity")
            remove.connect("clicked", self._remove_activity, activity.id)
            line.append(remove)
            row.set_child(line); activities.append(row)
        self.detail.append(activities)
        add_line = Gtk.Box(spacing=8)
        self.activity_entry = Gtk.Entry(placeholder_text="New activity")
        self.activity_entry.connect("activate", self._add_activity)
        add_activity = Gtk.Button(label="Add activity")
        add_activity.connect("clicked", self._add_activity)
        add_line.append(self.activity_entry); add_line.append(add_activity)
        self.detail.append(add_line)

    def _new_template(self, _button):
        self._text_prompt("New template", "Template name", self._create_template)

    def _create_template(self, name: str):
        try:
            template = Template.create(name)
            self.parent.templates.append(template)
            self.parent.save_templates()
            self.selected_id = template.id
            self.refresh()
        except ValueError as error: self.parent.show_error(str(error))

    def _rename_template(self, _button):
        template = self.current()
        if template: self._text_prompt("Rename template", "Template name", self._save_rename, template.name)

    def _save_rename(self, name: str):
        template = self.current()
        if not template: return
        try:
            self.parent.replace_template(template.renamed(name))
            self.refresh()
        except ValueError as error: self.parent.show_error(str(error))

    def _add_activity(self, _button):
        template = self.current()
        if not template: return
        try:
            activity = Activity.create(self.activity_entry.get_text())
            self.parent.replace_template(template.with_activities([*template.activities, activity]))
            self.refresh()
        except ValueError as error: self.parent.show_error(str(error))

    def _remove_activity(self, _button, activity_id: str):
        template = self.current()
        if template:
            self.parent.replace_template(template.with_activities([x for x in template.activities if x.id != activity_id]))
            self.refresh()

    def _confirm_delete(self, _button):
        template = self.current()
        if not template: return
        dialog = Gtk.Window(title="Delete template?", transient_for=self, modal=True, default_width=360)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=20, margin_bottom=20,
                      margin_start=20, margin_end=20)
        box.append(Gtk.Label(label=f"Delete ‘{template.name}’? Past weekly plans will be kept.", wrap=True, xalign=0))
        actions = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        confirm = Gtk.Button(label="Delete")
        confirm.add_css_class("destructive-action")
        cancel.connect("clicked", lambda _x: dialog.close())
        confirm.connect("clicked", lambda _x: self._delete_template(dialog, template.id))
        actions.append(cancel); actions.append(confirm); box.append(actions); dialog.set_child(box); dialog.present()

    def _delete_template(self, dialog, template_id: str):
        self.parent.templates = [item for item in self.parent.templates if item.id != template_id]
        self.parent.save_templates()
        self.selected_id = self.parent.templates[0].id if self.parent.templates else None
        dialog.close(); self.refresh()

    def _text_prompt(self, title: str, label: str, callback, initial: str = ""):
        dialog = Gtk.Window(title=title, transient_for=self, modal=True, default_width=360)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=20, margin_bottom=20,
                      margin_start=20, margin_end=20)
        box.append(Gtk.Label(label=label, xalign=0))
        entry = Gtk.Entry(text=initial)
        box.append(entry)
        actions = Gtk.Box(spacing=8, halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel"); save = Gtk.Button(label="Save")
        cancel.connect("clicked", lambda _x: dialog.close())
        save.connect("clicked", lambda _x: (callback(entry.get_text()), dialog.close()))
        entry.connect("activate", lambda _x: (callback(entry.get_text()), dialog.close()))
        actions.append(cancel); actions.append(save); box.append(actions); dialog.set_child(box); dialog.present(); entry.grab_focus()


class TodoWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(application=application, title="Weekly Todo", default_width=480, default_height=640)
        self.set_icon_name(APP_ID)
        self.store = Store()
        try:
            self.templates = self.store.load_templates()
            self.weeks = self.store.load_weeks()
            self.locked = self.store.load_locked()
        except StoreError as error:
            self.templates, self.weeks, self.locked = [], {}, True
            self.store.warning = str(error)
        self.today = date.today()
        self.view_week = monday_for(self.today)
        self.selected_day = self.today
        self.toast_overlay = Adw.ToastOverlay()
        self.day_color_provider = Gtk.CssProvider()
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), self.day_color_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        view = Adw.ToolbarView()
        self.toast_overlay.set_child(view)
        self.set_content(self.toast_overlay)
        header = Adw.HeaderBar()
        self.title_label = Gtk.Label()
        self.title_label.add_css_class("title")
        header.set_title_widget(self.title_label)
        previous = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Previous week")
        next_button = Gtk.Button(icon_name="go-next-symbolic", tooltip_text="Next week")
        previous.connect("clicked", lambda _x: self.change_week(-1))
        next_button.connect("clicked", lambda _x: self.change_week(1))
        header.pack_start(previous); header.pack_start(next_button)
        self.lock_button = Gtk.ToggleButton(icon_name="changes-prevent-symbolic", tooltip_text="Lock or unlock editing")
        self.lock_button.set_active(self.locked)
        self.lock_button.connect("toggled", self.set_locked)
        self.lock_button.set_icon_name("changes-prevent-symbolic" if self.locked else "changes-allow-symbolic")
        header.pack_end(self.lock_button)
        manage = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Manage templates")
        manage.connect("clicked", lambda _x: TemplateEditor(self).present())
        self.manage_button = manage; header.pack_end(manage)
        view.add_top_bar(header)
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=12, margin_bottom=12,
                               margin_start=12, margin_end=12)
        view.set_content(self.content)
        self.refresh()
        if self.store.warning: self.toast_overlay.add_toast(Adw.Toast.new(self.store.warning))

    def current_plan(self) -> WeeklyPlan | None:
        return self.weeks.get(self.view_week.isoformat())

    def is_current_week(self) -> bool:
        return self.view_week == monday_for(self.today)

    def show_error(self, message: str):
        self.toast_overlay.add_toast(Adw.Toast.new(message))

    def save_templates(self):
        try: self.store.save_templates(self.templates)
        except StoreError as error: self.show_error(str(error))

    def replace_template(self, replacement: Template):
        self.templates = [replacement if item.id == replacement.id else item for item in self.templates]
        self.save_templates(); self.refresh()

    def change_week(self, amount: int):
        self.view_week += timedelta(days=7 * amount)
        self.selected_day = self.today if self.is_current_week() else self.view_week
        self.refresh()

    def set_locked(self, button):
        self.locked = button.get_active()
        self.lock_button.set_icon_name("changes-prevent-symbolic" if self.locked else "changes-allow-symbolic")
        try: self.store.save_locked(self.locked)
        except StoreError as error: self.show_error(str(error))
        self.refresh()

    def refresh(self):
        while child := self.content.get_first_child(): self.content.remove(child)
        self.title_label.set_text(f"{self.view_week:%b %-d} – {(self.view_week + timedelta(days=6)):%b %-d}")
        self.manage_button.set_sensitive(not self.locked)
        plan = self.current_plan()
        if not plan:
            self._set_today_progress_color(None)
            self._planning_screen(); return
        self._set_today_progress_color(plan)
        day_bar = Gtk.Box(homogeneous=True, spacing=4)
        for index in range(7):
            day = self.view_week + timedelta(days=index)
            label = f"{day:%a}\n{day:%-d}"
            button = Gtk.ToggleButton(label=label)
            button.set_active(day == self.selected_day)
            if day == self.today:
                button.add_css_class("today-progress")
                button.set_tooltip_text(f"Today: {self._completion_percent(plan, day):.0%} complete")
            # Locked mode still permits reviewing the week; only completion is limited to today.
            button.set_sensitive(True)
            button.connect("clicked", self.select_day, day)
            day_bar.append(button)
        self.content.append(day_bar)
        date_label = Gtk.Label(label=self.selected_day.strftime("%A, %B %-d"), xalign=0)
        date_label.add_css_class("title-2")
        self.content.append(date_label)
        if not plan.activities:
            self.content.append(Gtk.Label(label="This template has no activities yet. Unlock and edit the template.", wrap=True, xalign=0))
            return
        activities = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE, vexpand=True)
        can_complete = self.is_current_week() and self.selected_day == self.today
        for activity in plan.activities:
            activities.append(ActivityRow(activity, plan.is_done(self.selected_day, activity.id), can_complete,
                                          lambda activity_id: self.toggle_completion(activity_id)))
        self.content.append(activities)
        hint = "Slide right or use the checkbox to mark today complete." if can_complete else "Only today's activities can be marked complete."
        self.content.append(Gtk.Label(label=hint, xalign=0))

    @staticmethod
    def _completion_percent(plan: WeeklyPlan, day: date) -> float:
        if not plan.activities:
            return 0.0
        complete = sum(plan.is_done(day, activity.id) for activity in plan.activities)
        return complete / len(plan.activities)

    def _set_today_progress_color(self, plan: WeeklyPlan | None):
        if plan is None or not self.is_current_week():
            css = ".today-progress { }"
        else:
            color = completion_color(self._completion_percent(plan, self.today))
            css = f"""
                .today-progress, .today-progress:checked {{
                  background-image: none;
                  background-color: {color};
                  color: white;
                }}
                .today-progress label {{ color: white; }}
            """
        self.day_color_provider.load_from_string(css)

    def select_day(self, _button, day: date):
        self.selected_day = day
        self.refresh()

    def toggle_completion(self, activity_id: str):
        plan = self.current_plan()
        if not plan or not (self.is_current_week() and self.selected_day == self.today): return
        try:
            self.weeks[plan.week_start] = plan.toggled(self.selected_day, activity_id)
            self.store.save_weeks(self.weeks)
            self.refresh()
        except (StoreError, ValueError) as error: self.show_error(str(error))

    def _planning_screen(self):
        title = Gtk.Label(label="Plan this week", xalign=0)
        title.add_css_class("title-1")
        self.content.append(title)
        self.content.append(Gtk.Label(label="Choose a reusable template or make a new one. Each day will receive the same activities.",
                                      wrap=True, xalign=0))
        if self.templates:
            selector = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE)
            for template in self.templates:
                row = Gtk.ListBoxRow()
                row.template_id = template.id
                row.set_child(Gtk.Label(label=f"{template.name}  ·  {len(template.activities)} activities", xalign=0,
                                        margin_top=10, margin_bottom=10, margin_start=10))
                selector.append(row)
            selector.select_row(selector.get_row_at_index(0))
            self.content.append(selector)
            apply_button = Gtk.Button(label="Use selected template")
            apply_button.add_css_class("suggested-action")
            apply_button.connect("clicked", self.apply_selected_template, selector)
            self.content.append(apply_button)
        else:
            self.content.append(Gtk.Label(label="No templates yet.", xalign=0))
        create = Gtk.Button(label="Create template")
        create.connect("clicked", self.create_template_for_plan)
        self.content.append(create)

    def apply_selected_template(self, _button, selector):
        row = selector.get_selected_row()
        if not row: return
        template = next(item for item in self.templates if item.id == row.template_id)
        self.apply_template(template)

    def apply_template(self, template: Template):
        plan = WeeklyPlan.from_template(self.view_week, template)
        self.weeks[plan.week_start] = plan
        try:
            self.store.save_weeks(self.weeks)
            self.selected_day = self.today if self.is_current_week() else self.view_week
            self.refresh()
        except StoreError as error: self.show_error(str(error))

    def create_template_for_plan(self, _button):
        editor = TemplateEditor(self)
        editor.present()


class TodoApplication(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS)

    def do_startup(self):
        Adw.Application.do_startup(self)
        display = Gdk.Display.get_default()
        if display:
            # Make development runs resolve the project icon without installation.
            Gtk.IconTheme.get_for_display(display).add_search_path(str(PROJECT_ROOT / "data" / "icons"))

    def do_activate(self):
        window = self.props.active_window
        if not window:
            window = TodoWindow(self)
        window.present()


def main() -> int:
    return TodoApplication().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
