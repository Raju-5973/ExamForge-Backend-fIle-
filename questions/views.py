from rest_framework import viewsets, permissions
from .models import Question
from .serializers import QuestionSerializer
from users.permissions import IsStaff, IsPrincipal

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsStaff()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        department = None
        if hasattr(self.request.user, 'profile'):
            department = self.request.user.profile.department
        serializer.save(created_by=self.request.user, department=department)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()

    def get_queryset(self):
        user = self.request.user
        base_qs = Question.objects.filter(is_deleted=False)
        
        if not hasattr(user, 'profile'):
            return base_qs.none()
            
        if user.profile.role == 'principal':
            return base_qs.order_by('-created_at')
            
        # Staff members see questions from their own department
        user_dept = user.profile.department
        return base_qs.filter(department=user_dept).order_by('-created_at')
