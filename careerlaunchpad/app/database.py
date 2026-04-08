import click
import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    NOT NULL UNIQUE,
            password_hash TEXT    NOT NULL,
            role          TEXT    NOT NULL CHECK(role IN ('admin', 'company', 'student')),
            is_active     INTEGER NOT NULL DEFAULT 1,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

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

    db.execute(
        """
        CREATE TABLE IF NOT EXISTS students (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL UNIQUE,
            department       TEXT,
            cgpa             REAL,
            graduation_year  INTEGER,
            resume_path      TEXT,
            phone            TEXT,
            is_blacklisted   INTEGER NOT NULL DEFAULT 0,
            created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    # Backward-compatible migration for older databases created before
    # is_blacklisted was introduced.
    student_cols = {
        row["name"] for row in db.execute("PRAGMA table_info(students)").fetchall()
    }
    if "is_blacklisted" not in student_cols:
        db.execute(
            "ALTER TABLE students ADD COLUMN is_blacklisted INTEGER NOT NULL DEFAULT 0"
        )

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
            UNIQUE(student_id, drive_id),
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
            FOREIGN KEY (drive_id)   REFERENCES placement_drives(id) ON DELETE CASCADE
        )
        """
    )

    db.commit()
    click.echo("Database tables created successfully.")


@click.command("init-db")
def init_db_command():
    init_db()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
