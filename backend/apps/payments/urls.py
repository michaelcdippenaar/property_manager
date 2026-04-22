from rest_framework.routers import DefaultRouter

from .views import RentInvoiceViewSet, RentPaymentViewSet, UnmatchedPaymentViewSet

router = DefaultRouter()
router.register(r"invoices", RentInvoiceViewSet, basename="rentinvoice")
router.register(r"payments", RentPaymentViewSet, basename="rentpayment")
router.register(r"unmatched", UnmatchedPaymentViewSet, basename="unmatchedpayment")

urlpatterns = router.urls
