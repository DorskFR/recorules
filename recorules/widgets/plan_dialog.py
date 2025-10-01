"""Dialog for planning future days."""

from datetime import date
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class PlanDialog(ModalScreen):
    """Modal dialog for planning a future day."""

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        ("escape", "dismiss", "Cancel"),
    ]

    CSS = """
    PlanDialog {
        align: center middle;
    }

    #dialog {
        width: 60;
        height: auto;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    #dialog-title {
        width: 100%;
        text-align: center;
        margin-bottom: 1;
        text-style: bold;
    }

    .input-row {
        height: auto;
        margin: 1 0;
    }

    .input-label {
        width: 20;
        padding-right: 1;
    }

    #button-row {
        width: 100%;
        height: auto;
        margin-top: 1;
    }

    Button {
        margin: 0 1;
    }
    """

    def __init__(self, target_date: date, **kwargs) -> None:
        super().__init__(**kwargs)
        self.target_date = target_date

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Vertical(id="dialog"):
            yield Static(
                f"Plan for {self.target_date.strftime('%Y-%m-%d (%a)')}", id="dialog-title"
            )

            with Grid(classes="input-row"):
                yield Label("Office hours:", classes="input-label")
                yield Input(placeholder="0", id="office-hours")

            with Grid(classes="input-row"):
                yield Label("WFH hours:", classes="input-label")
                yield Input(placeholder="0", id="wfh-hours")

            with Grid(classes="input-row"):
                yield Label("Note:", classes="input-label")
                yield Input(placeholder="Optional note", id="note")

            with Grid(classes="input-row"):
                yield Label("Paid leave:", classes="input-label")
                yield Button("No", id="paid-leave-toggle", variant="default")

            with Grid(id="button-row"):
                yield Button("Save", id="save-button", variant="primary")
                yield Button("Cancel", id="cancel-button", variant="default")
                yield Button("Delete", id="delete-button", variant="error")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "cancel-button":
            self.dismiss(None)
        elif event.button.id == "save-button":
            self.save_plan()
        elif event.button.id == "delete-button":
            self.dismiss({"action": "delete", "date": self.target_date})
        elif event.button.id == "paid-leave-toggle":
            self.toggle_paid_leave()

    def toggle_paid_leave(self) -> None:
        """Toggle the paid leave button."""
        button = self.query_one("#paid-leave-toggle", Button)
        if button.label == "No":
            button.label = "Yes"
            button.variant = "success"
        else:
            button.label = "No"
            button.variant = "default"

    def save_plan(self) -> None:
        """Save the plan and dismiss the dialog."""
        office_input = self.query_one("#office-hours", Input)
        wfh_input = self.query_one("#wfh-hours", Input)
        note_input = self.query_one("#note", Input)
        paid_leave_button = self.query_one("#paid-leave-toggle", Button)

        try:
            office_hours = float(office_input.value or "0")
            wfh_hours = float(wfh_input.value or "0")
        except ValueError:
            self.notify("Invalid hours format", severity="error")
            return

        if office_hours < 0 or wfh_hours < 0:
            self.notify("Hours cannot be negative", severity="error")
            return

        result = {
            "action": "save",
            "date": self.target_date,
            "office_minutes": int(office_hours * 60),
            "remote_minutes": int(wfh_hours * 60),
            "is_paid_leave": paid_leave_button.label == "Yes",
            "note": note_input.value or "",
        }

        self.dismiss(result)
