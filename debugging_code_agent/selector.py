from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Label

from debugging_code_agent.utils import pick_value

TABLE_ID = "#problems_table"
HINT_ID = "#hint"
UNSELECTED_MARKER = "○"
SELECTED_MARKER = "●"
INITIAL_HINT = "SPACE to select · CTRL+S to confirm · Q to quit"
SELECTION_HINT = "Selected {count} item(s) · CTRL+S to confirm · Q to quit"


@dataclass(frozen=True, slots=True)
class ProblemRow:
    task_id: str
    difficulty: str
    tags: str

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> ProblemRow:
        return cls(
            task_id=pick_value(record, "slug", "task_id", "id", "_id", default=""),
            difficulty=pick_value(record, "difficulty", "level", default=""),
            tags=pick_value(record, "tags", "topic_tags", "topics", default=""),
        )

    def as_table_row(self) -> tuple[str, str, str, str]:
        return (
            UNSELECTED_MARKER,
            self.task_id,
            self.difficulty,
            self.tags,
        )


def _as_problem_rows(records: Iterable[Any]) -> list[ProblemRow]:
    rows: list[ProblemRow] = []
    for record in records:
        if isinstance(record, Mapping):
            rows.append(ProblemRow.from_record(record))
    return rows


class Selector(App):
    BINDINGS = [
        Binding("space", "toggle_select", "Select"),
        Binding("ctrl+s", "confirm", "Confirm"),
        Binding("q", "quit", "Quit"),
    ]

    CSS = """
    DataTable { height: 1fr; }
    Label { padding: 1; color: $success; }
    """

    def __init__(self, records: Iterable[Any]) -> None:
        super().__init__()
        self.problems: list[ProblemRow] = _as_problem_rows(records)
        self.selected_ids: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(INITIAL_HINT, id=HINT_ID.removeprefix("#"))
        yield DataTable(id=TABLE_ID.removeprefix("#"))
        yield Footer()

    @property
    def table(self) -> DataTable:
        return self.query_one(TABLE_ID, DataTable)

    @property
    def hint(self) -> Label:
        return self.query_one(HINT_ID, Label)

    def _setup_table(self, table: DataTable) -> None:
        table.cursor_type = "row"
        for column_name, width in (
            (" ", 2),
            ("Task", 60),
            ("Difficulty", 10),
            ("Tags", 60),
        ):
            table.add_column(column_name, width=width)

    def _populate_table(self, table: DataTable) -> None:
        for problem in self.problems:
            table.add_row(
                *problem.as_table_row(),
                key=problem.task_id or None,
            )

    def on_mount(self) -> None:
        table = self.table
        self._setup_table(table)
        self._populate_table(table)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        self.action_toggle_select()

    def _current_selection(self) -> tuple[int, str] | None:
        table = self.table
        if table.row_count == 0:
            return None

        row_index = table.cursor_row
        if row_index is None or row_index < 0:
            return None

        try:
            row_values = table.get_row_at(row_index)
        except Exception:
            return None

        if not row_values or len(row_values) < 2:
            return None

        task_id = str(row_values[1]).strip()
        if not task_id:
            return None

        return row_index, task_id

    def _toggle_selected_id(self, task_id: str) -> str:
        if task_id in self.selected_ids:
            self.selected_ids.remove(task_id)
            return UNSELECTED_MARKER

        self.selected_ids.add(task_id)
        return SELECTED_MARKER

    def _update_hint(self) -> None:
        self.hint.update(SELECTION_HINT.format(count=len(self.selected_ids)))

    def action_toggle_select(self) -> None:
        selected_row = self._current_selection()
        if selected_row is None:
            return

        row_index, task_id = selected_row
        marker = self._toggle_selected_id(task_id)
        self.table.update_cell_at(Coordinate(row_index, 0), marker)
        self._update_hint()

    def action_confirm(self) -> None:
        selected = sorted(self.selected_ids)
        self.exit(selected)
