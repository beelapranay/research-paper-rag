import os
from dotenv import load_dotenv
import resend

load_dotenv()


def send_verification_email(to_email: str, token: str) -> None:
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")

    resend.api_key = api_key

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:8080")
    verify_url = f"{frontend_url}/verify?token={token}"

    resend.Emails.send({
        "from": os.environ.get("RESEND_FROM", "noreply@paper-rag.local"),
        "to": to_email,
        "subject": "Verify your PaperRAG account",
        "html": (
            f"<p>Click to verify your account:</p>"
            f"<p><a href='{verify_url}'>Verify email</a></p>"
        ),
    })
