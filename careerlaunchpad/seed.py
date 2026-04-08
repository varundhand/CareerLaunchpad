"""
seed.py
-------
Run once to initialise the database and create the admin superuser.

    python seed.py

Safe to re-run: tables use CREATE TABLE IF NOT EXISTS,
and the admin insert is skipped if the email already exists.
"""

from app import create_app
from app.database import init_db, get_db
from app.models import User


def seed_admin():
    db = get_db()

    # Check if admin already exists
    existing = db.execute(
        "SELECT id FROM users WHERE role = 'admin' LIMIT 1"
    ).fetchone()

    if existing:
        print("ℹ️   Admin user already exists — skipping seed.")
        return

    # Create admin user
    # Change these credentials before deploying!
    User.create(
        name="Admin",
        email="admin@careerlaunchpad.com",
        password="admin123",
        role="admin",
    )
    print("✅  Admin user created.")
    print("    Email   : admin@careerlaunchpad.com")
    print("    Password: admin123")
    print("    ⚠️  Change the password before going live!")


if __name__ == "__main__":
    app = create_app("development")
    with app.app_context():
        print("🔧  Initialising database...")
        init_db()
        print("🌱  Seeding admin user...")
        seed_admin()
        print("\n🚀  Setup complete. Run with:  python run.py")