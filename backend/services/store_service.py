"""
SQLite store service — persists parsed reports and their test results.
Uses SQLAlchemy Core (no ORM overhead) for simplicity.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    select,
)

from backend.config import get_settings
from backend.models.report import ReportData

logger = logging.getLogger(__name__)

metadata = MetaData()

reports_table = Table(
    "reports",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("patient", String(256)),
    Column("report_date", String(10)),  # YYYY-MM-DD
    Column("report_type", String(64)),
    Column("lab_name", String(256), nullable=True),
    Column("doctor", String(256), nullable=True),
    Column("raw_json", Text),           # full ReportData as JSON
    Column("uploaded_at", String(32)),
)

test_results_table = Table(
    "test_results",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("report_id", Integer),
    Column("test_name", String(256)),
    Column("value", Float),
    Column("unit", String(64)),
    Column("reference_range", String(128)),
    Column("status", String(32)),
)


def _get_engine():
    settings = get_settings()
    db_url = f"sqlite:///{settings.db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    metadata.create_all(engine)
    return engine


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _get_engine()
    return _engine


def save_report(report: ReportData) -> int:
    """
    Persist a fully-flagged ReportData to SQLite.
    Returns the new report row ID.
    """
    engine = get_engine()
    now = datetime.utcnow().isoformat()

    with engine.begin() as conn:
        result = conn.execute(
            insert(reports_table).values(
                patient=report.patient,
                report_date=report.report_date,
                report_type=report.report_type.value,
                lab_name=report.lab_name,
                doctor=report.doctor,
                raw_json=report.model_dump_json(),
                uploaded_at=now,
            )
        )
        report_id = result.inserted_primary_key[0]
        logger.info("Saved report id=%d for patient='%s'", report_id, report.patient)

        # Save individual test rows
        for t in report.tests:
            conn.execute(
                insert(test_results_table).values(
                    report_id=report_id,
                    test_name=t.name,
                    value=t.value,
                    unit=t.unit,
                    reference_range=t.reference_range,
                    status=t.status.value,
                )
            )

    return report_id


def list_reports() -> List[dict]:
    """Return all stored reports as dicts (without full raw_json)."""
    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                reports_table.c.id,
                reports_table.c.patient,
                reports_table.c.report_date,
                reports_table.c.report_type,
                reports_table.c.lab_name,
                reports_table.c.doctor,
                reports_table.c.uploaded_at,
            ).order_by(reports_table.c.uploaded_at.desc())
        ).fetchall()
    return [dict(r._mapping) for r in rows]


def get_report_by_id(report_id: int) -> Optional[ReportData]:
    """Load a single report from SQLite and deserialize to ReportData."""
    engine = get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            select(reports_table.c.raw_json).where(reports_table.c.id == report_id)
        ).fetchone()
    if row is None:
        return None
    return ReportData.model_validate_json(row.raw_json)
