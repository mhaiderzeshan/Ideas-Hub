import asyncio
import logging
from typing import Dict
from functools import lru_cache

import brevo_python
from brevo_python.rest import ApiException

from tenacity import retry, stop_after_attempt, wait_exponential
from jinja2 import Template
from app.core.config import settings

# Logger setup
logger = logging.getLogger(__name__)


class EmailService:
    """Production-ready email service using Brevo API with retry logic and templates"""

    def __init__(self):
        """Initialize the Brevo API client from environment variables"""
        # SMTP settings with Brevo API settings ---
        self.api_key = settings.BREVO_API_KEY.get_secret_value()
        self.from_email = settings.EMAIL_FROM
        self.frontend_url = settings.FRONTEND_URL
        self.from_name = settings.EMAIL_FROM_NAME

        if not all([self.api_key, self.from_email, self.frontend_url]):
            raise ValueError(
                "BREVO_API_KEY, FROM_EMAIL, and FRONTEND_URL must be set.")

        # Configure Brevo API client
        configuration = brevo_python.Configuration()
        configuration.api_key['api-key'] = self.api_key
        self.api_client = brevo_python.ApiClient(configuration)
        self.transactional_api = brevo_python.TransactionalEmailsApi(
            self.api_client)

        # Kept for potential future use
        self._templates_cache: Dict[str, Template] = {}

    @retry(
        stop=stop_after_attempt(3),
        # Adjusted wait slightly
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def send_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: str
    ) -> bool:
        """
        Send password reset email via Brevo with retry logic.
        """
        try:
            reset_url = f"{self.frontend_url}/auth/reset-password?token={reset_token}"
            html_content = self._render_reset_template(
                user_name=user_name,
                reset_url=reset_url
            )

            await self._send_email(
                to_email=to_email,
                subject="Password Reset Request - Ideas Hub",
                html_content=html_content,
                recipient_name=user_name
            )

            logger.info(
                f"Password reset email queued for {to_email} via Brevo.")
            return True

        # Catching Brevo's specific exception to trigger retry ---
        except ApiException as e:
            logger.error(
                f"Brevo API error sending email to {to_email}: {e.reason} - {e.body}")
            raise  # Re-raising the exception is crucial for tenacity to retry

        except Exception as e:
            logger.error(
                f"Unexpected error preparing email for {to_email}: {str(e)}")
            return False

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        recipient_name: str
    ) -> None:
        """
        Internal method to send an email using the Brevo API.
        This runs the blocking SDK call in a thread pool to not block asyncio.
        """
        sender = {"name": self.from_name, "email": self.from_email}
        to = [{"email": to_email, "name": recipient_name}]

        send_smtp_email = brevo_python.SendSmtpEmail(
            to=to,
            sender=sender,
            subject=subject,
            html_content=html_content
        )

        # Using run_in_executor to handle the blocking nature of the SDK call gracefully
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,  # Use the default thread pool executor
            self.transactional_api.send_transac_email,
            send_smtp_email
        )

    def _render_reset_template(self, **kwargs) -> str:
        """Render email template with variables"""
        template_str = """
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #2c3e50; text-align: center;">Password Reset Request</h2>
                    <p>Hello {{ user_name }},</p>
                    <p>We received a request to reset your password for your Ideas Hub account. Please click the button below to proceed.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{{ reset_url }}" 
                           style="background-color: #3498db; color: white; padding: 12px 30px; 
                                  text-decoration: none; border-radius: 5px; display: inline-block;">
                            Reset Your Password
                        </a>
                    </div>
                    <p><strong>This link is valid for 1 hour.</strong> If you did not request a password reset, please ignore this email.</p>
                    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
                    <p style="font-size: 0.9em; color: #777;">Thank you,<br>The Ideas Hub Team</p>
                </div>
            </body>
        </html>
        """
        return Template(template_str).render(**kwargs)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_url: str
    ) -> bool:
        """Send verification email via Brevo with retry logic."""
        try:
            html_content = self._render_verification_template(
                user_name=user_name,
                verification_url=verification_url
            )

            await self._send_email(
                to_email=to_email,
                subject="Verify Your Email - Ideas Hub",
                html_content=html_content,
                recipient_name=user_name
            )

            logger.info(
                f"Verification email queued for {to_email} via Brevo.")
            return True

        except ApiException as e:
            logger.error(
                f"Brevo API error sending verification email to {to_email}: {e.reason} - {e.body}")
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error preparing verification email for {to_email}: {str(e)}")
            return False

    def _render_verification_template(self, **kwargs) -> str:
        """Render verification email template."""
        template_str = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
                .button { display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
                .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Welcome to Ideas Hub, {{ user_name }}!</h2>
                <p>Thank you for signing up. To complete your registration, please verify your email address.</p>
                <p><a href="{{ verification_url }}" class="button">Verify Email Address</a></p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #007bff;">{{ verification_url }}</p>
                <div class="footer">
                    <p>This verification link will expire in 24 hours.</p>
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return Template(template_str).render(**kwargs)

    async def send_welcome_email(
        self,
        to_email: str,
        user_name: str
    ) -> bool:
        """Send welcome email to new users via Brevo"""
        try:
            html_content = self._render_welcome_template(user_name=user_name)

            await self._send_email(
                to_email=to_email,
                subject="Welcome to Ideas Hub!",
                html_content=html_content,
                recipient_name=user_name
            )

            logger.info(f"Welcome email queued for {to_email} via Brevo.")
            return True

        except Exception as e:
            logger.error(
                f"Failed to send welcome email to {to_email}: {str(e)}")
            return False

    def _render_welcome_template(self, **kwargs) -> str:
        template_str = """
        <html><body>... (your welcome template) ...</body></html>
        """
        return Template(template_str).render(**kwargs)


@lru_cache()
def get_email_service() -> EmailService:
    """Get cached email service instance"""
    return EmailService()
