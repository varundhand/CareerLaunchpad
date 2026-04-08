from flask import Blueprint

company_bp = Blueprint("company", __name__, template_folder="templates")

# Routes will be added in Phase 4