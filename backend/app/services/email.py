"""
STUB email service: no real SMTP/provider credentials exist in this
environment, so sending an email just means logging the link to stdout.
Swap this out for a real provider (SES, SendGrid, etc.) later by writing a
class that implements the same `send_verification_email` interface
(EmailService is written as an ABC for exactly this reason) and wiring it
in wherever `EmailService()` is currently constructed -- callers only
depend on the interface, not on this stdout implementation.
"""
from abc import ABC, abstractmethod


class EmailService(ABC):
    @abstractmethod
    def send_verification_email(self, to_email: str, verification_url: str) -> None:
        ...


class ConsoleEmailService(EmailService):
    """Logs the verification link to stdout instead of sending a real email."""

    def send_verification_email(self, to_email: str, verification_url: str) -> None:
        print(f"[email] verify: {verification_url}")
