from datetime import date, datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.database import get_db
from app.models import Company

company_bp = Blueprint("company", __name__, template_folder="templates")


def _company_required():
    if current_user.role != "company":
        flash("Company access required.", "danger")
        return False
    return True


def _current_company():
    return Company.get_by_user_id(current_user.id)


def _is_editable_drive_status(status):
    return status not in {"closed", "rejected"}


def _deadline_is_passed(deadline_value):
    if not deadline_value:
        return False
    try:
        if isinstance(deadline_value, datetime):
            return deadline_value.date() < date.today()
        if isinstance(deadline_value, date):
            return deadline_value < date.today()
        return str(deadline_value) < date.today().isoformat()
    except Exception:
        return False


@company_bp.route("/dashboard")
@login_required
def dashboard():
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    rows = db.execute(
        """
        SELECT d.*, COUNT(a.id) AS applicant_count
        FROM placement_drives d
        LEFT JOIN applications a ON a.drive_id = d.id
        WHERE d.company_id = ?
        GROUP BY d.id
        ORDER BY d.created_at DESC
        """,
        (company.id,),
    ).fetchall()

    today = date.today().isoformat()
    upcoming = []
    closed = []
    for d in rows:
        is_closed = d["status"] in {"closed", "rejected"}
        if _deadline_is_passed(d["application_deadline"]):
            is_closed = True
        if is_closed:
            closed.append(d)
        else:
            upcoming.append(d)

    return render_template(
        "company/dashboard.html",
        company=company,
        upcoming_drives=upcoming,
        closed_drives=closed,
    )


