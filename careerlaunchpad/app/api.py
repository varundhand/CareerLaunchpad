from flask import Blueprint, jsonify
from flask_login import current_user

from app.database import get_db
from app.models import Student

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _role_required(*roles):
    if not current_user.is_authenticated:
        return jsonify({"error": "authentication required"}), 401
    if roles and current_user.role not in roles:
        return jsonify({"error": "forbidden"}), 403
    return None


@api_bp.route("/drives")
def drives():
    guard = _role_required("admin", "company", "student")
    if guard:
        return guard

    db = get_db()
    rows = db.execute(
        """
        SELECT d.id, d.job_title, d.drive_name, d.location, d.salary,
               d.interview_type, d.application_deadline, d.status,
               c.company_name
        FROM placement_drives d
        JOIN companies c ON d.company_id = c.id
        WHERE d.status = 'approved'
        ORDER BY d.created_at DESC
        """
    ).fetchall()
    return jsonify([
        {
            "id": row["id"],
            "job_title": row["job_title"],
            "drive_name": row["drive_name"],
            "location": row["location"],
            "salary": row["salary"],
            "interview_type": row["interview_type"],
            "application_deadline": row["application_deadline"],
            "status": row["status"],
            "company_name": row["company_name"],
        }
        for row in rows
    ])


@api_bp.route("/students")
def student_profile_api():
    guard = _role_required("student")
    if guard:
        return guard

    student = Student.get_by_user_id(current_user.id)
    if not student:
        return jsonify({"error": "student profile not found"}), 404

    db = get_db()
    user = db.execute("SELECT id, name, email, role FROM users WHERE id = ?", (current_user.id,)).fetchone()
    return jsonify(
        {
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
            },
            "student": {
                "id": student.id,
                "department": student.department,
                "cgpa": student.cgpa,
                "graduation_year": student.graduation_year,
                "resume_path": student.resume_path,
                "phone": student.phone,
                "is_blacklisted": getattr(student, "is_blacklisted", 0),
            },
        }
    )


@api_bp.route("/applications")
def applications():
    guard = _role_required("admin", "company", "student")
    if guard:
        return guard

    db = get_db()
    if current_user.role == "student":
        rows = db.execute(
            """
            SELECT a.id, a.status, a.remark, a.applied_at,
                   d.job_title, d.drive_name, c.company_name
            FROM applications a
            JOIN placement_drives d ON a.drive_id = d.id
            JOIN companies c ON d.company_id = c.id
            JOIN students s ON a.student_id = s.id
            WHERE s.user_id = ?
            ORDER BY a.applied_at DESC
            """,
            (current_user.id,),
        ).fetchall()
    elif current_user.role == "company":
        rows = db.execute(
            """
            SELECT a.id, a.status, a.remark, a.applied_at,
                   d.job_title, d.drive_name, c.company_name
            FROM applications a
            JOIN placement_drives d ON a.drive_id = d.id
            JOIN companies c ON d.company_id = c.id
            WHERE d.company_id = (SELECT id FROM companies WHERE user_id = ?)
            ORDER BY a.applied_at DESC
            """,
            (current_user.id,),
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT a.id, a.status, a.remark, a.applied_at,
                   d.job_title, d.drive_name, c.company_name
            FROM applications a
            JOIN placement_drives d ON a.drive_id = d.id
            JOIN companies c ON d.company_id = c.id
            ORDER BY a.applied_at DESC
            """
        ).fetchall()

    return jsonify([
        {
            "id": row["id"],
            "status": row["status"],
            "remark": row["remark"],
            "applied_at": row["applied_at"],
            "job_title": row["job_title"],
            "drive_name": row["drive_name"],
            "company_name": row["company_name"],
        }
        for row in rows
    ])