from flask import Blueprint


company_bp = Blueprint("company", __name__, url_prefix="/company")


@company_bp.route("/")
def dashboard():
    return "Company routes stub"
