import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQml.Models
import org.kde.plasma.plasmoid
import org.kde.plasma.plasma5support as Plasma5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    preferredRepresentation: fullRepresentation
    Plasmoid.icon: "view-calendar-tasks"
    Plasmoid.title: "Weekly Todo"
    property var state: ({ hasPlan: false, items: [], activities: [], completions: {}, days: [], progress: 0, locked: true, templates: [], templateId: null })
    property string selectedDate: ""

    function colorFor(progress) {
        if (progress <= 0.333) return Qt.rgba(0.88 + progress * 0.36, 0.106 + progress * 0.278, 0.141 - progress * 0.141, 1)
        if (progress <= 0.666) {
            const step = (progress - 0.333) / 0.333
            return Qt.rgba(1.0 - step * 0.035, 0.47 + step * 0.35, step * 0.176, 1)
        }
        const step = (progress - 0.666) / 0.334
        return Qt.rgba(0.965 - step * 0.816, 0.82 - step * 0.185, 0.176 + step * 0.235, 1)
    }

    function execute(command) { executable.connectSource(command) }
    function refresh() { execute("weekly-todo-data summary") }
    function showWeek(offset) {
        const day = new Date(root.state.weekStart + "T12:00:00")
        day.setDate(day.getDate() + offset * 7)
        execute("weekly-todo-data week " + day.toISOString().slice(0, 10))
    }
    function selectDay(day) { execute("weekly-todo-data day " + day) }
    function toggle(activityId) { execute("weekly-todo-data toggle " + activityId) }
    function changeLock() { execute("weekly-todo-data lock " + (root.state.locked ? "off" : "on")) }
    function applyTemplate(templateId) {
        const week = root.state.weekStart ? " " + root.state.weekStart : ""
        execute("weekly-todo-data apply " + templateId + week)
    }
    function quoteArg(value) {
        return "'" + String(value).replace(/'/g, "'\\''") + "'"
    }
    function createTemplate(name, activities) {
        const payload = JSON.stringify({
            name: name,
            activities: activities,
            weekStart: root.state.weekStart || "",
            apply: !root.state.hasPlan
        })
        execute("weekly-todo-data create " + quoteArg(payload))
    }
    function currentTemplateName() {
        const templates = root.state.templates || []
        const selected = templates.find((item) => item.id === root.state.templateId)
        if (selected)
            return selected.name
        if (templates.length === 0)
            return "New template"
        return "Choose template"
    }

    Plasma5Support.DataSource {
        id: executable
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) {
            executable.disconnectSource(source)
            try {
                const result = JSON.parse(data["stdout"])
                if (result.error) { errorLabel.text = result.error; return }
                root.state = result
                root.selectedDate = result.selectedDate
                errorLabel.text = ""
            } catch (error) { errorLabel.text = "Could not read Weekly Todo data." }
        }
    }

    fullRepresentation: Item {
        implicitWidth: Kirigami.Units.gridUnit * 23
        implicitHeight: Kirigami.Units.gridUnit * 21

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: Kirigami.Units.smallSpacing
            spacing: Kirigami.Units.smallSpacing

            RowLayout {
                Layout.fillWidth: true
                ToolButton { icon.name: "go-previous"; onClicked: root.showWeek(-1); Accessible.name: "Previous week" }
                Label { text: root.state.weekStart || "Weekly Todo"; font.bold: true; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true }
                ToolButton { icon.name: "go-next"; onClicked: root.showWeek(1); Accessible.name: "Next week" }
                ToolButton {
                    icon.name: root.state.locked ? "changes-prevent" : "changes-allow"
                    onClicked: root.changeLock()
                    Accessible.name: root.state.locked ? "Unlock editing" : "Lock editing"
                }
                ToolButton {
                    visible: !root.state.locked
                    icon.name: "view-list-details"
                    text: root.currentTemplateName()
                    display: AbstractButton.TextBesideIcon
                    Accessible.name: "Change template"
                    ToolTip.visible: hovered
                    ToolTip.text: "Change or create a template"
                    onClicked: templateMenu.popup()

                    Menu {
                        id: templateMenu
                        MenuItem {
                            text: "New template…"
                            icon.name: "list-add"
                            onTriggered: newTemplateDialog.open()
                        }
                        MenuSeparator {}
                        Instantiator {
                            model: root.state.templates || []
                            delegate: MenuItem {
                                required property var modelData
                                text: modelData.name + "  ·  " + modelData.activityCount
                                checkable: true
                                checked: modelData.id === root.state.templateId
                                onTriggered: root.applyTemplate(modelData.id)
                            }
                            onObjectAdded: (index, object) => templateMenu.insertItem(index + 2, object)
                            onObjectRemoved: (_index, object) => templateMenu.removeItem(object)
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Repeater {
                    model: root.state.days
                    delegate: Button {
                        required property var modelData
                        Layout.fillWidth: true
                        text: modelData.label
                        checkable: false
                        highlighted: modelData.date === root.state.today
                        onClicked: root.selectDay(modelData.date)
                        background: Rectangle {
                            radius: Kirigami.Units.smallSpacing
                            color: modelData.date === root.state.today
                                ? root.colorFor(root.state.progress)
                                : (root.selectedDate === modelData.date ? Kirigami.Theme.highlightColor : "transparent")
                        }
                        contentItem: Label {
                            text: parent.text
                            color: (modelData.date === root.state.today || root.selectedDate === modelData.date)
                                ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                }
            }

            Label { text: root.selectedDate === root.state.today ? "Today" : root.selectedDate; font.bold: true; Layout.fillWidth: true }

            Rectangle {
                visible: root.selectedDate === root.state.today
                Layout.fillWidth: true
                Layout.preferredHeight: 5
                radius: height / 2
                color: Kirigami.Theme.disabledTextColor
                Rectangle { width: parent.width * root.state.progress; height: parent.height; radius: height / 2; color: root.colorFor(root.state.progress) }
            }

            Label {
                visible: !root.state.hasPlan
                text: root.state.locked
                    ? "Unlock to choose a template, or open Weekly Todo to plan this week."
                    : "Choose a template, or create a new one from the template button."
                wrapMode: Text.WordWrap
                Layout.fillWidth: true
            }

            ListView {
                visible: root.state.hasPlan
                model: root.state.items
                clip: true
                spacing: Kirigami.Units.smallSpacing
                Layout.fillWidth: true
                Layout.fillHeight: true
                delegate: Button {
                    required property var modelData
                    property bool completed: modelData.done
                    width: ListView.view.width
                    text: completed ? "✓  " + modelData.title : modelData.title
                    icon.name: ""
                    enabled: root.selectedDate === root.state.today
                    onClicked: root.toggle(modelData.id)
                    Accessible.name: completed ? "Completed: " + modelData.title : "Mark complete: " + modelData.title
                }
            }

            Label { id: errorLabel; visible: text.length > 0; color: Kirigami.Theme.negativeTextColor; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }

        Dialog {
            id: newTemplateDialog
            title: "New template"
            modal: true
            anchors.centerIn: parent
            width: Math.min(parent.width - Kirigami.Units.largeSpacing, Kirigami.Units.gridUnit * 20)
            standardButtons: Dialog.Cancel | Dialog.Ok
            onOpened: {
                templateNameField.text = ""
                activityTitleField.text = ""
                draftActivities.clear()
                templateNameField.forceActiveFocus()
            }
            onAccepted: {
                const titles = []
                for (let index = 0; index < draftActivities.count; index++)
                    titles.push(draftActivities.get(index).title)
                root.createTemplate(templateNameField.text, titles)
            }

            ColumnLayout {
                width: newTemplateDialog.availableWidth
                spacing: Kirigami.Units.smallSpacing

                Label { text: "Template name"; Layout.fillWidth: true }
                TextField {
                    id: templateNameField
                    placeholderText: "Morning"
                    Layout.fillWidth: true
                    Accessible.name: "Template name"
                    onAccepted: activityTitleField.forceActiveFocus()
                }

                Label { text: "Activities"; Layout.fillWidth: true }
                Repeater {
                    model: draftActivities
                    delegate: RowLayout {
                        required property int index
                        required property string title
                        Layout.fillWidth: true
                        Label { text: title; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        ToolButton {
                            icon.name: "user-trash-symbolic"
                            Accessible.name: "Remove " + title
                            onClicked: draftActivities.remove(index)
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    TextField {
                        id: activityTitleField
                        placeholderText: "New activity"
                        Layout.fillWidth: true
                        Accessible.name: "New activity"
                        onAccepted: addDraftActivity.click()
                    }
                    Button {
                        id: addDraftActivity
                        text: "Add"
                        onClicked: {
                            const title = activityTitleField.text.trim()
                            if (!title)
                                return
                            draftActivities.append({ title: title })
                            activityTitleField.text = ""
                            activityTitleField.forceActiveFocus()
                        }
                    }
                }
            }
        }
    }

    Timer { interval: 30000; repeat: true; running: true; triggeredOnStart: true; onTriggered: root.refresh() }
    ListModel { id: draftActivities }
}
