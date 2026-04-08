from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask import redirect, url_for

student_bp = Blueprint("student", __name__, template_folder="templates")

@student_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "student":
        return redirect(url_for("auth.login"))
    # Full dashboard built in Phase 5
    return "<h2>Student Dashboard — Phase 5 coming soon</h2><a href='/logout'>Logout</a>"