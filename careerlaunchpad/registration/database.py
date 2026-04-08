import sqlite3
import click
from flask import current_app, g


def get_db():
    """Open a new database connection if there is none for the current request context."""
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row  # rows behave like dicts
        g.db.execute("PRAGMA foreign_keys = ON")  # enforce FK constraints
    return g.db


def close_db(e=None):
    """Close the database connection at the end of a request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create all tables. Safe to call multiple times (IF NOT EXISTS)."""
    db = get_db()

    # ------------------------------------------------------------------ #
    # 1. USERS  — base authentication record for all roles                #
    # ------------------------------------------------------------------ #
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK(role IN ('admin', 'company', 'student')),
            is_active     INTEGER NOT NULL DEFAULT 1,   -- 0 = deactivated / blacklisted
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # ------------------------------------------------------------------ #
    # 2. COMPANIES — extended profile for company role                    #
    # ------------------------------------------------------------------ #
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL UNIQUE,
            company_name    TEXT    NOT NULL,
            hr_contact      TEXT,
            website         TEXT,
            description     TEXT,
            approval_status TEXT    NOT NULL DEFAULT 'pending'
                                    CHECK(approval_status IN ('pending', 'approved', 'rejected')),
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    # ------------------------------------------------------------------ #
    # 3. STUDENTS — extended profile for student role                     #
    # ------------------------------------------------------------------ #
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL UNIQUE,
            department       TEXT,
            cgpa             REAL,
            graduation_year  INTEGER,
            resume_path      TEXT,   -- relative path inside static/resumes/
            phone            TEXT,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    # ------------------------------------------------------------------ #
    # 4. PLACEMENT DRIVES — job postings created by companies             #
    # ------------------------------------------------------------------ #
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS placement_drives (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id        INTEGER NOT NULL,
            job_title         TEXT    NOT NULL,
            drive_name        TEXT    NOT NULL,
            job_description   TEXT,
            eligibility       TEXT,
            salary            TEXT,
            location          TEXT,
            interview_type    TEXT    DEFAULT 'In-person',
            application_deadline DATE,
            status            TEXT    NOT NULL DEFAULT 'pending'
                                      CHECK(status IN ('pending', 'approved', 'closed', 'rejected')),
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
        )
        """
    )

    # ------------------------------------------------------------------ #
    # 5. APPLICATIONS — student applications to placement drives          #
    # ------------------------------------------------------------------ #
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS applications (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id    INTEGER NOT NULL,
            drive_id      INTEGER NOT NULL,
            applied_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status        TEXT    NOT NULL DEFAULT 'applied'
                                  CHECK(status IN ('applied', 'shortlisted', 'selected', 'rejected')),
            remark        TEXT,
            UNIQUE(student_id, drive_id),   -- prevent duplicate applications
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (drive_id)   REFERENCES placement_drives(id) ON DELETE CASCADE
        )
        """
    )

    db.commit()
    click.echo("✅  All tables created successfully.")


@click.command("init-db")
def init_db_command():
    """Flask CLI command: flask init-db"""
    init_db()


def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)