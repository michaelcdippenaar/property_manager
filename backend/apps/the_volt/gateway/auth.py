"""
VoltApiKeyAuthentication — DRF authentication class for subscriber API keys.

Used only on the external gateway endpoints (/gateway/request/, /gateway/checkout/).
All other Volt endpoints use standard JWT auth.

Header: X-Volt-API-Key: volt_<token>

Sets request.auth = DataSubscriber instance (not a Django User).
request.user remains AnonymousUser for these endpoints — permission checks
must use request.auth instead.
"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from apps.the_volt.encryption.utils import hash_bytes


class VoltApiKeyAuthentication(BaseAuthentication):
    def authenticate(self, request):
        api_key = request.headers.get("X-Volt-API-Key", "").strip()
        if not api_key:
            return None  # Let other authenticators handle it

        from apps.the_volt.gateway.models import DataSubscriber
        key_hash = hash_bytes(api_key.encode())
        try:
            subscriber = DataSubscriber.objects.get(api_key_hash=key_hash, is_active=True)
        except DataSubscriber.DoesNotExist:
            raise AuthenticationFailed("Invalid or inactive API key.")

        # Return (user, auth) — user=None signals "not a Django user"
        # Views using this auth must check request.auth for subscriber identity
        return (None, subscriber)

    def authenticate_header(self, request):
        return "X-Volt-API-Key"
