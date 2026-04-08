"""
models.py
---------
Lightweight model classes built on top of raw sqlite3.
No ORM — just plain Python objects that wrap DB rows and
provide helper class-methods for common queries.

Flask-Login requires a User class with the four properties/methods below.
"""

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.database import get_db


# ======================================================================
# USER  (Flask-Login compatible)
# ======================================================================

class User(UserMixin):
    """Wraps a row from the `users` table."""

    def __init__(self, row):
        self.id            = row["id"]
        self.name          = row["name"]
        self.email         = row["email"]
        self.password_hash = row["password_hash"]
        self.role          = row["role"]
        self.is_active     = bool(row["is_active"])
        self.created_at    = row["created_at"]

    # Flask-Login: is_active property
    @property
    def is_active(self):
        return self._is_active

    @is_active.setter
    def is_active(self, value):
        self._is_active = value

    # ------------------------------------------------------------------ #
    # Password helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def hash_password(password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # ------------------------------------------------------------------ #
    # Queries                                                              #
    # ------------------------------------------------------------------ #

    @classmethod
    def get_by_id(cls, user_id):
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return cls(row) if row else None

    @classmethod
    def get_by_email(cls, email):
        db = get_db()
        row = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return cls(row) if row else None

    @classmethod
    def create(cls, name, email, password, role):
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (name, email, cls.hash_password(password), role),
        )
        db.commit()
        return cls.get_by_email(email)

    @classmethod
    def get_all(cls, role=None):
        db = get_db()
        if role:
            rows = db.execute("SELECT * FROM users WHERE role = ?", (role,)).fetchall()
        else:
            rows = db.execute("SELECT * FROM users").fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def set_active(cls, user_id, active: bool):
        db = get_db()
        db.execute("UPDATE users SET is_active = ? WHERE id = ?", (int(active), user_id))
        db.commit()


# ======================================================================
# COMPANY
# ======================================================================

class Company:
    """Wraps a row from the `companies` table."""

    def __init__(self, row):
        self.id              = row["id"]
        self.user_id         = row["user_id"]
        self.company_name    = row["company_name"]
        self.hr_contact      = row["hr_contact"]
        self.website         = row["website"]
        self.description     = row["description"]
        self.approval_status = row["approval_status"]
        self.created_at      = row["created_at"]

    @classmethod
    def get_by_id(cls, company_id):
        db = get_db()
        row = db.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
        return cls(row) if row else None

    @classmethod
    def get_by_user_id(cls, user_id):
        db = get_db()
        row = db.execute("SELECT * FROM companies WHERE user_id = ?", (user_id,)).fetchone()
        return cls(row) if row else None

    @classmethod
    def create(cls, user_id, company_name, hr_contact=None, website=None, description=None):
        db = get_db()
        db.execute(
            """INSERT INTO companies (user_id, company_name, hr_contact, website, description)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, company_name, hr_contact, website, description),
        )
        db.commit()
        return cls.get_by_user_id(user_id)

    @classmethod
    def get_all(cls, approval_status=None):
        db = get_db()
        if approval_status:
            rows = db.execute(
                "SELECT * FROM companies WHERE approval_status = ?", (approval_status,)
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM companies").fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def search_by_name(cls, query):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM companies WHERE company_name LIKE ?", (f"%{query}%",)
        ).fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def set_approval(cls, company_id, status):
        db = get_db()
        db.execute(
            "UPDATE companies SET approval_status = ? WHERE id = ?", (status, company_id)
        )
        db.commit()

    def update(self, company_name=None, hr_contact=None, website=None, description=None):
        db = get_db()
        db.execute(
            """UPDATE companies SET company_name=?, hr_contact=?, website=?, description=?
               WHERE id=?""",
            (
                company_name or self.company_name,
                hr_contact   or self.hr_contact,
                website      or self.website,
                description  or self.description,
                self.id,
            ),
        )
        db.commit()


# ======================================================================
# STUDENT
# ======================================================================

class Student:
    """Wraps a row from the `students` table."""

    def __init__(self, row):
        self.id              = row["id"]
        self.user_id         = row["user_id"]
        self.department      = row["department"]
        self.cgpa            = row["cgpa"]
        self.graduation_year = row["graduation_year"]
        self.resume_path     = row["resume_path"]
        self.phone           = row["phone"]
        self.created_at      = row["created_at"]

    @classmethod
    def get_by_id(cls, student_id):
        db = get_db()
        row = db.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
        return cls(row) if row else None

    @classmethod
    def get_by_user_id(cls, user_id):
        db = get_db()
        row = db.execute("SELECT * FROM students WHERE user_id = ?", (user_id,)).fetchone()
        return cls(row) if row else None

    @classmethod
    def create(cls, user_id, department=None, cgpa=None, graduation_year=None, phone=None):
        db = get_db()
        db.execute(
            """INSERT INTO students (user_id, department, cgpa, graduation_year, phone)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, department, cgpa, graduation_year, phone),
        )
        db.commit()
        return cls.get_by_user_id(user_id)

    @classmethod
    def get_all(cls):
        db = get_db()
        rows = db.execute("SELECT * FROM students").fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def search(cls, query):
        """Search by name (joins users table) or student id."""
        db = get_db()
        rows = db.execute(
            """SELECT s.* FROM students s
               JOIN users u ON s.user_id = u.id
               WHERE u.name LIKE ? OR CAST(s.id AS TEXT) LIKE ? OR u.email LIKE ?""",
            (f"%{query}%", f"%{query}%", f"%{query}%"),
        ).fetchall()
        return [cls(r) for r in rows]

    def update(self, department=None, cgpa=None, graduation_year=None,
               phone=None, resume_path=None):
        db = get_db()
        db.execute(
            """UPDATE students
               SET department=?, cgpa=?, graduation_year=?, phone=?, resume_path=?
               WHERE id=?""",
            (
                department      or self.department,
                cgpa            if cgpa is not None else self.cgpa,
                graduation_year or self.graduation_year,
                phone           or self.phone,
                resume_path     or self.resume_path,
                self.id,
            ),
        )
        db.commit()


