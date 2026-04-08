from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask import redirect, url_for

admin_bp = Blueprint("admin", __name__, template_folder="templates")

@admin_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "admin":
        return redirect(url_for("auth.login"))
    # Full dashboard built in Phase 3
    return "<h2>Admin Dashboard — Phase 3 coming soon</h2><a href='/logout'>Logout</a>"