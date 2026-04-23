"""
Base ABC for OTP delivery channels.

All channels must implement `send(recipient, code, context)`.
"""
from abc import ABC, abstractmethod
from typing import Any


class Channel(ABC):
    """
    Abstract base class for OTP delivery channels.

    Concrete implementations: EmailChannel, SMSChannel.
    """

    @abstractmethod
    def send(self, recipient: str, code: str, context: dict[str, Any]) -> None:
        """
        Deliver the OTP code to the recipient.

        Args:
            recipient: Delivery address — email address or phone number.
            code:      The plaintext 6-digit OTP to deliver.
            context:   Rendering context, e.g. {"purpose": "registration", "ttl_minutes": 5}.

        Raises:
            NotImplementedError: When the channel has no concrete implementation yet.
            Exception:           Any transport error; callers should catch and try the next channel.
        """
        raise NotImplementedError
