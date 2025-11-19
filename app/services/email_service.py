# app/services/email_service.py
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from app.core.config import settings


class EmailService:
    def __init__(self):
        configuration = sib_api_v3_sdk.Configuration()
        configuration.api_key['api-key'] = settings.BREVO_API_KEY.get_secret_value()
        self.api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
            sib_api_v3_sdk.ApiClient(configuration)
        )

    def send_email(self, to_email: str, to_name: str, subject: str, html_content: str):
        """Send email using Brevo (synchronous - runs in background task)"""
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=[{"email": to_email, "name": to_name}],
            sender={"email": settings.EMAIL_FROM,
                    "name": settings.EMAIL_FROM_NAME},
            subject=subject,
            html_content=html_content
        )

        try:
            api_response = self.api_instance.send_transac_email(
                send_smtp_email)
            return api_response
        except ApiException as e:
            print(f"Exception when sending email: {e}")
            raise

    @staticmethod
    def send_verification_email(to_email: str, to_name: str, verification_url: str):
        """Send verification email"""
        email_service = EmailService()

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Welcome to Ideas Hub, {to_name}!</h2>
                <p>Thank you for signing up. To complete your registration, please verify your email address.</p>
                <p>
                    <a href="{verification_url}" class="button">Verify Email Address</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #007bff;">{verification_url}</p>
                <div class="footer">
                    <p>This verification link will expire in 24 hours.</p>
                    <p>If you didn't create an account, you can safely ignore this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return email_service.send_email(
            to_email=to_email,
            to_name=to_name,
            subject="Verify Your Email - Ideas Hub",
            html_content=html_content
        )

    @staticmethod
    def send_password_reset_email(to_email: str, to_name: str, reset_url: str):
        """Send password reset email"""
        email_service = EmailService()

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 24px;
                    background-color: #dc3545;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>Password Reset Request</h2>
                <p>Hi {to_name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <p>
                    <a href="{reset_url}" class="button">Reset Password</a>
                </p>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #007bff;">{reset_url}</p>
                <div class="footer">
                    <p>This reset link will expire in 1 hour.</p>
                    <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
                </div>
            </div>
        </body>
        </html>
        """

        return email_service.send_email(
            to_email=to_email,
            to_name=to_name,
            subject="Password Reset - Ideas Hub",
            html_content=html_content
        )
