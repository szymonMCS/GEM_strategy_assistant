import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


class PushoverError(Exception):
    """Pushover API error."""
    pass


class PushoverClient:
    def __init__(
        self, 
        user_key: Optional[str] = None, 
        api_token: Optional[str] = None
    ):
        """
        Initialize Pushover client.
        
        Args:
            user_key: Pushover user key (if None, reads from settings)
            api_token: Pushover API token (if None, reads from settings)
        """
        if user_key is None or api_token is None:
            from gem_strategy_assistant.config import settings
            user_key = user_key or settings.pushover_user_key
            api_token = api_token or settings.pushover_api_token

        if not user_key:
            raise PushoverError("PUSHOVER_USER_KEY not configured")
        if not api_token:
            raise PushoverError("PUSHOVER_API_TOKEN not configured")

        self.user_key = user_key
        self.api_token = api_token

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _make_request(self, payload: dict) -> dict:
        """Make API request to Pushover."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(PUSHOVER_API_URL, data=payload)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Pushover API error {e.response.status_code}: {e.response.text}")
            raise PushoverError(f"API returned {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Pushover request failed: {e}")
            raise PushoverError(f"Request failed: {e}") from e

    def send_notification(
        self,
        message: str,
        title: Optional[str] = None,
        priority: int = 0,
        sound: Optional[str] = None,
    ) -> dict:
        """
        Send a push notification via Pushover.
        
        Args:
            message: Notification message (max 1024 chars)
            title: Notification title (max 250 chars)
            priority: Priority level (-2 to 2, default 0)
            sound: Notification sound name
            
        Returns:
            Response dictionary with status
            
        Raises:
            PushoverError: If sending fails
        """
        logger.info(f"Sending Pushover notification: {title or 'No title'}")
        
        payload = {
            "token": self.api_token,
            "user": self.user_key,
            "message": message[:1024],
        }
        
        if title:
            payload["title"] = title[:250]
        if sound:
            payload["sound"] = sound
        
        payload["priority"] = max(-2, min(2, priority))
        
        try:
            result = self._make_request(payload)
            
            if result.get("status") == 1:
                logger.info("✅ Pushover notification sent successfully")
            else:
                logger.warning(f"⚠️  Pushover response: {result}")
                
            return result
        except PushoverError as e:
            logger.error(f"❌ Failed to send Pushover notification: {e}")
            raise

    def send_signal_notification(
        self,
        signal_type: str,
        etf_name: str,
        details: str,
        priority: int = 1,
    ) -> dict:
        """
        Send a trading signal push notification.
        
        Args:
            signal_type: Type of signal ("BUY", "SELL", "HOLD")
            etf_name: Name of the ETF
            details: Additional details about the signal
            priority: Notification priority (default: 1 = high)
            
        Returns:
            Response dictionary with status
        """
        title = f"🚨 {signal_type} {etf_name}"
        message = f"Momentum Signal: {signal_type}\nETF: {etf_name}\n\n{details}"
        
        sound_map = {
            "BUY": "cashregister",
            "SELL": "falling",
            "HOLD": "cosmic",
        }
        sound = sound_map.get(signal_type, "pushover")
        
        return self.send_notification(
            message=message,
            title=title,
            priority=priority,
            sound=sound,
        )
