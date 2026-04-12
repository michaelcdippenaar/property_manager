from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve
from graphene_django.views import GraphQLView
from .stats import StatsView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("graphql/", GraphQLView.as_view(graphiql=settings.DEBUG)),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/properties/", include("apps.properties.urls")),
    path("api/v1/leases/", include("apps.leases.urls")),
    path("api/v1/maintenance/", include("apps.maintenance.urls")),
    path("api/v1/esigning/", include("apps.esigning.urls")),
    path("api/v1/tenant-portal/", include("apps.tenant_portal.urls")),
    path("api/v1/ai/", include("apps.ai.urls")),
    path("api/v1/stats/", StatsView.as_view(), name="stats"),
    path("api/v1/test-hub/", include("apps.test_hub.urls")),
    path("api/v1/market-data/", include("apps.market_data.urls")),
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
]
