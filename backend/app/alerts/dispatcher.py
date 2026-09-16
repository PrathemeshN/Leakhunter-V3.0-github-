import json
import logging
import aiohttp
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

async def dispatch_webhook(alert_data: Dict[str, Any], destination_type: str, webhook_url: str) -> bool:
    """
    Formats and dispatches the alert to the specified destination type (Slack, Discord, Custom).
    """
    if not webhook_url:
        logger.error("No webhook URL provided.")
        return False

    payload = {}
    headers = {"Content-Type": "application/json"}

    try:
        if destination_type.lower() == "slack":
            payload = _format_slack_payload(alert_data)
        elif destination_type.lower() == "discord":
            payload = _format_discord_payload(alert_data)
        else:
            # Default generic webhook payload
            payload = alert_data

        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, headers=headers, timeout=10) as response:
                if response.status >= 400:
                    response_text = await response.text()
                    logger.error(f"Webhook dispatch failed: HTTP {response.status} - {response_text}")
                    return False
                logger.info(f"Successfully dispatched alert to {destination_type}")
                return True
    except Exception as e:
        logger.error(f"Exception while dispatching webhook to {destination_type}: {e}")
        return False


def _format_slack_payload(alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats the breach payload into Slack's Block Kit format.
    """
    title = alert_data.get("title", "New Threat Alert")
    severity = alert_data.get("severity", 0)
    source = alert_data.get("source", "Unknown Source")
    desc = alert_data.get("description", "")
    
    # Simple color coding based on severity
    color = "#FF0000" if severity >= 80 else "#FFA500" if severity >= 50 else "#00FF00"

    return {
        "text": f"🚨 *High Severity Alert: {title}* 🚨",
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{title}*\n\n{desc[:500]}..." if len(desc) > 500 else f"*{title}*\n\n{desc}"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Severity:*\n{severity}/100"},
                            {"type": "mrkdwn", "text": f"*Source:*\n{source}"},
                            {"type": "mrkdwn", "text": f"*Data Types:*\n{', '.join(alert_data.get('data_types', []))}"}
                        ]
                    }
                ]
            }
        ]
    }


def _format_discord_payload(alert_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats the breach payload into Discord's Embed format.
    """
    title = alert_data.get("title", "New Threat Alert")
    severity = alert_data.get("severity", 0)
    source = alert_data.get("source", "Unknown Source")
    desc = alert_data.get("description", "")
    
    # Decimal color coding based on severity (Discord uses decimal integers for colors)
    # Red: 16711680, Orange: 16753920, Green: 65280
    color = 16711680 if severity >= 80 else 16753920 if severity >= 50 else 65280

    return {
        "content": "🚨 **New Threat Alert** 🚨",
        "embeds": [
            {
                "title": title[:256],
                "description": desc[:4096],
                "color": color,
                "fields": [
                    {"name": "Severity", "value": f"{severity}/100", "inline": True},
                    {"name": "Source", "value": source, "inline": True},
                    {"name": "Data Types", "value": ", ".join(alert_data.get("data_types", [])) or "None", "inline": False}
                ],
                "footer": {"text": "LeakHunter V3 Automated Alerting"}
            }
        ]
    }
