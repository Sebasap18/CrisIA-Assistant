# app/services/notification_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.domain.interfaces import INotificationService
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class NotificationService(INotificationService):
    """
    Implementación del servicio de notificaciones.
    Soporta envío por correo electrónico vía SMTP y mock para WhatsApp.
    """

    async def send_email(self, to_email: str, subject: str, body: str) -> bool:
        if not settings.SMTP_USER or not settings.SMTP_PASS:
            logger.warning(
                "Credenciales SMTP no configuradas. Mockeando envío de email a %s con asunto '%s'",
                to_email, subject
            )
            logger.info("MOCK EMAIL BODY:\n%s", body)
            return True

        try:
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_USER
            msg['To'] = to_email
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # Usar starttls
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)

            logger.info("Correo enviado exitosamente a %s", to_email)
            return True
        except Exception as e:
            logger.exception("Error enviando correo a %s: %s", to_email, e)
            return False

    async def send_whatsapp(self, to_phone: str, message: str) -> bool:
        """
        Envío de WhatsApp (Mock por ahora, hasta definir proveedor).
        """
        logger.info("Mockeando envío de WhatsApp al número %s", to_phone)
        logger.info("MOCK WHATSAPP MESSAGE:\n%s", message)
        return True
