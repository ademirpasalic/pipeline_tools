"""
Mini Production Tracker
A lightweight production tracking dashboard with shot/asset status,
artist assignment, and progress reporting.

Author: Ademir Pasalic
Requirements: pip install PySide6
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from PySide6 import QtWidgets, QtCore, QtGui
except ImportError:
    from PyQt5 import QtWidgets, QtCore, QtGui


STATUSES = ["Not Started", "In Progress", "Review", "Approved", "Final"]
STATUS_COLORS = {
    "Not Started": "#4a4a5e",
    "In Progress": "#40a0ff",
    "Review": "#ffc040",
    "Approved": "#00e5a0",
    "Final": "#00e5a0",
}
DEPARTMENTS = ["Layout", "Animation", "Lighting", "Compositing", "FX"]


class TrackerDatabase:
    """JSON-based shot/asset database."""

    def __init__(self, path="tracker_db.json"):
        self.path = Path(path)
        self.shots = []
        self._load()

    def _load(self):
        if self.path.exists():
            with open(self.path) as f:
                self.shots = json.load(f)

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.shots, f, indent=2)

    def add(self, name, department, artist="", status="Not Started", notes=""):
        shot = {
            "id": str(len(self.shots) + 1),
            "name": name,
            "department": department,
            "artist": artist,
            "status": status,
            "notes": notes,
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        self.shots.append(shot)
        self.save()
        return shot

    def update(self, shot_id, **kwargs):
        for shot in self.shots:
            if shot["id"] == str(shot_id):
                shot.update(kwargs)
                shot["updated"] = datetime.now().isoformat()
                self.save()
                return

    def delete(self, shot_id):
        self.shots = [s for s in self.shots if s["id"] != str(shot_id)]
        self.save()

    def get_stats(self):
        stats = {"total": len(self.shots)}
        for s in self.shots:
            stats[s["status"]] = stats.get(s["status"], 0) + 1
        return stats


class TrackerWindow(QtWidgets.QMainWindow):
    """Main GUI."""

    def __init__(self):
        super().__init__()
        self.db = TrackerDatabase()
        self.setWindowTitle("Production Tracker")
        self.setMinimumSize(1000, 650)
        self._build_ui()
        self._apply_style()
        self._refresh()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        header = QtWidgets.QLabel("Production Tracker")
        header.setObjectName("header")
        layout.addWidget(header)

        # Stats bar
        self.stats_label = QtWidgets.QLabel("")
        self.stats_label.setObjectName("stats")
        layout.addWidget(self.stats_label)

        # Add shot row
        add_row = QtWidgets.QHBoxLayout()
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setPlaceholderText("Shot/Asset name (e.g. SH010)")
        self.dept_combo = QtWidgets.QComboBox()
        self.dept_combo.addItems(DEPARTMENTS)
        self.artist_input = QtWidgets.QLineEdit()
        self.artist_input.setPlaceholderText("Artist")
        self.artist_input.setMaximumWidth(150)
        add_btn = QtWidgets.QPushButton("+ Add")
        add_btn.setObjectName("primary")
        add_btn.clicked.connect(self._add_shot)
        add_row.addWidget(self.name_input, 1)
        add_row.addWidget(self.dept_combo)
        add_row.addWidget(self.artist_input)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # Filter
        filter_row = QtWidgets.QHBoxLayout()
        filter_row.addWidget(QtWidgets.QLabel("Filter:"))
        self.filter_dept = QtWidgets.QComboBox()
        self.filter_dept.addItem("All Departments")
        self.filter_dept.addItems(DEPARTMENTS)
        self.filter_dept.currentIndexChanged.connect(self._refresh)
        self.filter_status = QtWidgets.QComboBox()
        self.filter_status.addItem("All Statuses")
        self.filter_status.addItems(STATUSES)
        self.filter_status.currentIndexChanged.connect(self._refresh)
        filter_row.addWidget(self.filter_dept)
        filter_row.addWidget(self.filter_status)
        filter_row.addStretch()
        delete_btn = QtWidgets.QPushButton("Delete Selected")
        delete_btn.clicked.connect(self._delete_selected)
        filter_row.addWidget(delete_btn)
        layout.addLayout(filter_row)

        # Table
        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Shot", "Department", "Artist", "Status", "Notes", "Updated"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 200)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.cellChanged.connect(self._cell_changed)
        layout.addWidget(self.table, 1)

    def _add_shot(self):
        name = self.name_input.text().strip()
        if not name:
            return
        self.db.add(
            name,
            self.dept_combo.currentText(),
            self.artist_input.text().strip(),
        )
        self.name_input.clear()
        self.artist_input.clear()
        self._refresh()

    def _delete_selected(self):
        rows = sorted(set(i.row() for i in self.table.selectedIndexes()), reverse=True)
        for row in rows:
            shot_id = self.table.item(row, 0).data(QtCore.Qt.UserRole)
            if shot_id is not None:
                self.db.delete(shot_id)
        self._refresh()

    def _refresh(self):
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        dept_filter = self.filter_dept.currentText()
        status_filter = self.filter_status.currentText()

        for i, shot in enumerate(self.db.shots):
            if dept_filter != "All Departments" and shot["department"] != dept_filter:
                continue
            if status_filter != "All Statuses" and shot["status"] != status_filter:
                continue

            row = self.table.rowCount()
            self.table.insertRow(row)

            name_item = QtWidgets.QTableWidgetItem(shot["name"])
            name_item.setData(QtCore.Qt.UserRole, shot["id"])
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(shot["department"]))
            self.table.setItem(row, 2, QtWidgets.QTableWidgetItem(shot["artist"]))

            # Status combo
            status_combo = QtWidgets.QComboBox()
            status_combo.addItems(STATUSES)
            status_combo.setCurrentText(shot["status"])
            status_combo.currentTextChanged.connect(lambda text, sid=shot["id"]: self._update_status(sid, text))
            self.table.setCellWidget(row, 3, status_combo)

            self.table.setItem(row, 4, QtWidgets.QTableWidgetItem(shot.get("notes", "")))
            self.table.setItem(row, 5, QtWidgets.QTableWidgetItem(shot["updated"][:16]))

            color_hex = STATUS_COLORS.get(shot.get("status", ""), "")
            if color_hex:
                q_color = QtGui.QColor(color_hex)
                q_color.setAlpha(60)
                for col in range(self.table.columnCount()):
                    cell = self.table.item(row, col)
                    if cell:
                        cell.setBackground(q_color)

        # Stats
        stats = self.db.get_stats()
        parts = [f"{stats['total']} total"]
        for status in STATUSES:
            count = stats.get(status, 0)
            if count:
                parts.append(f"{count} {status.lower()}")
        self.stats_label.setText(" · ".join(parts))
        self.table.blockSignals(False)

    def _update_status(self, shot_id, status):
        self.db.update(shot_id, status=status)
        self._refresh()

    def _cell_changed(self, row, col):
        if col in (2, 4):  # artist or notes
            shot_id = self.table.item(row, 0).data(QtCore.Qt.UserRole)
            if shot_id is not None:
                field = "artist" if col == 2 else "notes"
                value = self.table.item(row, col).text()
                self.db.update(shot_id, **{field: value})

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { background: #0a0a0f; }
            QWidget { color: #e0e0e8; font-family: 'JetBrains Mono', 'Consolas', monospace; font-size: 12px; }
            #header { font-size: 20px; font-weight: bold; color: #00e5a0; padding: 8px 0; }
            #stats { color: #7a7a8e; font-size: 11px; padding: 4px 0; }
            QLabel { color: #7a7a8e; }
            QLineEdit { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px; color: #e0e0e8; }
            QLineEdit:focus { border-color: #00e5a0; }
            QComboBox { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 6px; color: #e0e0e8; }
            QPushButton { background: #12121e; border: 1px solid #1e1e30; border-radius: 4px; padding: 8px 16px; color: #7a7a8e; }
            QPushButton:hover { border-color: #00e5a0; color: #00e5a0; }
            QPushButton#primary { background: #00e5a0; color: #0a0a0f; border-color: #00e5a0; font-weight: bold; }
            QPushButton#primary:hover { background: transparent; color: #00e5a0; }
            QTableWidget { background: #0f0f18; border: 1px solid #1e1e30; border-radius: 4px; alternate-background-color: #12121e; gridline-color: #1e1e30; }
            QTableWidget::item { padding: 4px; }
            QHeaderView::section { background: #12121e; border: 1px solid #1e1e30; padding: 6px; color: #00e5a0; font-weight: bold; }
        """)


def main():
    app = QtWidgets.QApplication(sys.argv)
    window = TrackerWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
