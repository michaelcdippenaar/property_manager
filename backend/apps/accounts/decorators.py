"""
Feature-flag decorator for DRF views.

Usage (class-based view action)::

    from apps.accounts.decorators import requires_feature

    class LeaseBuilderSessionView(APIView):
        @requires_feature("ai_lease_generation")
        def post(self, request):
            ...

Usage (function-based view)::

    @api_view(["POST"])
    @requires_feature("ai_lease_generation")
    def my_view(request):
        ...

When the agency does not have the feature, returns:

    HTTP 402 Payment Required
    {
        "detail": "Your plan does not include ai_lease_generation.",
        "feature": "ai_lease_generation",
        "upgrade_required": true,
        "upgrade_url": "https://klikk.co.za/pricing"
    }
"""
from __future__ import annotations

import functools
import os
from typing import Callable

from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.response import Response


def requires_feature(feature_slug: str) -> Callable:
    """
    Decorator that blocks a view method unless the request's agency
    has the named feature enabled on its subscription tier.

    Must be applied *inside* any permission decorators so authentication
    has already been verified by the time this runs.
    """
    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(first_arg, *args, **kwargs):
            """
            Works for both CBV instance methods and FBV:
            - CBV:  first_arg=self  args=(request, ...)
            - FBV:  first_arg=request
            """
            from rest_framework.request import Request as DRFRequest

            # Determine which argument is the DRF Request
            if isinstance(first_arg, DRFRequest):
                # FBV: first_arg IS the request
                request = first_arg
            elif args and isinstance(args[0], DRFRequest):
                # CBV: first_arg is self, args[0] is request
                request = args[0]
            else:
                # Cannot identify DRF Request — fail hard rather than granting access.
                import django.conf
                if django.conf.settings.DEBUG:
                    raise ImproperlyConfigured(
                        f"@requires_feature could not resolve DRF Request for feature "
                        f"'{feature_slug}'. Check that the decorator is applied to a CBV "
                        f"method (self, request, ...) or a plain FBV (request, ...)."
                    )
                return Response(
                    {"detail": "Feature enforcement failed."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            if hasattr(request, 'user') and request.user.is_authenticated:
                from apps.accounts.models import Agency
                from apps.accounts.tier_service import TierService

                agency = Agency.for_user(request.user)
                svc = TierService(agency)
                if not svc.has_feature(feature_slug):
                    upgrade_url = os.environ.get("STRIPE_UPGRADE_LINK", "https://klikk.co.za/pricing")
                    return Response(
                        {
                            "detail": f"Your plan does not include {feature_slug}.",
                            "feature": feature_slug,
                            "upgrade_required": True,
                            "upgrade_url": upgrade_url,
                        },
                        status=status.HTTP_402_PAYMENT_REQUIRED,
                    )

            return view_func(first_arg, *args, **kwargs)
        return wrapper
    return decorator
