# Weekly Todo Widget

A local-first GTK 4 / Libadwaita weekly planner for Linux. Plan each Monday–Sunday week from a reusable template, then mark today's activities complete while the widget is locked.

## Run

The application needs Python, PyGObject, GTK 4, and Libadwaita.

```bash
PYTHONPATH=src python3 -m todo_widget.app
```

Data is stored as readable JSON in `$XDG_DATA_HOME/weekly-todo-widget` (normally `~/.local/share/weekly-todo-widget`).

The launcher icon is at `data/icons/hicolor/scalable/apps/io.github.weeklytodowidget.svg`. Install that icon and the matching file in `data/applications/` into the corresponding XDG data directories when packaging the application.

For a local development installation that also updates the dock/launcher icon, run `./install-local.sh`, then restart Weekly Todo.

## KDE Plasma widget

After `./install-local.sh`, right-click the KDE desktop, choose **Add Widgets**, search for **Weekly Todo**, and drag it onto the desktop. The widget shows today's activities, refreshes every 30 seconds, and toggles completion through the same local JSON data as the GTK app.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```
