"""
Firebase Cloud Messaging (FCM) push notification dispatch service.

Handles both Android (FCM data/notification messages) and iOS (APNs via FCM).

Usage::

    from apps.notifications.services.push import send_push_to_user

    send_push_to_user(
        user=lease.primary_tenant.linked_user,
        title="Lease signed",
        body="Your lease for Unit 3A has been signed by all parties.",
        data={"screen": "lease_detail", "lease_id": str(lease.pk)},
        category="lease",
    )

Firebase is initialised lazily on first use.  The service account JSON path is
read from ``settings.FIREBASE_CREDENTIALS_PATH`` (or
``FIREBASE_CREDENTIALS_PATH`` env var).  If Firebase is not configured, push
calls are logged as warnings and skipped gracefully — this keeps the dev
environment working without a Firebase project.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from apps.accounts.models import User

logger = logging.getLogger(__name__)

_firebase_app = None
_firebase_init_attempted = False


def _get_firebase_app():
    """Initialise firebase_admin once and return the app, or None if not configured."""
    global _firebase_app, _firebase_init_attempted
    if _firebase_init_attempted:
        return _firebase_app

    _firebase_init_attempted = True

    creds_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None) or os.environ.get(
        "FIREBASE_CREDENTIALS_PATH"
    )
    if not creds_path:
        logger.warning(
            "Push notifications: FIREBASE_CREDENTIALS_PATH not set — push dispatch disabled."
        )
        return None

    if not os.path.isfile(creds_path):
        logger.warning(
            "Push notifications: credentials file not found at %s — push dispatch disabled.",
            creds_path,
        )
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(creds_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase app initialised from %s", creds_path)
    except Exception:
        logger.exception("Failed to initialise Firebase app")
        _firebase_app = None

    return _firebase_app


def send_push_to_user(
    user: "User",
    title: str,
    body: str,
    data: dict[str, str] | None = None,
    category: str | None = None,
) -> int:
    """
    Send a push notification to all active device tokens for *user*.

    Checks ``PushPreference`` for the given category before dispatching.
    Stale/invalid tokens are silently removed.

    Returns the number of successfully dispatched messages.
    """
    from apps.accounts.models import PushToken
    from apps.notifications.models import PushPreference

    # Honour per-user category preference (default allow if no preference row exists)
    if category and not PushPreference.is_enabled(user, category):
        logger.debug(
            "Push suppressed for user %s — category '%s' disabled.", user.pk, category
        )
        return 0

    tokens = list(PushToken.objects.filter(user=user).values_list("token", "platform", "pk"))
    if not tokens:
        return 0

    app = _get_firebase_app()
    if app is None:
        return 0

    try:
        from firebase_admin import messaging
    except ImportError:
        logger.warning("firebase_admin not installed — push dispatch skipped.")
        return 0

    extra_data = {k: str(v) for k, v in (data or {}).items()}
    if category:
        extra_data["category"] = category

    sent = 0
    stale_pks: list[int] = []

    for token, platform, pk in tokens:
        notification = messaging.Notification(title=title, body=body)

        if platform == PushToken.Platform.IOS:
            apns = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1)
                )
            )
            msg = messaging.Message(
                notification=notification,
                apns=apns,
                data=extra_data,
                token=token,
            )
        else:
            android = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    channel_id="klikk_rentals",
                ),
            )
            msg = messaging.Message(
                notification=notification,
                android=android,
                data=extra_data,
                token=token,
            )

        try:
            messaging.send(msg, app=app)
            sent += 1
        except messaging.UnregisteredError:
            logger.info(
                "Push token %s is no longer registered — removing.", pk
            )
            stale_pks.append(pk)
        except Exception:
            logger.exception("Failed to send push to token pk=%s", pk)

    if stale_pks:
        PushToken.objects.filter(pk__in=stale_pks).delete()

    return sent


def send_push_to_users(
    users,
    title: str,
    body: str,
    data: dict[str, str] | None = None,
    category: str | None = None,
) -> int:
    """Send the same push to multiple users. Returns total dispatched count."""
    total = 0
    for user in users:
        if user is not None:
            total += send_push_to_user(user, title, body, data=data, category=category)
    return total
