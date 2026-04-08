from flask import Blueprint, render_template
from flask_login import login_required, current_user
from flask import redirect, url_for

company_bp = Blueprint("company", __name__, template_folder="templates")

@company_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role != "company":
        return redirect(url_for("auth.login"))
    # Full dashboard built in Phase 4
    return "<h2>Company Dashboard — Phase 4 coming soon</h2><a href='/logout'>Logout</a>"