@company_bp.route("/drives/create", methods=["GET", "POST"])
@login_required
def create_drive():
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    if company.approval_status != "approved":
        flash("Only approved companies can create drives.", "warning")
        return redirect(url_for("company.dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        eligibility = request.form.get("eligibility", "").strip()
        deadline = request.form.get("deadline", "").strip()

        if not title:
            flash("Title is required.", "danger")
            return render_template("company/drive_form.html", mode="create", drive=None)

        db = get_db()
        db.execute(
            """
            INSERT INTO placement_drives
            (company_id, job_title, drive_name, job_description, eligibility, application_deadline, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                company.id,
                title,
                title,
                description or None,
                eligibility or None,
                deadline or None,
            ),
        )
        db.commit()
        flash("Drive created and sent for approval.", "success")
        return redirect(url_for("company.dashboard"))

    return render_template("company/drive_form.html", mode="create", drive=None)


@company_bp.route("/drives/<int:drive_id>/edit", methods=["GET", "POST"])
@login_required
def edit_drive(drive_id):
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    drive = db.execute(
        "SELECT * FROM placement_drives WHERE id = ? AND company_id = ?",
        (drive_id, company.id),
    ).fetchone()
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("company.dashboard"))

    if not _is_editable_drive_status(drive["status"]):
        flash("Closed or rejected drives cannot be edited.", "warning")
        return redirect(url_for("company.dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        eligibility = request.form.get("eligibility", "").strip()
        deadline = request.form.get("deadline", "").strip()

        if not title:
            flash("Title is required.", "danger")
            return render_template("company/drive_form.html", mode="edit", drive=drive)

        db.execute(
            """
            UPDATE placement_drives
            SET job_title = ?, drive_name = ?, job_description = ?, eligibility = ?, application_deadline = ?
            WHERE id = ?
            """,
            (
                title,
                title,
                description or None,
                eligibility or None,
                deadline or None,
                drive_id,
            ),
        )
        db.commit()
        flash("Drive updated.", "success")
        return redirect(url_for("company.dashboard"))

    return render_template("company/drive_form.html", mode="edit", drive=drive)


@company_bp.route("/drives/<int:drive_id>/close", methods=["POST"])
@login_required
def close_drive(drive_id):
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    drive = db.execute(
        "SELECT status FROM placement_drives WHERE id = ? AND company_id = ?",
        (drive_id, company.id),
    ).fetchone()
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("company.dashboard"))

    if not _is_editable_drive_status(drive["status"]):
        flash("Closed or rejected drives cannot be changed.", "warning")
        return redirect(url_for("company.dashboard"))

    db.execute("UPDATE placement_drives SET status = 'closed' WHERE id = ?", (drive_id,))
    db.commit()
    flash("Drive closed.", "info")
    return redirect(url_for("company.dashboard"))


@company_bp.route("/drives/<int:drive_id>/delete", methods=["POST"])
@login_required
def delete_drive(drive_id):
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    drive = db.execute(
        "SELECT id, status FROM placement_drives WHERE id = ? AND company_id = ?",
        (drive_id, company.id),
    ).fetchone()
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("company.dashboard"))

    app_count = db.execute(
        "SELECT COUNT(*) AS cnt FROM applications WHERE drive_id = ?",
        (drive_id,),
    ).fetchone()["cnt"]
    if app_count > 0:
        flash("Cannot delete drive with applications.", "danger")
        return redirect(url_for("company.dashboard"))

    if not _is_editable_drive_status(drive["status"]):
        flash("Closed or rejected drives cannot be deleted.", "warning")
        return redirect(url_for("company.dashboard"))

    db.execute("DELETE FROM placement_drives WHERE id = ?", (drive_id,))
    db.commit()
    flash("Drive deleted.", "success")
    return redirect(url_for("company.dashboard"))


@company_bp.route("/drives/<int:drive_id>/applications")
@login_required
def drive_applications(drive_id):
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    drive = db.execute(
        "SELECT * FROM placement_drives WHERE id = ? AND company_id = ?",
        (drive_id, company.id),
    ).fetchone()
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("company.dashboard"))

    applications = db.execute(
        """
        SELECT a.*, s.resume_path, s.department, s.cgpa, s.graduation_year,
               u.name AS student_name, u.email AS student_email
        FROM applications a
        JOIN students s ON a.student_id = s.id
        JOIN users u ON s.user_id = u.id
        WHERE a.drive_id = ?
        ORDER BY a.applied_at DESC
        """,
        (drive_id,),
    ).fetchall()

    return render_template(
        "company/drive_applications.html",
        drive=drive,
        applications=applications,
    )


@company_bp.route("/applications/<int:application_id>")
@login_required
def application_detail(application_id):
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    app_row = db.execute(
        """
        SELECT a.*, s.resume_path, s.department, s.cgpa, s.graduation_year, s.phone,
               u.name AS student_name, u.email AS student_email,
               d.drive_name, d.job_title, d.status AS drive_status
        FROM applications a
        JOIN students s ON a.student_id = s.id
        JOIN users u ON s.user_id = u.id
        JOIN placement_drives d ON a.drive_id = d.id
        WHERE a.id = ? AND d.company_id = ?
        """,
        (application_id, company.id),
    ).fetchone()

    if not app_row:
        flash("Application not found.", "danger")
        return redirect(url_for("company.dashboard"))

    return render_template("company/application_detail.html", app_row=app_row)


@company_bp.route("/applications/<int:application_id>/update", methods=["POST"])
@login_required
def update_application_status(application_id):
    if not _company_required():
        return redirect(url_for("auth.login"))

    company = _current_company()
    if not company:
        flash("Company profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    new_status = request.form.get("status", "").strip().lower()
    if new_status not in {"shortlisted", "selected", "rejected"}:
        flash("Invalid status update.", "danger")
        return redirect(url_for("company.dashboard"))

    db = get_db()
    app_row = db.execute(
        """
        SELECT a.id, d.status AS drive_status, d.id AS drive_id
        FROM applications a
        JOIN placement_drives d ON a.drive_id = d.id
        WHERE a.id = ? AND d.company_id = ?
        """,
        (application_id, company.id),
    ).fetchone()

    if not app_row:
        flash("Application not found.", "danger")
        return redirect(url_for("company.dashboard"))

    if not _is_editable_drive_status(app_row["drive_status"]):
        flash("Cannot update applications for closed or rejected drives.", "warning")
        return redirect(url_for("company.drive_applications", drive_id=app_row["drive_id"]))

    db.execute(
        "UPDATE applications SET status = ? WHERE id = ?",
        (new_status, application_id),
    )
    db.commit()
    flash("Application status updated.", "success")
    return redirect(url_for("company.application_detail", application_id=application_id))