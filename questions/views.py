from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Question
from .serializers import QuestionSerializer
from users.permissions import IsStaff, IsPrincipal
from .tasks import generate_ai_questions_task
import json
import csv
import io
from django.db import transaction
import difflib

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsStaff()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        department = None
        institution = None
        if hasattr(self.request.user, 'profile'):
            department = self.request.user.profile.department
            institution = self.request.user.profile.institution
        serializer.save(created_by=self.request.user, department=department, institution=institution)

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save()

    def get_queryset(self):
        user = self.request.user
        base_qs = Question.objects.filter(is_deleted=False)
        
        if not hasattr(user, 'profile'):
            return base_qs.none()
        
        # Multi-tenant: always scope to the user's institution first
        institution = user.profile.institution
        if institution:
            base_qs = base_qs.filter(institution=institution)

        subject = self.request.query_params.get('subject')
        if subject:
            base_qs = base_qs.filter(subject=subject)
        
        if user.profile.role == 'principal':
            return base_qs.order_by('-created_at')
        
        # Staff members see questions from their own department within their institution
        user_dept = user.profile.department
        return base_qs.filter(department=user_dept).order_by('-created_at')


    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def generate_ai(self, request):
        topic = request.data.get('topic')
        difficulty = request.data.get('difficulty', 'Medium')
        marks = request.data.get('marks', 5)
        question_type = request.data.get('question_type', 'Short Questions')
        count = int(request.data.get('count', 5))
        
        if not topic:
            return Response({"error": "Topic is required"}, status=400)
            
        department = request.user.profile.department if hasattr(request.user, 'profile') else None
        
        # Dispatch Celery task
        task = generate_ai_questions_task.delay(
            topic=topic,
            difficulty=difficulty,
            marks=marks,
            question_type=question_type,
            count=count,
            user_id=request.user.id,
            department=department
        )
        
        return Response({
            "message": "AI Question Generation task started",
            "task_id": task.id
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def check_ai_status(self, request):
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({"error": "task_id is required"}, status=400)
            
        from celery.result import AsyncResult
        task_result = AsyncResult(task_id)
        
        response_data = {
            'task_id': task_id,
            'status': task_result.status,
            'result': task_result.result if task_result.ready() else None
        }
        return Response(response_data)


    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def bulk_upload(self, request):
        if 'file' not in request.FILES:
            return Response({"error": "No file provided"}, status=400)
            
        csv_file = request.FILES['file']
        if not csv_file.name.endswith('.csv'):
            return Response({"error": "Please upload a valid CSV file"}, status=400)

        department = request.user.profile.department if hasattr(request.user, 'profile') else None
        institution = request.user.profile.institution if hasattr(request.user, 'profile') else None

        try:
            # Read CSV
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
            next(io_string) # Skip header
            
            created_count = 0
            with transaction.atomic():
                for row in csv.reader(io_string, delimiter=',', quotechar='"'):
                    if len(row) < 5: continue # Basic validation
                    
                    # Expected format: Subject, Difficulty, Marks, Text, Sub_topic, Tags, Unit, Bloom, CO, PO
                    subject = row[0].strip()
                    difficulty = row[1].strip()
                    marks = int(row[2].strip() or 1)
                    text = row[3].strip()
                    sub_topic = row[4].strip() if len(row) > 4 else ''
                    tags = row[5].strip() if len(row) > 5 else ''
                    unit = int(row[6].strip()) if len(row) > 6 and row[6].strip() else None
                    bloom_level = row[7].strip() if len(row) > 7 else None
                    co_mapping = row[8].strip() if len(row) > 8 else None

                    # Duplicate detection check — scoped to institution
                    if not Question.objects.filter(text__iexact=text, institution=institution).exists():
                        Question.objects.create(
                            text=text,
                            subject=subject,
                            difficulty=difficulty,
                            marks=marks,
                            sub_topic=sub_topic,
                            tags=tags,
                            unit=unit,
                            bloom_level=bloom_level,
                            co_mapping=co_mapping,
                            department=department,
                            institution=institution,
                            created_by=request.user
                        )
                        created_count += 1
                        
            return Response({"message": f"Successfully imported {created_count} questions."})
            
        except Exception as e:
            return Response({"error": f"Failed to process CSV: {str(e)}"}, status=400)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def duplicate_check(self, request):
        """
        Module 8: Semantic Duplicate Detection Engine.
        Uses Levenshtein-like similarity ratio (difflib) to find near-duplicate questions
        in the institution's question bank before saving.
        """
        text = request.data.get('text', '').strip()
        if not text:
            return Response({"error": "Question text is required"}, status=400)

        user = request.user
        institution = user.profile.institution if hasattr(user, 'profile') else None
        
        # Scope to current institution
        candidate_qs = Question.objects.filter(is_deleted=False)
        if institution:
            candidate_qs = candidate_qs.filter(institution=institution)

        SIMILARITY_THRESHOLD = 0.75  # 75% similarity triggers a warning

        duplicates = []
        for q in candidate_qs[:500]:  # Limit for performance
            ratio = difflib.SequenceMatcher(None, text.lower(), q.text.lower()).ratio()
            if ratio >= SIMILARITY_THRESHOLD:
                duplicates.append({
                    'id': q.id,
                    'text': q.text,
                    'subject': q.subject,
                    'difficulty': q.difficulty,
                    'marks': q.marks,
                    'similarity': round(ratio * 100, 1),
                })

        duplicates.sort(key=lambda x: x['similarity'], reverse=True)
        return Response({
            'is_duplicate': len(duplicates) > 0,
            'count': len(duplicates),
            'matches': duplicates[:5],  # Return top 5 closest matches
        })

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def analytics(self, request):
        """
        Dedicated analytics endpoint for the principal dashboard.
        Returns aggregated stats for ALL questions (staff + AI) in the institution,
        regardless of department. Also includes paper generation trends.
        """
        from papers.models import QuestionPaper
        from django.db.models import Count
        from collections import defaultdict

        user = request.user
        institution = user.profile.institution if hasattr(user, 'profile') else None

        # Fetch ALL questions for the institution (not department-scoped)
        qs = Question.objects.filter(is_deleted=False)
        if institution:
            qs = qs.filter(institution=institution)

        total_questions = qs.count()

        # Subject distribution
        subject_map = defaultdict(int)
        for q in qs.values('subject'):
            subject_map[q['subject']] += 1
        subject_data = [{'name': k, 'value': v} for k, v in subject_map.items()]

        # Difficulty distribution
        difficulty_map = defaultdict(int)
        for q in qs.values('difficulty'):
            if q['difficulty']:
                difficulty_map[q['difficulty']] += 1
        difficulty_data = [{'name': k, 'value': v} for k, v in difficulty_map.items()]

        # Bloom's taxonomy distribution
        bloom_map = defaultdict(int)
        for q in qs.values('bloom_level'):
            if q['bloom_level']:
                bloom_map[q['bloom_level']] += 1
        bloom_data = [{'name': k, 'value': v} for k, v in bloom_map.items()]

        # Department-wise contribution
        dept_map = defaultdict(int)
        for q in qs.values('department'):
            dept = q['department'] or 'Unassigned'
            dept_map[dept] += 1
        dept_data = [{'name': k, 'value': v} for k, v in dept_map.items()]

        # Papers + trend
        papers_qs = QuestionPaper.objects.filter(institution=institution) if institution else QuestionPaper.objects.all()
        total_papers = papers_qs.count()

        date_map = defaultdict(int)
        for p in papers_qs.values('created_at'):
            if p['created_at']:
                date_key = p['created_at'].strftime('%d %b') if hasattr(p['created_at'], 'strftime') else str(p['created_at'])[:10]
                date_map[date_key] += 1
        trend_data = [{'name': k, 'papers': v} for k, v in sorted(date_map.items())]

        return Response({
            'total_questions': total_questions,
            'total_papers': total_papers,
            'subject_data': subject_data,
            'difficulty_data': difficulty_data,
            'bloom_data': bloom_data,
            'dept_data': dept_data,
            'trend_data': trend_data,
        })
