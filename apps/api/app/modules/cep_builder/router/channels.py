"""Notification channel management endpoints for CEP Builder."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from core.db import get_session
from fastapi import APIRouter, Depends, HTTPException
from schemas.common import ResponseEnvelope
from sqlmodel import Session

from ..crud import (
    list_notification_logs,
    list_notifications,
)

router = APIRouter(prefix="/cep/channels", tags=["cep-channels"])


@router.post("/test")
async def test_notification_channel(
    channel_type: str,
    config: dict = None,
    session: Session = Depends(get_session),
) -> ResponseEnvelope:
    """
    Test a notification channel with sample data.

    Args:
        channel_type: Type of channel (slack, email, sms, webhook, pagerduty)
        config: Channel configuration dict

    Returns:
        Test result with success status and message
    """
    if not config:
        raise HTTPException(status_code=400, detail="Config is required")

    try:
        from ..notification_channels import (
            NotificationChannelFactory,
            NotificationMessage,
        )

        channel = NotificationChannelFactory.create(channel_type, config)
        if not channel:
            raise HTTPException(
                status_code=400, detail=f"Unknown channel type: {channel_type}"
            )

        # Validate configuration
        if not channel.validate_config():
            raise HTTPException(
                status_code=400, detail="Invalid channel configuration"
            )

        # Create test message
        test_message = NotificationMessage(
            title="Test Notification from Tobit CEP",
            body="This is a test alert to verify your notification channel is working correctly.",
            recipients=config.get("recipients", []),
            metadata={
                "test": "true",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Send test notification
        result = await channel.send(test_message)

        return ResponseEnvelope.success(
            data={
                "success": result,
                "message": "Test notification sent successfully!"
                if result
                else "Failed to send test notification. Check configuration.",
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error testing channel: {str(e)}"
        )


@router.get("/types")
def get_channel_types() -> ResponseEnvelope:
    """
    Get available notification channel types and their configurations.

    Returns:
        List of available channel types with required fields
    """
    channel_types = {
        "slack": {
            "display_name": "Slack",
            "description": "Send alerts to Slack channels via webhook",
            "icon": "📱",
            "required_fields": ["webhook_url"],
            "optional_fields": [],
        },
        "email": {
            "display_name": "Email",
            "description": "Send alerts via SMTP",
            "icon": "📧",
            "required_fields": [
                "smtp_host",
                "smtp_port",
                "from_email",
                "password",
            ],
            "optional_fields": ["use_tls"],
        },
        "sms": {
            "display_name": "SMS",
            "description": "Send alerts via Twilio",
            "icon": "📲",
            "required_fields": ["account_sid", "auth_token", "from_number"],
            "optional_fields": [],
        },
        "webhook": {
            "display_name": "Webhook",
            "description": "Send alerts to HTTP endpoints",
            "icon": "🔗",
            "required_fields": ["url"],
            "optional_fields": ["headers"],
        },
        "pagerduty": {
            "display_name": "PagerDuty",
            "description": "Create incidents in PagerDuty",
            "icon": "⚠️",
            "required_fields": ["integration_key"],
            "optional_fields": ["default_severity"],
        },
    }

    return ResponseEnvelope.success(data={"channel_types": channel_types})


@router.get("/status")
def get_channels_status(session: Session = Depends(get_session)) -> ResponseEnvelope:
    """
    Get notification channels status with statistics.

    Returns:
        - Each channel's status (active/inactive)
        - Recent send statistics
        - Failure rate and retry status
        - Last connection time
    """
    notifications = list_notifications(session, active_only=False)

    channels_status = {}
    now = datetime.now(timezone.utc)
    lookback_hours = 24
    lookback = now - timedelta(hours=lookback_hours)

    for notification in notifications:
        channel_type = notification.channel

        if channel_type not in channels_status:
            channels_status[channel_type] = {
                "type": channel_type,
                "display_name": {
                    "slack": "Slack",
                    "email": "Email",
                    "sms": "SMS",
                    "webhook": "Webhook",
                    "pagerduty": "PagerDuty",
                }.get(channel_type, channel_type),
                "active": 0,
                "inactive": 0,
                "total_sent": 0,
                "total_failed": 0,
                "recent_logs": [],
                "last_sent_at": None,
            }

        if notification.is_active:
            channels_status[channel_type]["active"] += 1
        else:
            channels_status[channel_type]["inactive"] += 1

        # Get recent logs for this notification
        logs = list_notification_logs(session, str(notification.notification_id), limit=100)

        for log in logs:
            if log.fired_at >= lookback:
                channels_status[channel_type]["total_sent"] += 1
                if log.status != "success":
                    channels_status[channel_type]["total_failed"] += 1

                if not channels_status[channel_type]["last_sent_at"] or log.fired_at > channels_status[channel_type]["last_sent_at"]:
                    channels_status[channel_type]["last_sent_at"] = log.fired_at

                channels_status[channel_type]["recent_logs"].append({
                    "log_id": str(log.log_id),
                    "fired_at": log.fired_at.isoformat(),
                    "status": log.status,
                    "response_status": log.response_status,
                })

    # Calculate failure rate and add to each channel
    for channel_data in channels_status.values():
        if channel_data["total_sent"] > 0:
            channel_data["failure_rate"] = channel_data["total_failed"] / channel_data["total_sent"]
        else:
            channel_data["failure_rate"] = 0

        # Keep only last 10 logs
        channel_data["recent_logs"] = channel_data["recent_logs"][-10:]

    return ResponseEnvelope.success(
        data={
            "channels": list(channels_status.values()),
            "period_hours": lookback_hours,
        }
    )
