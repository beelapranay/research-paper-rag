import os

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change")
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))

DB_PATH = os.environ.get("DB_PATH", "backend/app.db")
