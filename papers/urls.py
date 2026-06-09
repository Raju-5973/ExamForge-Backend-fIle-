from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import QuestionPaperViewSet, BlueprintViewSet, ApprovalWorkflowViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'papers', QuestionPaperViewSet, basename='paper')
router.register(r'blueprints', BlueprintViewSet, basename='blueprint')
router.register(r'approvals', ApprovalWorkflowViewSet, basename='approval')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
