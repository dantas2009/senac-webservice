import os
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from typing import Dict
from dotenv import load_dotenv, find_dotenv


load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
    MAIL_FROM = os.getenv("MAIL_USERNAME"),
    MAIL_PORT = 587,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_FROM_NAME = "Compra Inteligente",
    MAIL_SSL_TLS=False,
    MAIL_STARTTLS=True,
    USE_CREDENTIALS=True,
    TEMPLATE_FOLDER="app/templates"
)

async def recuperar_senha_mail(subject: str, email_to: str, body: Dict):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=body,
        subtype="html"
    )

    fm = FastMail(conf)

    await fm.send_message(message=message, template_name="recuperar-senha.html")
