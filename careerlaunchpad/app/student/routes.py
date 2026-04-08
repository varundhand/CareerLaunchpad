from flask import Blueprint

student_bp = Blueprint("student", __name__, template_folder="templates")

# Routes will be added in Phase 5