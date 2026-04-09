import os
import uuid
from datetime import date, datetime

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.database import get_db
from app.models import Student, User

student_bp = Blueprint("student", __name__, template_folder="templates")


def _student_required():
    if current_user.role != "student":
        flash("Student access required.", "danger")
        return False
    return True


def _current_student():
    student = Student.get_by_user_id(current_user.id)
    if student is None:
        student = Student.create(user_id=current_user.id)
    return student


def _allowed_file(filename):
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config.get("ALLOWED_EXTENSIONS", set())


def _resume_too_large(resume_file):
    try:
        current_pos = resume_file.stream.tell()
        resume_file.stream.seek(0, os.SEEK_END)
        size = resume_file.stream.tell()
        resume_file.stream.seek(current_pos, os.SEEK_SET)
        return size > current_app.config.get("MAX_CONTENT_LENGTH", 0)
    except Exception:
        return False


def _is_deadline_over(deadline_value):
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

@student_bp.route("/dashboard")
@login_required
def dashboard():
    if not _student_required():
        return redirect(url_for("auth.login"))

    student = _current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    approved_drives = db.execute(
        """
        SELECT d.*, c.company_name
        FROM placement_drives d
        JOIN companies c ON d.company_id = c.id
        WHERE d.status = 'approved'
        ORDER BY d.created_at DESC
        """
    ).fetchall()

    applied = db.execute(
        """
        SELECT a.*, d.job_title, d.drive_name, c.company_name
        FROM applications a
        JOIN placement_drives d ON a.drive_id = d.id
        JOIN companies c ON d.company_id = c.id
        WHERE a.student_id = ?
        ORDER BY a.applied_at DESC
        """,
        (student.id,),
    ).fetchall()

    applied_drive_ids = {row["drive_id"] for row in applied}
    open_drives = [d for d in approved_drives if not _is_deadline_over(d["application_deadline"])]

    return render_template(
        "student/dashboard.html",
        student=student,
        approved_drives=open_drives,
        applied=applied,
        applied_drive_ids=applied_drive_ids,
    )


@student_bp.route("/drives/<int:drive_id>")
@login_required
def drive_detail(drive_id):
    if not _student_required():
        return redirect(url_for("auth.login"))

    student = _current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    drive = db.execute(
        """
        SELECT d.*
        FROM placement_drives d
        WHERE d.id = ? AND d.status = 'approved'
        """,
        (drive_id,),
    ).fetchone()
    if not drive:
        flash("Drive not found.", "danger")
        return redirect(url_for("student.dashboard"))

    company = db.execute(
        "SELECT * FROM companies WHERE id = ?",
        (drive["company_id"],),
    ).fetchone()

    already_applied = db.execute(
        "SELECT id FROM applications WHERE student_id = ? AND drive_id = ?",
        (student.id, drive_id),
    ).fetchone() is not None

    return render_template(
        "student/drive_detail.html",
        drive=drive,
        company=company,
        already_applied=already_applied,
    )


@student_bp.route("/drives/<int:drive_id>/apply", methods=["POST"])
@login_required
def apply(drive_id):
    if not _student_required():
        return redirect(url_for("auth.login"))

    student = _current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    drive = db.execute(
        "SELECT id, status, application_deadline FROM placement_drives WHERE id = ?",
        (drive_id,),
    ).fetchone()
    if not drive or drive["status"] != "approved":
        flash("This drive is not available for applications.", "warning")
        return redirect(url_for("student.dashboard"))

    if _is_deadline_over(drive["application_deadline"]):
        flash("Application deadline has passed for this drive.", "warning")
        return redirect(url_for("student.drive_detail", drive_id=drive_id))

    exists = db.execute(
        "SELECT id FROM applications WHERE student_id = ? AND drive_id = ?",
        (student.id, drive_id),
    ).fetchone()
    if exists:
        flash("You have already applied to this drive.", "info")
        return redirect(url_for("student.drive_detail", drive_id=drive_id))

    db.execute(
        "INSERT INTO applications (student_id, drive_id, status) VALUES (?, ?, 'applied')",
        (student.id, drive_id),
    )
    db.commit()
    flash("Application submitted successfully.", "success")
    return redirect(url_for("student.history"))


@student_bp.route("/history")
@login_required
def history():
    if not _student_required():
        return redirect(url_for("auth.login"))

    student = _current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    db = get_db()
    history_rows = db.execute(
        """
        SELECT a.*, d.job_title, d.drive_name, d.interview_type, d.salary,
               c.company_name
        FROM applications a
        JOIN placement_drives d ON a.drive_id = d.id
        JOIN companies c ON d.company_id = c.id
        WHERE a.student_id = ?
        ORDER BY a.applied_at DESC
        """,
        (student.id,),
    ).fetchall()

    return render_template("student/history.html", history_rows=history_rows)


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if not _student_required():
        return redirect(url_for("auth.login"))

    student = _current_student()
    if not student:
        flash("Student profile not found.", "danger")
        return redirect(url_for("auth.logout"))

    user = User.get_by_id(current_user.id)
    db = get_db()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        department = request.form.get("department", "").strip()
        cgpa_raw = request.form.get("cgpa", "").strip()
        year_raw = request.form.get("graduation_year", "").strip()
        phone = request.form.get("phone", "").strip()

        errors = []
        if not name:
            errors.append("Name is required.")

        cgpa = None
        if cgpa_raw:
            try:
                cgpa = float(cgpa_raw)
                if not (0 <= cgpa <= 10):
                    errors.append("CGPA must be between 0 and 10.")
            except ValueError:
                errors.append("CGPA must be a number.")

        graduation_year = None
        if year_raw:
            try:
                graduation_year = int(year_raw)
            except ValueError:
                errors.append("Graduation year must be a number.")

        resume_file = request.files.get("resume")
        resume_path = student.resume_path
        if resume_file and resume_file.filename:
            if not _allowed_file(resume_file.filename):
                errors.append("Only PDF resumes are allowed.")
            elif _resume_too_large(resume_file):
                errors.append("Resume must be 5 MB or smaller.")
            else:
                ext = secure_filename(resume_file.filename).rsplit(".", 1)[1].lower()
                filename = f"student_{student.id}_{uuid.uuid4().hex[:8]}.{ext}"
                upload_dir = current_app.config["UPLOAD_FOLDER"]
                os.makedirs(upload_dir, exist_ok=True)
                resume_file.save(os.path.join(upload_dir, filename))
                resume_path = filename

        if errors:
            for err in errors:
                flash(err, "danger")
            # refresh objects for template consistency
            student = _current_student()
            user = User.get_by_id(current_user.id)
            return render_template("student/profile.html", student=student, user=user)

        db.execute("UPDATE users SET name = ? WHERE id = ?", (name, current_user.id))
        db.execute(
            """
            UPDATE students
            SET department = ?, cgpa = ?, graduation_year = ?, phone = ?, resume_path = ?
            WHERE user_id = ?
            """,
            (
                department or None,
                cgpa,
                graduation_year,
                phone or None,
                resume_path,
                current_user.id,
            ),
        )
        db.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("student.profile"))

    return render_template("student/profile.html", student=student, user=user)


@student_bp.route("/resume/<path:filename>")
@login_required
def view_resume(filename):
    if not _student_required():
        return redirect(url_for("auth.login"))

    student = _current_student()
    if not student or not student.resume_path:
        flash("Resume not found.", "danger")
        return redirect(url_for("student.profile"))

    # Students can view only their own uploaded resume file.
    if filename != student.resume_path:
        flash("Access denied for this resume.", "danger")
        return redirect(url_for("student.profile"))

    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)