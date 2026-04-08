from flask import Blueprint

auth_bp = Blueprint("auth", __name__, template_folder="templates")

# Routes will be added in Phase 2