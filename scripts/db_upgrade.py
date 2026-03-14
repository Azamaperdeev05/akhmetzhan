from __future__ import annotations

import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from dotenv import load_dotenv


LEGACY_TABLES = {"emails", "scan_runs", "scan_results", "url_findings"}
EMAIL_COLUMNS = [
    "id",
    "message_id",
    "thread_id",
    "subject",
    "body_preview",
    "sender",
    "sender_domain",
    "received_at",
    "raw_headers",
    "created_at",
]
SCAN_RUN_COLUMNS = [
    "id",
    "started_at",
    "finished_at",
    "scanned_count",
    "phishing_count",
    "notes",
]
SCAN_RESULT_COLUMNS = [
    "id",
    "email_id",
    "scan_run_id",
    "phishing_probability",
    "label",
    "risk_level",
    "reasons",
    "spf_status",
    "dkim_status",
    "scanned_at",
]
URL_FINDING_COLUMNS = [
    "id",
    "scan_result_id",
    "url",
    "final_url",
    "domain",
    "suspicious",
    "reason",
]


@dataclass(frozen=True)
class LegacyMigrationResult:
    backup_path: Path
    kept_scan_results: int
    dropped_scan_results: int


def _load_database_url(project_root: Path) -> str:
    load_dotenv(project_root / ".env")
    return os.getenv("DATABASE_URL", "sqlite:///phishguard.db").strip()


def _sqlite_path_from_database_url(project_root: Path, database_url: str) -> Path | None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return None

    raw_path = database_url[len(prefix) :]
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = project_root / db_path
    return db_path.resolve()


def _sqlite_table_names(db_path: Path) -> set[str]:
    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
        return {row[0] for row in rows}
    finally:
        connection.close()


def is_legacy_sqlite_database(db_path: Path) -> bool:
    if not db_path.exists():
        return False

    tables = _sqlite_table_names(db_path)
    return LEGACY_TABLES.issubset(tables) and "alembic_version" not in tables


def _build_alembic_config(project_root: Path, database_url: str) -> Config:
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _run_alembic_upgrade(project_root: Path, database_url: str) -> None:
    config = _build_alembic_config(project_root, database_url)
    previous_database_url = os.getenv("DATABASE_URL")
    os.environ["DATABASE_URL"] = database_url
    try:
        command.upgrade(config, "head")
    finally:
        if previous_database_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_database_url


def _copy_rows(
    source_connection: sqlite3.Connection,
    target_connection: sqlite3.Connection,
    table_name: str,
    columns: list[str],
    where_clause: str = "",
    params: tuple[object, ...] = (),
) -> None:
    query = f"SELECT {', '.join(columns)} FROM {table_name} {where_clause}".strip()
    rows = source_connection.execute(query, params).fetchall()
    if not rows:
        return

    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders})"
    payload = [tuple(row[column] for column in columns) for row in rows]
    target_connection.executemany(insert_sql, payload)


def _allocate_backup_path(db_path: Path) -> Path:
    candidate = db_path.with_name(f"{db_path.stem}.legacy-backup{db_path.suffix}")
    counter = 1
    while candidate.exists():
        candidate = db_path.with_name(f"{db_path.stem}.legacy-backup-{counter}{db_path.suffix}")
        counter += 1
    return candidate


def migrate_legacy_sqlite_database(project_root: Path, db_path: Path) -> LegacyMigrationResult:
    temp_path = db_path.with_name(f"{db_path.stem}.migrated{db_path.suffix}")
    if temp_path.exists():
        temp_path.unlink()

    _run_alembic_upgrade(project_root, f"sqlite:///{temp_path.as_posix()}")

    source_connection = sqlite3.connect(db_path)
    source_connection.row_factory = sqlite3.Row
    target_connection = sqlite3.connect(temp_path)
    target_connection.row_factory = sqlite3.Row

    try:
        _copy_rows(source_connection, target_connection, "emails", EMAIL_COLUMNS)
        _copy_rows(source_connection, target_connection, "scan_runs", SCAN_RUN_COLUMNS)

        scan_result_rows = source_connection.execute(
            (
                "SELECT id, email_id, scan_run_id, phishing_probability, label, risk_level, "
                "reasons, spf_status, dkim_status, scanned_at "
                "FROM scan_results ORDER BY email_id ASC, scanned_at DESC, id DESC"
            )
        ).fetchall()

        kept_rows: list[sqlite3.Row] = []
        kept_scan_result_ids: set[int] = set()
        seen_email_ids: set[int] = set()
        for row in scan_result_rows:
            if row["email_id"] in seen_email_ids:
                continue
            seen_email_ids.add(row["email_id"])
            kept_rows.append(row)
            kept_scan_result_ids.add(int(row["id"]))

        if kept_rows:
            placeholders = ", ".join("?" for _ in SCAN_RESULT_COLUMNS)
            insert_sql = (
                f"INSERT INTO scan_results ({', '.join(SCAN_RESULT_COLUMNS)}) VALUES ({placeholders})"
            )
            target_connection.executemany(
                insert_sql,
                [tuple(row[column] for column in SCAN_RESULT_COLUMNS) for row in kept_rows],
            )

        if kept_scan_result_ids:
            scan_result_ids = sorted(kept_scan_result_ids)
            id_placeholders = ", ".join("?" for _ in scan_result_ids)
            where_clause = f"WHERE scan_result_id IN ({id_placeholders})"
            _copy_rows(
                source_connection,
                target_connection,
                "url_findings",
                URL_FINDING_COLUMNS,
                where_clause=where_clause,
                params=tuple(scan_result_ids),
            )

        target_connection.commit()
    finally:
        source_connection.close()
        target_connection.close()

    backup_path = _allocate_backup_path(db_path)
    shutil.move(str(db_path), str(backup_path))
    shutil.move(str(temp_path), str(db_path))

    return LegacyMigrationResult(
        backup_path=backup_path,
        kept_scan_results=len(kept_rows),
        dropped_scan_results=max(0, len(scan_result_rows) - len(kept_rows)),
    )


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    database_url = _load_database_url(project_root)
    sqlite_path = _sqlite_path_from_database_url(project_root, database_url)

    if sqlite_path is not None and is_legacy_sqlite_database(sqlite_path):
        result = migrate_legacy_sqlite_database(project_root=project_root, db_path=sqlite_path)
        print(
            "Legacy SQLite migration completed. "
            f"Backup: {result.backup_path} | "
            f"kept_scan_results={result.kept_scan_results} | "
            f"dropped_scan_results={result.dropped_scan_results}"
        )
        return

    _run_alembic_upgrade(project_root, database_url)
    print("Database migration completed: head")


if __name__ == "__main__":
    main()
