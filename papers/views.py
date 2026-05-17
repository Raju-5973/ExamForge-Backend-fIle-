from rest_framework import viewsets, permissions
from .models import QuestionPaper
from .serializers import QuestionPaperSerializer
from users.permissions import IsPrincipal

class QuestionPaperViewSet(viewsets.ModelViewSet):
    queryset = QuestionPaper.objects.all()
    serializer_class = QuestionPaperSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsPrincipal()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'principal':
            return QuestionPaper.objects.filter(created_by=user).order_by('-created_at')
        # If staff, maybe they can see papers for their subject? 
        # For now, let's keep it user-specific as requested.
        return QuestionPaper.objects.filter(created_by=user).order_by('-created_at')
