from flask import Blueprint


student_bp = Blueprint("student", __name__, url_prefix="/student")


@student_bp.route("/")
def dashboard():
    return "Student routes stub"
