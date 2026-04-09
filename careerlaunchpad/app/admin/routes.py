from math import ceil

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.database import get_db

admin_bp = Blueprint("admin", __name__, template_folder="templates")


def _admin_required():
    if current_user.role != "admin":
        flash("Admin access required.", "danger")
        return False
    return True


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    stats = {
        "students": db.execute("SELECT COUNT(*) AS cnt FROM students").fetchone()["cnt"],
        "companies": db.execute("SELECT COUNT(*) AS cnt FROM companies").fetchone()["cnt"],
        "drives": db.execute("SELECT COUNT(*) AS cnt FROM placement_drives").fetchone()["cnt"],
        "applications": db.execute("SELECT COUNT(*) AS cnt FROM applications").fetchone()["cnt"],
    }

    drive_rows = db.execute(
        """
        SELECT d.job_title, d.drive_name, COUNT(a.id) AS applicant_count
        FROM placement_drives d
        LEFT JOIN applications a ON a.drive_id = d.id
        GROUP BY d.id
        ORDER BY applicant_count DESC, d.created_at DESC
        LIMIT 7
        """
    ).fetchall()

    status_rows = db.execute(
        "SELECT status, COUNT(*) AS cnt FROM applications GROUP BY status"
    ).fetchall()

    drive_created_rows = db.execute(
        """
        SELECT substr(created_at, 1, 7) AS month, COUNT(*) AS cnt
        FROM placement_drives
        GROUP BY substr(created_at, 1, 7)
        ORDER BY month ASC
        """
    ).fetchall()

    chart_data = {
        "drive_labels": [row["drive_name"] or row["job_title"] for row in drive_rows],
        "drive_counts": [row["applicant_count"] for row in drive_rows],
        "status_labels": [row["status"] for row in status_rows],
        "status_counts": [row["cnt"] for row in status_rows],
        "months": [row["month"] for row in drive_created_rows],
        "month_counts": [row["cnt"] for row in drive_created_rows],
    }
    return render_template("admin/dashboard.html", stats=stats, chart_data=chart_data)


@admin_bp.route("/companies")
@login_required
def companies():
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    rows = db.execute(
        """
        SELECT c.*, u.email, u.is_active
        FROM companies c
        JOIN users u ON c.user_id = u.id
        ORDER BY c.created_at DESC
        """
    ).fetchall()
    return render_template("admin/companies.html", companies=rows)


@admin_bp.route("/companies/<int:company_id>/approve", methods=["POST"])
@login_required
def approve_company(company_id):
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    db.execute(
        "UPDATE companies SET approval_status = 'approved' WHERE id = ?",
        (company_id,),
    )
    db.commit()
    flash("Company approved.", "success")
    return redirect(url_for("admin.companies"))


@admin_bp.route("/companies/<int:company_id>/reject", methods=["POST"])
@login_required
def reject_company(company_id):
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    db.execute(
        "UPDATE companies SET approval_status = 'rejected' WHERE id = ?",
        (company_id,),
    )
    db.commit()
    flash("Company rejected.", "warning")
    return redirect(url_for("admin.companies"))


@admin_bp.route("/companies/<int:company_id>/blacklist", methods=["POST"])
@login_required
def blacklist_company(company_id):
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    company = db.execute("SELECT user_id FROM companies WHERE id = ?", (company_id,)).fetchone()
    if not company:
        flash("Company not found.", "danger")
        return redirect(url_for("admin.companies"))

    db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (company["user_id"],))
    db.execute("UPDATE companies SET approval_status = 'rejected' WHERE id = ?", (company_id,))
    db.execute(
        "UPDATE placement_drives SET status = 'closed' WHERE company_id = ?",
        (company_id,),
    )
    db.commit()
    flash("Company blacklisted and drives closed.", "warning")
    return redirect(url_for("admin.companies"))


@admin_bp.route("/students")
@login_required
def students():
    if not _admin_required():
        return redirect(url_for("auth.login"))

    q = request.args.get("q", "").strip()
    db = get_db()

    if q:
        rows = db.execute(
            """
            SELECT s.*, u.name, u.email, u.is_active
            FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE u.name LIKE ? OR CAST(s.id AS TEXT) LIKE ?
            ORDER BY s.created_at DESC
            """,
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT s.*, u.name, u.email, u.is_active
            FROM students s
            JOIN users u ON s.user_id = u.id
            ORDER BY s.created_at DESC
            """
        ).fetchall()

    return render_template("admin/students.html", students=rows, q=q)


@admin_bp.route("/students/<int:student_id>/blacklist", methods=["POST"])
@login_required
def blacklist_student(student_id):
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    student = db.execute("SELECT user_id FROM students WHERE id = ?", (student_id,)).fetchone()
    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("admin.students"))

    db.execute("UPDATE students SET is_blacklisted = 1 WHERE id = ?", (student_id,))
    db.execute("UPDATE users SET is_active = 0 WHERE id = ?", (student["user_id"],))
    db.commit()
    flash("Student blacklisted.", "warning")
    return redirect(url_for("admin.students"))


@admin_bp.route("/drives")
@login_required
def drives():
    if not _admin_required():
        return redirect(url_for("auth.login"))

    status = request.args.get("status", "").strip().lower()
    db = get_db()

    base_query = """
        SELECT d.*, c.company_name
        FROM placement_drives d
        JOIN companies c ON d.company_id = c.id
    """

    if status in {"pending", "approved", "closed", "rejected"}:
        rows = db.execute(
            base_query + " WHERE d.status = ? ORDER BY d.created_at DESC",
            (status,),
        ).fetchall()
    else:
        rows = db.execute(base_query + " ORDER BY d.created_at DESC").fetchall()

    return render_template("admin/drives.html", drives=rows, status=status)


@admin_bp.route("/drives/<int:drive_id>/approve", methods=["POST"])
@login_required
def approve_drive(drive_id):
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    db.execute("UPDATE placement_drives SET status = 'approved' WHERE id = ?", (drive_id,))
    db.commit()
    flash("Drive approved.", "success")
    return redirect(url_for("admin.drives"))


@admin_bp.route("/drives/<int:drive_id>/reject", methods=["POST"])
@login_required
def reject_drive(drive_id):
    if not _admin_required():
        return redirect(url_for("auth.login"))

    db = get_db()
    db.execute("UPDATE placement_drives SET status = 'rejected' WHERE id = ?", (drive_id,))
    db.commit()
    flash("Drive rejected.", "warning")
    return redirect(url_for("admin.drives"))


@admin_bp.route("/applications")
@login_required
def applications():
    if not _admin_required():
        return redirect(url_for("auth.login"))

    page = request.args.get("page", 1, type=int)
    page_size = 10
    offset = (max(page, 1) - 1) * page_size

    db = get_db()
    total = db.execute("SELECT COUNT(*) AS cnt FROM applications").fetchone()["cnt"]
    rows = db.execute(
        """
        SELECT a.*, u.name AS student_name, u.email AS student_email,
               d.drive_name, d.job_title, c.company_name
        FROM applications a
        JOIN students s ON a.student_id = s.id
        JOIN users u ON s.user_id = u.id
        JOIN placement_drives d ON a.drive_id = d.id
        JOIN companies c ON d.company_id = c.id
        ORDER BY a.applied_at DESC
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    ).fetchall()

    total_pages = max(1, ceil(total / page_size))
    page = min(max(1, page), total_pages)

    return render_template(
        "admin/applications.html",
        applications=rows,
        page=page,
        total_pages=total_pages,
    )