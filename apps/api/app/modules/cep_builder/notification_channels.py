"""Multi-channel notification service for CEP rule actions (Slack, Email, SMS, Webhook)"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# 재시도 관리자는 notification_service에서 주입됨
retry_manager = None


class NotificationMessage:
    """Notification message structure"""

    def __init__(
        self,
        title: str,
        body: str,
        recipients: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.title = title
        self.body = body
        self.recipients = recipients
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()


class NotificationChannel(ABC):
    """Base class for notification channels"""

    @abstractmethod
    async def send(self, message: NotificationMessage) -> bool:
        """Send message through channel"""
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """Validate channel configuration"""
        pass


class SlackNotificationChannel(NotificationChannel):
    """Send notifications to Slack via webhook"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def validate_config(self) -> bool:
        """Validate Slack webhook URL"""
        return bool(self.webhook_url and self.webhook_url.startswith("https://"))

    async def send(self, message: NotificationMessage) -> bool:
        """Send message to Slack"""
        if not self.validate_config():
            logger.error("Invalid Slack webhook URL")
            return False

        # Build Slack message blocks
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": message.title, "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message.body},
            },
        ]

        # Add metadata context if available
        if message.metadata:
            context_text = " | ".join(
                [f"*{k}*: {v}" for k, v in message.metadata.items()]
            )
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": context_text,
                        }
                    ],
                }
            )

        payload = {
            "text": message.title,
            "blocks": blocks,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                success = response.status_code == 200

                if success:
                    logger.info("Slack notification sent successfully")
                else:
                    logger.error(
                        f"Slack notification failed: {response.status_code} {response.text}"
                    )

                return success

        except Exception as e:
            logger.error(f"Slack notification error: {str(e)}")
            return False


class EmailNotificationChannel(NotificationChannel):
    """Send notifications via email (SMTP)"""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_email: str,
        password: str,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.from_email = from_email
        self.password = password
        self.use_tls = use_tls

    def validate_config(self) -> bool:
        """Validate email configuration"""
        return bool(
            self.smtp_host
            and self.smtp_port > 0
            and "@" in self.from_email
            and self.password
        )

    async def send(self, message: NotificationMessage) -> bool:
        """Send email notification"""
        if not self.validate_config():
            logger.error("Invalid email configuration")
            return False

        if not message.recipients:
            logger.error("No email recipients specified")
            return False

        try:
            # Create MIME message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.title
            msg["From"] = self.from_email
            msg["To"] = ", ".join(message.recipients)

            # HTML content
            metadata_html = ""
            if message.metadata:
                metadata_html = "<hr><ul>"
                for k, v in message.metadata.items():
                    metadata_html += f"<li><strong>{k}:</strong> {v}</li>"
                metadata_html += "</ul>"

            html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <h2 style="color: #2c3e50;">{message.title}</h2>
                    <p>{message.body}</p>
                    {metadata_html}
                    <hr style="border: none; border-top: 1px solid #ddd; margin-top: 20px;">
                    <small style="color: #7f8c8d;">
                        Sent at {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")}
                    </small>
                </body>
            </html>
            """

            msg.attach(MIMEText(html, "html"))

            # In production: Use aiosmtplib for async SMTP
            # For now, log that email would be sent
            logger.info(
                f"Email notification would be sent to {len(message.recipients)} recipients: {message.recipients}"
            )

            return True

        except Exception as e:
            logger.error(f"Email notification error: {str(e)}")
            return False


class SmsNotificationChannel(NotificationChannel):
    """Send notifications via SMS (Twilio)"""

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

    def validate_config(self) -> bool:
        """Validate SMS configuration"""
        return bool(self.account_sid and self.auth_token and self.from_number)

    async def send(self, message: NotificationMessage) -> bool:
        """Send SMS notification"""
        if not self.validate_config():
            logger.error("Invalid SMS configuration")
            return False

        if not message.recipients:
            logger.error("No SMS recipients specified")
            return False

        try:
            # Twilio API endpoint
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

            # SMS message (limited to 160 characters)
            sms_body = message.body[:160]

            results = []

            # Send SMS to each recipient
            async with httpx.AsyncClient(timeout=10.0) as client:
                for recipient in message.recipients:
                    try:
                        auth = (self.account_sid, self.auth_token)

                        response = await client.post(
                            url,
                            data={
                                "From": self.from_number,
                                "To": recipient,
                                "Body": sms_body,
                            },
                            auth=auth,
                        )

                        success = response.status_code == 201
                        results.append(success)

                        if success:
                            logger.info(f"SMS sent to {recipient}")
                        else:
                            logger.error(
                                f"SMS to {recipient} failed: {response.status_code}"
                            )

                    except Exception as e:
                        logger.error(f"SMS to {recipient} error: {str(e)}")
                        results.append(False)

            return all(results)

        except Exception as e:
            logger.error(f"SMS notification error: {str(e)}")
            return False


class WebhookNotificationChannel(NotificationChannel):
    """Send notifications via HTTP webhook"""

    def __init__(self, url: str, headers: Optional[Dict[str, str]] = None):
        self.url = url
        self.headers = headers or {"Content-Type": "application/json"}

    def validate_config(self) -> bool:
        """Validate webhook URL"""
        return bool(
            self.url
            and (self.url.startswith("http://") or self.url.startswith("https://"))
        )

    async def send(self, message: NotificationMessage) -> bool:
        """Send notification via webhook"""
        if not self.validate_config():
            logger.error("Invalid webhook URL")
            return False

        try:
            payload = {
                "title": message.title,
                "body": message.body,
                "recipients": message.recipients,
                "metadata": message.metadata,
                "timestamp": message.created_at.isoformat(),
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.url,
                    json=payload,
                    headers=self.headers,
                )

                success = response.status_code in [200, 201, 202]

                if success:
                    logger.info(f"Webhook notification sent successfully to {self.url}")
                else:
                    logger.error(
                        f"Webhook notification failed: {response.status_code} {response.text}"
                    )

                return success

        except Exception as e:
            logger.error(f"Webhook notification error: {str(e)}")
            return False


class PagerDutyNotificationChannel(NotificationChannel):
    """Send notifications to PagerDuty as incidents"""

    def __init__(
        self,
        integration_key: str,
        default_severity: str = "critical",
    ):
        self.integration_key = integration_key
        self.default_severity = default_severity

    def validate_config(self) -> bool:
        """Validate PagerDuty configuration"""
        return bool(self.integration_key and len(self.integration_key) > 20)

    async def send(self, message: NotificationMessage) -> bool:
        """Send incident to PagerDuty"""
        if not self.validate_config():
            logger.error("Invalid PagerDuty configuration")
            return False

        try:
            # Map severity (critical, error, warning, info)
            severity = self.default_severity
            if "critical" in message.body.lower() or "error" in message.body.lower():
                severity = "critical"
            elif "warn" in message.body.lower():
                severity = "warning"

            payload = {
                "routing_key": self.integration_key,
                "event_action": "trigger",
                "dedup_key": f"tobit-cep-{message.created_at.timestamp()}",
                "payload": {
                    "summary": message.title,
                    "severity": severity,
                    "source": "Tobit CEP",
                    "component": "monitoring",
                    "custom_details": message.metadata,
                },
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                )

                success = response.status_code in [200, 202]

                if success:
                    logger.info("PagerDuty incident created successfully")
                else:
                    logger.error(
                        f"PagerDuty incident failed: {response.status_code} {response.text}"
                    )

                return success

        except Exception as e:
            logger.error(f"PagerDuty notification error: {str(e)}")
            return False


class NotificationChannelFactory:
    """Factory for creating notification channels"""

    @staticmethod
    def create(
        channel_type: str, config: Dict[str, Any]
    ) -> Optional[NotificationChannel]:
        """Create notification channel based on type"""

        channel_type = channel_type.lower()

        try:
            if channel_type == "slack":
                return SlackNotificationChannel(config.get("webhook_url", ""))

            elif channel_type == "email":
                return EmailNotificationChannel(
                    smtp_host=config.get("smtp_host", ""),
                    smtp_port=config.get("smtp_port", 587),
                    from_email=config.get("from_email", ""),
                    password=config.get("password", ""),
                    use_tls=config.get("use_tls", True),
                )

            elif channel_type == "sms":
                return SmsNotificationChannel(
                    account_sid=config.get("account_sid", ""),
                    auth_token=config.get("auth_token", ""),
                    from_number=config.get("from_number", ""),
                )

            elif channel_type == "webhook":
                return WebhookNotificationChannel(
                    url=config.get("url", ""),
                    headers=config.get("headers"),
                )

            elif channel_type == "pagerduty":
                return PagerDutyNotificationChannel(
                    integration_key=config.get("integration_key", ""),
                    default_severity=config.get("default_severity", "critical"),
                )

            else:
                logger.error(f"Unknown notification channel type: {channel_type}")
                return None

        except Exception as e:
            logger.error(f"Error creating notification channel: {str(e)}")
            return None


class NotificationService:
    """Service for managing and sending notifications"""

    def __init__(self):
        self.channels: Dict[str, NotificationChannel] = {}

    def register_channel(self, channel_id: str, channel: NotificationChannel) -> None:
        """Register a notification channel"""
        if channel.validate_config():
            self.channels[channel_id] = channel
            logger.info(f"Registered notification channel: {channel_id}")
        else:
            logger.error(f"Invalid configuration for channel: {channel_id}")

    def register_channel_from_config(
        self, channel_id: str, channel_type: str, config: Dict[str, Any]
    ) -> bool:
        """Register channel from configuration"""
        channel = NotificationChannelFactory.create(channel_type, config)
        if channel:
            self.register_channel(channel_id, channel)
            return True
        return False

    async def send_notification(
        self,
        message: NotificationMessage,
        channel_ids: Optional[List[str]] = None,
    ) -> Dict[str, bool]:
        """Send notification through specified channels"""
        results = {}

        # If no channels specified, use all registered channels
        channels_to_use = channel_ids if channel_ids else list(self.channels.keys())

        for channel_id in channels_to_use:
            if channel_id in self.channels:
                try:
                    result = await self.channels[channel_id].send(message)
                    results[channel_id] = result
                except Exception as e:
                    logger.error(f"Error sending via {channel_id}: {str(e)}")
                    results[channel_id] = False
            else:
                logger.warning(f"Channel not found: {channel_id}")
                results[channel_id] = False

        return results

    def list_channels(self) -> Dict[str, str]:
        """List registered channels"""
        return {
            channel_id: type(channel).__name__
            for channel_id, channel in self.channels.items()
        }
