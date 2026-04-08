from app import create_app
from app.database import init_db


def main():
    app = create_app()
    with app.app_context():
        init_db()
        print("Seed script scaffold ready. Add seed data here when needed.")


if __name__ == "__main__":
    main()
