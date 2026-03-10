import os
import warnings

_jwt_secret = os.environ.get("JWT_SECRET", "")
if not _jwt_secret:
    warnings.warn(
        "JWT_SECRET is not set – falling back to an insecure default. "
        "Set the JWT_SECRET environment variable before deploying to production.",
        stacklevel=2,
    )
    _jwt_secret = "dev-secret-change"

JWT_SECRET: str = _jwt_secret
JWT_EXPIRE_MINUTES = int(os.environ.get("JWT_EXPIRE_MINUTES", "1440"))

DB_PATH = os.environ.get("DB_PATH", "backend/app.db")
