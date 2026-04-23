from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from django.http import JsonResponse
from graphene_django.views import GraphQLView
from .stats import StatsView
from apps.properties.dashboard_views import DashboardPortfolioView


def health_check(request):
    """Simple liveness probe used by Docker health check and deploy/health-check.sh."""
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("api/v1/health/", health_check, name="health-check"),
    path("admin/", admin.site.urls),
    path("graphql/", GraphQLView.as_view(graphiql=settings.DEBUG)),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/properties/", include("apps.properties.urls")),
    path("api/v1/leases/", include("apps.leases.urls")),
    path("api/v1/tenant/", include("apps.tenant.urls")),
    path("api/v1/maintenance/", include("apps.maintenance.urls")),
    path("api/v1/esigning/", include("apps.esigning.urls")),
    path("api/v1/tenant-portal/", include("apps.tenant_portal.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
    path("api/v1/stats/", StatsView.as_view(), name="stats"),
    path("api/v1/dashboard/portfolio/", DashboardPortfolioView.as_view(), name="dashboard-portfolio"),
    # test-hub is only accessible when ENABLE_TEST_ENDPOINTS is True (never production)
    *(
        [path("api/v1/test-hub/", include("apps.test_hub.urls"))]
        if settings.ENABLE_TEST_ENDPOINTS
        else []
    ),
    path("api/v1/market-data/", include("apps.market_data.urls")),
    path("api/v1/the-volt/", include("apps.the_volt.urls")),
    path("api/v1/legal/", include("apps.legal.urls")),
    path("api/v1/payments/", include("apps.payments.urls")),
    path("api/v1/audit/", include("apps.audit.urls")),
    path("api/v1/popia/", include("apps.popia.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]

# django-silk profiler UI — available in dev only (gated by INSTALLED_APPS)
if "silk" in settings.INSTALLED_APPS:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
