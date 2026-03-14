from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    case,
    create_engine,
    func,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from utils.schemas import EmailMessage, ScanResult, URLFinding


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class EmailRecord(Base):
    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    message_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    thread_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str] = mapped_column(Text, default="")
    body_preview: Mapped[str] = mapped_column(Text, default="")
    sender: Mapped[str] = mapped_column(String(512), default="")
    sender_domain: Mapped[str] = mapped_column(String(255), default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    raw_headers: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    scan_results: Mapped[list["ScanResultRecord"]] = relationship(
        "ScanResultRecord",
        back_populates="email",
        cascade="all, delete-orphan",
    )


class ScanRunRecord(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scanned_count: Mapped[int] = mapped_column(Integer, default=0)
    phishing_count: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str] = mapped_column(Text, default="")

    results: Mapped[list["ScanResultRecord"]] = relationship(
        "ScanResultRecord",
        back_populates="scan_run",
        cascade="all, delete-orphan",
    )


class ScanResultRecord(Base):
    __tablename__ = "scan_results"
    __table_args__ = (UniqueConstraint("email_id", name="uq_scan_results_email_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email_id: Mapped[int] = mapped_column(ForeignKey("emails.id"), index=True)
    scan_run_id: Mapped[int | None] = mapped_column(ForeignKey("scan_runs.id"), nullable=True, index=True)
    phishing_probability: Mapped[float] = mapped_column(Float, default=0.0)
    label: Mapped[str] = mapped_column(String(50), default="LEGITIMATE")
    risk_level: Mapped[str] = mapped_column(String(20), default="LOW")
    reasons: Mapped[str] = mapped_column(Text, default="[]")
    spf_status: Mapped[str] = mapped_column(String(20), default="unknown")
    dkim_status: Mapped[str] = mapped_column(String(20), default="unknown")
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    email: Mapped["EmailRecord"] = relationship("EmailRecord", back_populates="scan_results")
    scan_run: Mapped["ScanRunRecord | None"] = relationship("ScanRunRecord", back_populates="results")
    url_findings: Mapped[list["URLFindingRecord"]] = relationship(
        "URLFindingRecord",
        back_populates="scan_result",
        cascade="all, delete-orphan",
    )


class URLFindingRecord(Base):
    __tablename__ = "url_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_result_id: Mapped[int] = mapped_column(ForeignKey("scan_results.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    final_url: Mapped[str] = mapped_column(Text, default="")
    domain: Mapped[str] = mapped_column(String(255), default="")
    suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    reason: Mapped[str] = mapped_column(Text, default="")

    scan_result: Mapped["ScanResultRecord"] = relationship("ScanResultRecord", back_populates="url_findings")


def should_auto_create_schema(database_url: str) -> bool:
    return database_url.startswith("sqlite")


class Database:
    def __init__(self, database_url: str, auto_create_schema: bool | None = None) -> None:
        connect_args: dict[str, bool] = {}
        if database_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False

        self._engine = create_engine(database_url, future=True, connect_args=connect_args)
        self._session_factory = sessionmaker(bind=self._engine, expire_on_commit=False, future=True)
        if auto_create_schema is None:
            auto_create_schema = should_auto_create_schema(database_url)
        if auto_create_schema:
            Base.metadata.create_all(self._engine)

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def has_scan_result(self, message_id: str) -> bool:
        with self.session_scope() as session:
            count = (
                session.query(func.count(ScanResultRecord.id))
                .join(EmailRecord, ScanResultRecord.email_id == EmailRecord.id)
                .filter(EmailRecord.message_id == message_id)
                .scalar()
            )
            return bool(count)

    def start_scan_run(self) -> int:
        with self.session_scope() as session:
            run = ScanRunRecord(started_at=utcnow())
            session.add(run)
            session.flush()
            return run.id

    def finish_scan_run(
        self,
        run_id: int,
        scanned_count: int,
        phishing_count: int,
        notes: str = "",
    ) -> None:
        with self.session_scope() as session:
            run = session.get(ScanRunRecord, run_id)
            if run is None:
                return
            run.finished_at = utcnow()
            run.scanned_count = scanned_count
            run.phishing_count = phishing_count
            run.notes = notes

    def _upsert_email(self, session: Session, email: EmailMessage) -> EmailRecord:
        record = session.query(EmailRecord).filter_by(message_id=email.message_id).one_or_none()
        if record is None:
            record = EmailRecord(message_id=email.message_id)
            session.add(record)

        record.thread_id = email.thread_id
        record.subject = email.subject
        record.body_preview = (email.body or "")[:1000]
        record.sender = email.sender
        record.sender_domain = email.sender_domain
        record.received_at = email.received_at
        record.raw_headers = json.dumps(email.headers, ensure_ascii=True)
        return record

    def _find_scan_result_id_by_message_id(self, session: Session, message_id: str) -> int | None:
        existing_id = (
            session.query(ScanResultRecord.id)
            .join(EmailRecord, ScanResultRecord.email_id == EmailRecord.id)
            .filter(EmailRecord.message_id == message_id)
            .limit(1)
            .scalar()
        )
        return int(existing_id) if existing_id is not None else None

    def save_scan_result_if_new(
        self,
        email: EmailMessage,
        result: ScanResult,
        run_id: int | None = None,
    ) -> tuple[int, bool]:
        session = self._session_factory()
        try:
            email_record = self._upsert_email(session, email)
            session.flush()

            existing_id = (
                session.query(ScanResultRecord.id)
                .filter_by(email_id=email_record.id)
                .limit(1)
                .scalar()
            )
            if existing_id is not None:
                session.commit()
                return int(existing_id), False

            scan_row = ScanResultRecord(
                email_id=email_record.id,
                scan_run_id=run_id,
                phishing_probability=float(result.phishing_probability),
                label=result.label,
                risk_level=result.risk_level,
                reasons=json.dumps(result.reasons, ensure_ascii=True),
                spf_status=result.spf_status,
                dkim_status=result.dkim_status,
                scanned_at=result.scanned_at,
            )
            session.add(scan_row)
            session.flush()

            for finding in result.urls:
                payload = self._url_payload(finding)
                session.add(
                    URLFindingRecord(
                        scan_result_id=scan_row.id,
                        url=payload.url,
                        final_url=payload.final_url,
                        suspicious=payload.suspicious,
                        reason=payload.reason,
                        domain=payload.domain,
                    )
                )

            session.commit()
            return scan_row.id, True
        except IntegrityError:
            session.rollback()
            existing_id = self._find_scan_result_id_by_message_id(session, email.message_id)
            if existing_id is not None:
                return existing_id, False
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_scan_result(self, email: EmailMessage, result: ScanResult, run_id: int | None = None) -> int:
        scan_id, _created = self.save_scan_result_if_new(email=email, result=result, run_id=run_id)
        return scan_id

    def _url_payload(self, finding: URLFinding | dict[str, str]) -> URLFinding:
        if isinstance(finding, URLFinding):
            return finding

        return URLFinding(
            url=finding.get("url", ""),
            final_url=finding.get("final_url", ""),
            suspicious=bool(finding.get("suspicious", False)),
            reason=finding.get("reason", ""),
            domain=finding.get("domain", ""),
        )

    def count_results(self) -> int:
        with self.session_scope() as session:
            return int(session.query(func.count(ScanResultRecord.id)).scalar() or 0)

    def list_recent_results(self, limit: int = 50, offset: int = 0) -> list[dict[str, object]]:
        with self.session_scope() as session:
            rows = (
                session.query(ScanResultRecord, EmailRecord)
                .join(EmailRecord, ScanResultRecord.email_id == EmailRecord.id)
                .order_by(ScanResultRecord.scanned_at.desc())
                .offset(offset)
                .limit(limit)
                .all()
            )

            output: list[dict[str, object]] = []
            for scan_row, email_row in rows:
                reasons = json.loads(scan_row.reasons or "[]")
                output.append(
                    {
                        "scan_id": scan_row.id,
                        "message_id": email_row.message_id,
                        "subject": email_row.subject,
                        "sender": email_row.sender,
                        "sender_domain": email_row.sender_domain,
                        "received_at": email_row.received_at,
                        "scanned_at": scan_row.scanned_at,
                        "phishing_probability": scan_row.phishing_probability,
                        "label": scan_row.label,
                        "risk_level": scan_row.risk_level,
                        "reasons": reasons,
                        "spf_status": scan_row.spf_status,
                        "dkim_status": scan_row.dkim_status,
                    }
                )
            return output

    def get_summary(self, days: int = 30) -> dict[str, object]:
        with self.session_scope() as session:
            total = int(session.query(func.count(ScanResultRecord.id)).scalar() or 0)
            phishing = int(
                session.query(func.count(ScanResultRecord.id))
                .filter(ScanResultRecord.label == "PHISHING")
                .scalar()
                or 0
            )

            since = utcnow() - timedelta(days=days)
            recent_total = int(
                session.query(func.count(ScanResultRecord.id))
                .filter(ScanResultRecord.scanned_at >= since)
                .scalar()
                or 0
            )
            recent_phishing = int(
                session.query(func.count(ScanResultRecord.id))
                .filter(
                    ScanResultRecord.scanned_at >= since,
                    ScanResultRecord.label == "PHISHING",
                )
                .scalar()
                or 0
            )

            ratio = (phishing / total) if total else 0.0
            recent_ratio = (recent_phishing / recent_total) if recent_total else 0.0

            return {
                "total_scans": total,
                "phishing_count": phishing,
                "phishing_ratio": ratio,
                "recent_total": recent_total,
                "recent_phishing": recent_phishing,
                "recent_ratio": recent_ratio,
                "window_days": days,
            }

    def get_daily_stats(self, days: int = 30) -> list[dict[str, object]]:
        with self.session_scope() as session:
            since = utcnow() - timedelta(days=days)
            day_bucket = func.date(ScanResultRecord.scanned_at)
            rows = (
                session.query(
                    day_bucket.label("day"),
                    func.count(ScanResultRecord.id).label("total"),
                    func.sum(
                        case(
                            (ScanResultRecord.label == "PHISHING", 1),
                            else_=0,
                        )
                    ).label("phishing"),
                )
                .filter(ScanResultRecord.scanned_at >= since)
                .group_by(day_bucket)
                .order_by(day_bucket.asc())
                .all()
            )

            output: list[dict[str, object]] = []
            for day, total, phishing in rows:
                output.append({"day": str(day), "total": int(total or 0), "phishing": int(phishing or 0)})
            return output
