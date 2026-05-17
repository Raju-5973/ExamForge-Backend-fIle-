from django.contrib import admin
from .models import Question

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('subject', 'department', 'difficulty', 'marks', 'created_by', 'created_at')
    list_filter = ('subject', 'department', 'difficulty', 'created_by')
    search_fields = ('text', 'subject')
