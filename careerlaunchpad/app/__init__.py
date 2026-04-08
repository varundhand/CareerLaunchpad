import os
from flask import Flask
from flask_login import LoginManager
from config import config

login_manager = LoginManager()
# login_view will be set in Phase 2 once auth routes exist
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


def create_app(config_name="default"):
    app = Flask(__name__, template_folder="templates")
    app.config.from_object(config[config_name])

    # Ensure the uploads folder exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Flask-Login ────────────────────────────────────────────────────
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.get_by_id(int(user_id))

    # ── Database ───────────────────────────────────────────────────────
    from app.database import init_app as db_init_app
    db_init_app(app)

    # ── Blueprints ─────────────────────────────────────────────────────
    from app.auth.routes    import auth_bp
    from app.admin.routes   import admin_bp
    from app.company.routes import company_bp
    from app.student.routes import student_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp,   url_prefix="/admin")
    app.register_blueprint(company_bp, url_prefix="/company")
    app.register_blueprint(student_bp, url_prefix="/student")

    # ── Root redirect ──────────────────────────────────────────────────
    from flask import redirect

    @app.route("/")
    def index():
        return redirect("/login")

    return app