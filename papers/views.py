from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import QuestionPaper, Blueprint, ApprovalWorkflow, Notification
from .serializers import QuestionPaperSerializer, BlueprintSerializer, ApprovalWorkflowSerializer, NotificationSerializer
from users.permissions import IsPrincipal, IsStaff
from questions.models import Question
from django.utils import timezone
import random

class QuestionPaperViewSet(viewsets.ModelViewSet):
    queryset = QuestionPaper.objects.all()
    serializer_class = QuestionPaperSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'destroy']:
            return [IsPrincipal()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        institution = self.request.user.profile.institution if hasattr(self.request.user, 'profile') else None
        serializer.save(created_by=self.request.user, institution=institution)

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'profile'):
            return QuestionPaper.objects.none()
        institution = user.profile.institution
        base_qs = QuestionPaper.objects.all()
        if institution:
            # All members of the institution can see all papers
            base_qs = base_qs.filter(institution=institution)
            return base_qs.order_by('-created_at')
        # Fallback: only show user's own papers if no institution
        return base_qs.filter(created_by=user).order_by('-created_at')


    @action(detail=False, methods=['post'])
    def generate_from_blueprint(self, request):
        blueprint_id = request.data.get('blueprint_id')
        if not blueprint_id:
            return Response({'error': 'Blueprint ID required'}, status=400)
            
        try:
            blueprint = Blueprint.objects.get(id=blueprint_id)
        except Blueprint.DoesNotExist:
            return Response({'error': 'Blueprint not found'}, status=404)
            
        config = blueprint.configuration
        total_marks = blueprint.total_marks
        
        # A simple algorithm to pick questions based on difficulty distribution.
        # For a production system, this would be a complex knapsack or genetic algorithm solving constraints for Unit, Bloom, and Difficulty simultaneously.
        # Here we will do a greedy approach prioritizing Difficulty -> Bloom.
        
        diff_dist = config.get('difficulty', {})
        bloom_dist = config.get('bloom_distribution', {})
        
        available_questions = Question.objects.filter(subject=blueprint.subject, is_deleted=False)
        selected_questions = []
        current_marks = 0
        
        # Calculate target marks for each difficulty bucket
        target_diff_marks = {
            diff: int((pct / 100) * total_marks) for diff, pct in diff_dist.items()
        }
        
        for diff, target in target_diff_marks.items():
            q_pool = list(available_questions.filter(difficulty=diff).order_by('?')) # Randomize
            bucket_marks = 0
            for q in q_pool:
                if bucket_marks + q.marks <= target:
                    selected_questions.append(q)
                    bucket_marks += q.marks
                    current_marks += q.marks
                    
        # If we didn't hit total marks exactly due to rounding or missing questions, fill with random questions
        if current_marks < total_marks:
            remaining_marks = total_marks - current_marks
            fallback_pool = list(available_questions.exclude(id__in=[q.id for q in selected_questions]).order_by('?'))
            for q in fallback_pool:
                if remaining_marks - q.marks >= 0:
                    selected_questions.append(q)
                    remaining_marks -= q.marks
                    if remaining_marks == 0:
                        break

        if not selected_questions:
            return Response({'error': 'Not enough questions in bank to generate paper.'}, status=400)

        # Create the paper (include institution so it is visible to all institution members)
        institution = request.user.profile.institution if hasattr(request.user, 'profile') else None
        paper = QuestionPaper.objects.create(
            subject=blueprint.name,
            created_by=request.user,
            institution=institution,
            distribution=[{"type": "Generated via Blueprint", "marks": total_marks, "count": len(selected_questions)}]
        )
        paper.questions.set(selected_questions)
        
        return Response({'message': 'Paper generated successfully', 'paper_id': paper.id})

class BlueprintViewSet(viewsets.ModelViewSet):
    queryset = Blueprint.objects.all()
    serializer_class = BlueprintSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        department = None
        institution = None
        if hasattr(self.request.user, 'profile'):
            department = self.request.user.profile.department
            institution = self.request.user.profile.institution
        serializer.save(created_by=self.request.user, department=department, institution=institution)

    def get_queryset(self):
        user = self.request.user
        if not hasattr(user, 'profile'):
            return Blueprint.objects.none()
        
        institution = user.profile.institution
        base_qs = Blueprint.objects.all()
        if institution:
            # All institution members can see all blueprints
            return base_qs.filter(institution=institution).order_by('-created_at')
        
        # Fallback: show own blueprints if no institution
        return base_qs.filter(created_by=user).order_by('-created_at')


def _notify(recipient, notification_type, title, message, paper=None):
    """Helper to create a Notification record."""
    Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        related_paper=paper
    )

class ApprovalWorkflowViewSet(viewsets.ModelViewSet):
    queryset = ApprovalWorkflow.objects.all()
    serializer_class = ApprovalWorkflowSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        institution = user.profile.institution if hasattr(user, 'profile') else None
        qs = ApprovalWorkflow.objects.all()
        if institution:
            qs = qs.filter(institution=institution)
        return qs.order_by('-submitted_at')

    def perform_create(self, serializer):
        user = self.request.user
        institution = user.profile.institution if hasattr(user, 'profile') else None
        workflow = serializer.save(submitted_by=user, institution=institution, status='pending_hod')
        # Notify principals (act as HOD for now)
        from django.contrib.auth.models import User as DjangoUser
        from users.models import UserProfile
        principals = DjangoUser.objects.filter(profile__role='principal', profile__institution=institution)
        for p in principals:
            _notify(p, 'approval_submitted',
                    f'New Paper Awaiting Approval',
                    f'{user.get_full_name() or user.email} submitted "{workflow.paper.subject}" for HOD approval.',
                    paper=workflow.paper)


    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        workflow = self.get_object()
        remarks = request.data.get('remarks', '')
        user = request.user

        if workflow.status == 'pending_hod':
            workflow.status = 'pending_controller'
            workflow.hod_reviewed_by = user
            workflow.hod_reviewed_at = timezone.now()
            workflow.hod_remarks = remarks
            workflow.save()
            _notify(workflow.submitted_by, 'info',
                    'HOD Approved Your Paper',
                    f'Your paper "{workflow.paper.subject}" passed HOD review and is now pending Exam Controller approval.',
                    paper=workflow.paper)
            return Response({'status': 'Forwarded to Exam Controller'})

        elif workflow.status == 'pending_controller':
            workflow.status = 'approved'
            workflow.controller_reviewed_by = user
            workflow.controller_reviewed_at = timezone.now()
            workflow.controller_remarks = remarks
            workflow.save()
            _notify(workflow.submitted_by, 'approval_approved',
                    '✅ Paper Fully Approved',
                    f'Your paper "{workflow.paper.subject}" has been approved by the Exam Controller.',
                    paper=workflow.paper)
            return Response({'status': 'Paper fully approved'})

        return Response({'error': 'Cannot approve from current status'}, status=400)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        workflow = self.get_object()
        remarks = request.data.get('remarks', 'No reason provided.')
        workflow.status = 'rejected'
        workflow.controller_remarks = remarks
        workflow.save()
        _notify(workflow.submitted_by, 'approval_rejected',
                '❌ Paper Rejected',
                f'Your paper "{workflow.paper.subject}" was rejected. Remarks: {remarks}',
                paper=workflow.paper)
        return Response({'status': 'Paper rejected'})


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by('-created_at')


    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'All marked as read'})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.is_read = True
        notif.save()
        return Response({'status': 'Marked as read'})
