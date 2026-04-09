from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Company, Student
from app.database import get_db
# from app import csrf

auth_bp = Blueprint(
    "auth", __name__,
    template_folder="templates"
)


def _redirect_dashboard():
    """Send the logged-in user to their role's dashboard."""
    if current_user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    elif current_user.role == "company":
        return redirect(url_for("company.dashboard"))
    else:
        return redirect(url_for("student.dashboard"))


@auth_bp.route("/login", methods=["GET", "POST"])
# @csrf.exempt
def login():
    if current_user.is_authenticated:
        return _redirect_dashboard()

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("auth/login.html")

        user = User.get_by_email(email)

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Your account has been deactivated. Contact the admin.", "danger")
            return render_template("auth/login.html")

        if user.role == "company":
            company = Company.get_by_user_id(user.id)
            if company and company.approval_status == "pending":
                flash("Your company registration is pending admin approval.", "warning")
                return render_template("auth/login.html")
            if company and company.approval_status == "rejected":
                flash("Your company registration was rejected. Contact the admin.", "danger")
                return render_template("auth/login.html")

        login_user(user)
        flash(f"Welcome back, {user.name}!", "success")
        return _redirect_dashboard()

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/register/student", methods=["GET", "POST"])
def register_student():
    if current_user.is_authenticated:
        return _redirect_dashboard()

    if request.method == "POST":
        name          = request.form.get("name", "").strip()
        email         = request.form.get("email", "").strip().lower()
        password      = request.form.get("password", "")
        department    = request.form.get("department", "").strip()
        cgpa_str      = request.form.get("cgpa", "").strip()
        grad_year_str = request.form.get("graduation_year", "").strip()
        phone         = request.form.get("phone", "").strip()

        errors = []
        if not name:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if User.get_by_email(email):
            errors.append("An account with this email already exists.")

        cgpa = None
        if cgpa_str:
            try:
                cgpa = float(cgpa_str)
                if not (0 <= cgpa <= 10):
                    errors.append("CGPA must be between 0 and 10.")
            except ValueError:
                errors.append("CGPA must be a number.")

        grad_year = None
        if grad_year_str:
            try:
                grad_year = int(grad_year_str)
            except ValueError:
                errors.append("Graduation year must be a number.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register_student.html")

        user = User.create(name, email, password, role="student")
        Student.create(
            user_id=user.id,
            department=department or None,
            cgpa=cgpa,
            graduation_year=grad_year,
            phone=phone or None,
        )

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_student.html")


@auth_bp.route("/register/company", methods=["GET", "POST"])
def register_company():
    if current_user.is_authenticated:
        return _redirect_dashboard()

    if request.method == "POST":
        name         = request.form.get("name", "").strip()
        email        = request.form.get("email", "").strip().lower()
        password     = request.form.get("password", "")
        company_name = request.form.get("company_name", "").strip()
        hr_contact   = request.form.get("hr_contact", "").strip()
        website      = request.form.get("website", "").strip()
        description  = request.form.get("description", "").strip()

        errors = []
        if not name:
            errors.append("Contact person name is required.")
        if not email:
            errors.append("Email is required.")
        if not password or len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if not company_name:
            errors.append("Company name is required.")
        if User.get_by_email(email):
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("auth/register_company.html")

        user = User.create(name, email, password, role="company")
        Company.create(
            user_id=user.id,
            company_name=company_name,
            hr_contact=hr_contact or None,
            website=website or None,
            description=description or None,
        )

        flash(
            "Registration submitted! You can log in once the admin approves your account.",
            "success",
        )
        return redirect(url_for("auth.login"))

    return render_template("auth/register_company.html")