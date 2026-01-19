from fastmcp import FastMCP
from typing import Optional

from gem_strategy_assistant.infrastructure.notifications import (
    SendGridClient,
    SendGridError,
    PushoverClient,
    PushoverError,
)

mcp = FastMCP(
    name="momentum-notification-server"
)

_sendgrid_client: Optional[SendGridClient] = None
_pushover_client: Optional[PushoverClient] = None


def get_sendgrid_client() -> Optional[SendGridClient]:
    global _sendgrid_client
    if _sendgrid_client is None:
        try:
            _sendgrid_client = SendGridClient()
        except SendGridError:
            return None
    return _sendgrid_client


def get_pushover_client() -> Optional[PushoverClient]:
    """Get or create Pushover client singleton."""
    global _pushover_client
    if _pushover_client is None:
        try:
            _pushover_client = PushoverClient()
        except PushoverError:
            return None
    return _pushover_client


@mcp.tool()
def send_email(to_email: str, subject: str, content: str, content_type: str = "text/plain") -> dict:
    """
    Send an email notification via SendGrid.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        content: Email body content
        content_type: Content type ("text/plain" or "text/html", default: "text/plain")
        
    Returns:
        Dictionary with status and result
        
    Example:
        send_email("user@example.com", "Test", "Hello world!")
    """
    client = get_sendgrid_client()
    
    if client is None:
        return {
            "success": False,
            "error": "SendGrid not configured. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL."
        }
    
    try:
        result = client.send_email(to_email, subject, content, content_type)
        return {
            "success": True,
            "to_email": to_email,
            "subject": subject,
            "result": result
        }
    except SendGridError as e:
        return {
            "success": False,
            "error": str(e),
            "to_email": to_email
        }


@mcp.tool()
def send_push_notification(
    message: str,
    title: Optional[str] = None,
    priority: int = 0,
    sound: Optional[str] = None
) -> dict:
    """
    Send a push notification via Pushover.
    
    Args:
        message: Notification message (max 1024 chars)
        title: Notification title (max 250 chars, optional)
        priority: Priority level (-2 to 2, default: 0)
        sound: Notification sound name (optional)
        
    Returns:
        Dictionary with status and result
        
    Example:
        send_push_notification("Market alert!", title="ETF Strategy", priority=1)
    """
    client = get_pushover_client()
    
    if client is None:
        return {
            "success": False,
            "error": "Pushover not configured. Set PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN."
        }
    
    try:
        result = client.send_notification(message, title, priority, sound)
        return {
            "success": True,
            "title": title,
            "message_length": len(message),
            "priority": priority,
            "result": result
        }
    except PushoverError as e:
        return {
            "success": False,
            "error": str(e),
            "message": message[:100]
        }


@mcp.tool()
def send_signal_email(
    to_email: str,
    signal_type: str,
    etf_name: str,
    details: str
) -> dict:
    """
    Send a trading signal notification via email.
    
    Args:
        to_email: Recipient email address
        signal_type: Type of signal ("BUY", "SELL", "HOLD")
        etf_name: Name of the ETF
        details: Additional details about the signal
        
    Returns:
        Dictionary with status and result
        
    Example:
        send_signal_email("user@example.com", "BUY", "EIMI", "Momentum rank: #1")
    """
    client = get_sendgrid_client()
    
    if client is None:
        return {
            "success": False,
            "error": "SendGrid not configured. Set SENDGRID_API_KEY and SENDGRID_FROM_EMAIL."
        }
    
    try:
        result = client.send_signal_notification(to_email, signal_type, etf_name, details)
        return {
            "success": True,
            "to_email": to_email,
            "signal_type": signal_type,
            "etf_name": etf_name,
            "result": result
        }
    except SendGridError as e:
        return {
            "success": False,
            "error": str(e),
            "signal_type": signal_type,
            "etf_name": etf_name
        }


@mcp.tool()
def send_signal_push(
    signal_type: str,
    etf_name: str,
    details: str,
    priority: int = 1
) -> dict:
    """
    Send a trading signal push notification.
    
    Args:
        signal_type: Type of signal ("BUY", "SELL", "HOLD")
        etf_name: Name of the ETF
        details: Additional details about the signal
        priority: Notification priority (default: 1 = high)
        
    Returns:
        Dictionary with status and result
        
    Example:
        send_signal_push("BUY", "EIMI", "Momentum rank: #1, Score: 15.2%")
    """
    client = get_pushover_client()
    
    if client is None:
        return {
            "success": False,
            "error": "Pushover not configured. Set PUSHOVER_USER_KEY and PUSHOVER_API_TOKEN."
        }
    
    try:
        result = client.send_signal_notification(signal_type, etf_name, details, priority)
        return {
            "success": True,
            "signal_type": signal_type,
            "etf_name": etf_name,
            "priority": priority,
            "result": result
        }
    except PushoverError as e:
        return {
            "success": False,
            "error": str(e),
            "signal_type": signal_type,
            "etf_name": etf_name
        }


@mcp.tool()
def send_signal_all_channels(
    to_email: str,
    signal_type: str,
    etf_name: str,
    details: str,
    push_priority: int = 1
) -> dict:
    """
    Send a trading signal via all available notification channels.
    
    Attempts to send via both email (SendGrid) and push (Pushover).
    Returns combined status for both channels.
    
    Args:
        to_email: Recipient email address
        signal_type: Type of signal ("BUY", "SELL", "HOLD")
        etf_name: Name of the ETF
        details: Additional details about the signal
        push_priority: Push notification priority (default: 1 = high)
        
    Returns:
        Dictionary with status for each channel
        
    Example:
        send_signal_all_channels(
            "user@example.com", 
            "BUY", 
            "EIMI", 
            "Momentum rank: #1, Score: 15.2%"
        )
    """
    results = {
        "signal_type": signal_type,
        "etf_name": etf_name,
        "email": {"attempted": False, "success": False},
        "push": {"attempted": False, "success": False},
    }
    
    email_client = get_sendgrid_client()
    if email_client is not None:
        results["email"]["attempted"] = True
        try:
            email_result = email_client.send_signal_notification(
                to_email, signal_type, etf_name, details
            )
            results["email"]["success"] = True
            results["email"]["result"] = email_result
        except SendGridError as e:
            results["email"]["error"] = str(e)
    else:
        results["email"]["error"] = "SendGrid not configured"
    
    push_client = get_pushover_client()
    if push_client is not None:
        results["push"]["attempted"] = True
        try:
            push_result = push_client.send_signal_notification(
                signal_type, etf_name, details, push_priority
            )
            results["push"]["success"] = True
            results["push"]["result"] = push_result
        except PushoverError as e:
            results["push"]["error"] = str(e)
    else:
        results["push"]["error"] = "Pushover not configured"
    
    results["overall_success"] = (
        results["email"]["success"] or results["push"]["success"]
    )
    
    return results


@mcp.tool()
def check_notification_status() -> dict:
    """
    Check which notification channels are configured and available.
    
    Returns:
        Dictionary with status of each notification channel
        
    Example:
        check_notification_status()
    """
    return {
        "sendgrid": {
            "configured": get_sendgrid_client() is not None,
            "provider": "SendGrid",
            "type": "email"
        },
        "pushover": {
            "configured": get_pushover_client() is not None,
            "provider": "Pushover",
            "type": "push"
        }
    }


if __name__ == "__main__":
    mcp.run()
