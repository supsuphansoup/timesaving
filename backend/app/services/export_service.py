"""
Export service — generate PDF and Excel files from a confirmed timetable.
"""

from __future__ import annotations

import io
from typing import Any

from sqlalchemy.orm import Session

from app.models.course import Course
from app.models.professor import Professor
from app.models.room import Room
from app.models.timetable import Assignment, Timetable
from app.services.timetable_service import get_timetable

DAYS = ["MON", "TUE", "WED", "THU", "FRI"]
DAY_LABELS = {"MON": "월", "TUE": "화", "WED": "수", "THU": "목", "FRI": "금"}
PERIODS = list(range(1, 10))


def _build_grid(db: Session, timetable_id: int) -> tuple[list[dict], dict]:
    """Build a (assignments, lookup) tuple for rendering."""
    assignments = db.query(Assignment).filter(Assignment.timetable_id == timetable_id).all()
    course_map = {c.id: c for c in db.query(Course).all()}
    room_map = {r.id: r for r in db.query(Room).all()}
    prof_map = {p.id: p for p in db.query(Professor).all()}

    rows = []
    for a in assignments:
        c = course_map.get(a.course_id)
        r = room_map.get(a.room_id)
        p = prof_map.get(c.professor_id) if c else None
        rows.append(
            {
                "day": a.day,
                "day_label": DAY_LABELS.get(a.day, a.day),
                "period": a.start_period,
                "course": c.course_name if c else "?",
                "room": r.room_name if r else "?",
                "professor": p.name if p else "?",
                "department": c.department if c else "?",
                "grade": c.target_grade if c else "?",
            }
        )
    return rows, {}


def export_excel(db: Session, timetable_id: int) -> bytes:
    """Generate an Excel workbook and return raw bytes."""
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        raise RuntimeError("openpyxl 라이브러리가 설치되어 있지 않습니다.")

    rows, _ = _build_grid(db, timetable_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "시간표"

    header_fill = PatternFill("solid", fgColor="2563EB")
    header_font = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center")

    headers = ["교시", "월", "화", "수", "목", "금"]
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center

    # Build cell map: (day, period) -> text
    cell_data: dict[tuple, list[str]] = {}
    for row in rows:
        key = (row["day"], row["period"])
        cell_data.setdefault(key, []).append(f"{row['course']}\n({row['room']})\n{row['professor']}")

    for period in PERIODS:
        r = period + 1
        ws.cell(row=r, column=1, value=f"{period}교시").alignment = center
        for col, day in enumerate(DAYS, start=2):
            content = "\n\n".join(cell_data.get((day, period), []))
            cell = ws.cell(row=r, column=col, value=content)
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.row_dimensions[r].height = 80

    ws.column_dimensions["A"].width = 8
    for col_letter in ["B", "C", "D", "E", "F"]:
        ws.column_dimensions[col_letter].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


def export_pdf(db: Session, timetable_id: int) -> bytes:
    """Generate a PDF timetable and return raw bytes."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    except ImportError:
        raise RuntimeError("reportlab 라이브러리가 설치되어 있지 않습니다.")

    rows, _ = _build_grid(db, timetable_id)

    cell_data: dict[tuple, list[str]] = {}
    for row in rows:
        key = (row["day"], row["period"])
        cell_data.setdefault(key, []).append(f"{row['course']} ({row['room']}) {row['professor']}")

    table_data = [["교시", "월", "화", "수", "목", "금"]]
    for period in PERIODS:
        row_cells = [f"{period}교시"]
        for day in DAYS:
            content = " / ".join(cell_data.get((day, period), ["-"]))
            row_cells.append(content)
        table_data.append(row_cells)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), topMargin=1 * cm, bottomMargin=1 * cm)

    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F1F5F9")]),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("WORDWRAP", (0, 0), (-1, -1), True),
        ]
    )

    col_widths = [2 * cm] + [4.8 * cm] * 5
    t = Table(table_data, colWidths=col_widths, rowHeights=[1.2 * cm] + [2.5 * cm] * len(PERIODS))
    t.setStyle(style)

    title = Paragraph(
        f"<b>동서대학교 강의실 시간표 (ID: {timetable_id})</b>",
        getSampleStyleSheet()["Title"],
    )

    doc.build([title, Spacer(1, 0.3 * cm), t])
    buf.seek(0)
    return buf.read()
