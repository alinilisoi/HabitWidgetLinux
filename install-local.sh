#!/usr/bin/env sh
# Install the launcher metadata and icon for the current Linux user.
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
data_dir=${XDG_DATA_HOME:-"$HOME/.local/share"}
app_dir="$data_dir/weekly-todo-widget"
bin_dir="${XDG_BIN_HOME:-$HOME/.local/bin}"

install -Dm644 "$project_dir/src/todo_widget/__init__.py" "$app_dir/src/todo_widget/__init__.py"
install -Dm644 "$project_dir/src/todo_widget/app.py" "$app_dir/src/todo_widget/app.py"
install -Dm644 "$project_dir/src/todo_widget/bridge.py" "$app_dir/src/todo_widget/bridge.py"
install -Dm644 "$project_dir/src/todo_widget/models.py" "$app_dir/src/todo_widget/models.py"
install -Dm644 "$project_dir/src/todo_widget/storage.py" "$app_dir/src/todo_widget/storage.py"
install -Dm755 "$project_dir/bin/weekly-todo" "$app_dir/bin/weekly-todo"
install -Dm755 "$project_dir/bin/weekly-todo-data" "$app_dir/bin/weekly-todo-data"
mkdir -p "$bin_dir"
ln -sfn "$app_dir/bin/weekly-todo" "$bin_dir/weekly-todo"
ln -sfn "$app_dir/bin/weekly-todo-data" "$bin_dir/weekly-todo-data"

install -Dm644 "$project_dir/data/icons/hicolor/index.theme" "$data_dir/icons/hicolor/index.theme"
install -Dm644 "$project_dir/data/icons/hicolor/scalable/apps/io.github.weeklytodowidget.svg" \
  "$data_dir/icons/hicolor/scalable/apps/io.github.weeklytodowidget.svg"
install -Dm644 "$project_dir/data/applications/io.github.weeklytodowidget.desktop" \
  "$data_dir/applications/io.github.weeklytodowidget.desktop"

if command -v gtk4-update-icon-cache >/dev/null 2>&1; then
  gtk4-update-icon-cache -f "$data_dir/icons/hicolor" || true
elif command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f "$data_dir/icons/hicolor" || true
fi

if kpackagetool6 --type Plasma/Applet --show io.github.weeklytodowidget >/dev/null 2>&1; then
  kpackagetool6 --type Plasma/Applet --upgrade "$project_dir/plasma-widget"
else
  kpackagetool6 --type Plasma/Applet --install "$project_dir/plasma-widget"
fi

printf '%s\n' "Installed the Weekly Todo launcher icon and Plasma widget. Right-click the desktop, choose Add Widgets, then add Weekly Todo."