# ======================================================================
# PLACEMENT DRIVE
# ======================================================================

class PlacementDrive:
    """Wraps a row from the `placement_drives` table."""

    def __init__(self, row):
        self.id                   = row["id"]
        self.company_id           = row["company_id"]
        self.job_title            = row["job_title"]
        self.drive_name           = row["drive_name"]
        self.job_description      = row["job_description"]
        self.eligibility          = row["eligibility"]
        self.salary               = row["salary"]
        self.location             = row["location"]
        self.interview_type       = row["interview_type"]
        self.application_deadline = row["application_deadline"]
        self.status               = row["status"]
        self.created_at           = row["created_at"]

    @classmethod
    def get_by_id(cls, drive_id):
        db = get_db()
        row = db.execute(
            "SELECT * FROM placement_drives WHERE id = ?", (drive_id,)
        ).fetchone()
        return cls(row) if row else None

    @classmethod
    def get_by_company(cls, company_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM placement_drives WHERE company_id = ? ORDER BY created_at DESC",
            (company_id,),
        ).fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def get_all_approved(cls):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM placement_drives WHERE status = 'approved' ORDER BY created_at DESC"
        ).fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def get_all(cls):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM placement_drives ORDER BY created_at DESC"
        ).fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def create(cls, company_id, job_title, drive_name, job_description=None,
               eligibility=None, salary=None, location=None,
               interview_type="In-person", application_deadline=None):
        db = get_db()
        db.execute(
            """INSERT INTO placement_drives
               (company_id, job_title, drive_name, job_description, eligibility,
                salary, location, interview_type, application_deadline)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (company_id, job_title, drive_name, job_description, eligibility,
             salary, location, interview_type, application_deadline),
        )
        db.commit()

    @classmethod
    def set_status(cls, drive_id, status):
        db = get_db()
        db.execute(
            "UPDATE placement_drives SET status = ? WHERE id = ?", (status, drive_id)
        )
        db.commit()

    def update(self, job_title=None, drive_name=None, job_description=None,
               eligibility=None, salary=None, location=None,
               interview_type=None, application_deadline=None):
        db = get_db()
        db.execute(
            """UPDATE placement_drives
               SET job_title=?, drive_name=?, job_description=?, eligibility=?,
                   salary=?, location=?, interview_type=?, application_deadline=?
               WHERE id=?""",
            (
                job_title            or self.job_title,
                drive_name           or self.drive_name,
                job_description      or self.job_description,
                eligibility          or self.eligibility,
                salary               or self.salary,
                location             or self.location,
                interview_type       or self.interview_type,
                application_deadline or self.application_deadline,
                self.id,
            ),
        )
        db.commit()

    def applicant_count(self):
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM applications WHERE drive_id = ?", (self.id,)
        ).fetchone()
        return row["cnt"] if row else 0


# ======================================================================
# APPLICATION
# ======================================================================

class Application:
    """Wraps a row from the `applications` table."""

    def __init__(self, row):
        self.id         = row["id"]
        self.student_id = row["student_id"]
        self.drive_id   = row["drive_id"]
        self.applied_at = row["applied_at"]
        self.status     = row["status"]
        self.remark     = row["remark"]

    @classmethod
    def get_by_id(cls, app_id):
        db = get_db()
        row = db.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
        return cls(row) if row else None

    @classmethod
    def get_by_student(cls, student_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM applications WHERE student_id = ? ORDER BY applied_at DESC",
            (student_id,),
        ).fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def get_by_drive(cls, drive_id):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM applications WHERE drive_id = ? ORDER BY applied_at ASC",
            (drive_id,),
        ).fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def get_all(cls):
        db = get_db()
        rows = db.execute(
            "SELECT * FROM applications ORDER BY applied_at DESC"
        ).fetchall()
        return [cls(r) for r in rows]

    @classmethod
    def exists(cls, student_id, drive_id):
        """Return True if the student has already applied to this drive."""
        db = get_db()
        row = db.execute(
            "SELECT id FROM applications WHERE student_id = ? AND drive_id = ?",
            (student_id, drive_id),
        ).fetchone()
        return row is not None

    @classmethod
    def create(cls, student_id, drive_id):
        db = get_db()
        db.execute(
            "INSERT INTO applications (student_id, drive_id) VALUES (?, ?)",
            (student_id, drive_id),
        )
        db.commit()

    @classmethod
    def set_status(cls, app_id, status, remark=None):
        db = get_db()
        db.execute(
            "UPDATE applications SET status = ?, remark = ? WHERE id = ?",
            (status, remark, app_id),
        )
        db.commit()