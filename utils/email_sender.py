#email_sender.py

import base64
import resend

from config import RESEND_API_KEY


def send_mom_email(
    recipients,
    subject,
    body,
    doc_bytes,
    filename,
):
    resend.api_key = RESEND_API_KEY

    attachment = {
        "filename": filename,
        "content": base64.b64encode(doc_bytes).decode("utf-8"),
    }

    response = resend.Emails.send(
        {
            "from": "Meeting Agent <onboarding@resend.dev>",
            "to": recipients,
            "subject": subject,
            "text": body,
            "attachments": [attachment],
        }
    )

    return response