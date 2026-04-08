from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="templates")

# Routes will be added in Phase 3