"""Database models and session management using SQLAlchemy + SQLite."""

import os
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime,
    create_engine, JSON
)
from sqlalchemy.orm import declarative_base, sessionmaker

DB_PATH = os.path.join(os.path.dirname(__file__), "voicebot.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class AppSettings(Base):
    __tablename__ = "app_settings"

    key = Column(String, primary_key=True)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(String, primary_key=True)
    agent_id = Column(String, nullable=False, index=True)
    agent_name = Column(String, nullable=True)
    status = Column(String, nullable=False)  # initiated, in-progress, processing, done, failed
    call_successful = Column(String, nullable=True)  # success, failure, unknown
    start_time_unix = Column(Integer, nullable=False, index=True)
    call_duration_secs = Column(Integer, nullable=True, default=0)
    message_count = Column(Integer, nullable=True, default=0)
    transcript_summary = Column(Text, nullable=True)
    call_summary_title = Column(String, nullable=True)
    main_language = Column(String, nullable=True)
    direction = Column(String, nullable=True)  # inbound, outbound
    rating = Column(Float, nullable=True)
    tool_names = Column(Text, nullable=True)  # JSON array as text
    conversation_initiation_source = Column(String, nullable=True)

    # Phone numbers from metadata.phone_call
    agent_phone = Column(String, nullable=True)   # agent_number - numer voicebota
    client_phone = Column(String, nullable=True)   # external_number - numer klienta

    # Detailed fields from GET /conversation/{id}
    has_audio = Column(Boolean, nullable=True)
    cost = Column(Integer, nullable=True, default=0)
    termination_reason = Column(String, nullable=True)
    user_id = Column(String, nullable=True)

    # Analysis
    evaluation_criteria_results = Column(Text, nullable=True)  # JSON
    data_collection_results = Column(Text, nullable=True)  # JSON

    # Transcript stored as JSON
    transcript = Column(Text, nullable=True)

    # Metadata
    fetched_at = Column(DateTime, default=datetime.utcnow)
    details_fetched = Column(Boolean, default=False)

    # Month partition for archival (YYYY-MM)
    month_partition = Column(String, nullable=False, index=True)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False)
    sync_type = Column(String, nullable=False)  # manual, scheduled
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    conversations_fetched = Column(Integer, default=0)
    details_fetched = Column(Integer, default=0)
    status = Column(String, default="running")  # running, completed, failed
    error_message = Column(Text, nullable=True)
    period_from = Column(Integer, nullable=True)
    period_to = Column(Integer, nullable=True)


class ArchiveLog(Base):
    __tablename__ = "archive_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month_partition = Column(String, nullable=False)
    agent_id = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    records_count = Column(Integer, default=0)
    archived_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_add_phone_columns()


def _migrate_add_phone_columns():
    """Add phone columns if they don't exist (SQLite migration)."""
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(conversations)")
        columns = {row[1] for row in cursor.fetchall()}

        if "agent_phone" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN agent_phone TEXT")
        if "client_phone" not in columns:
            cursor.execute("ALTER TABLE conversations ADD COLUMN client_phone TEXT")

        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
