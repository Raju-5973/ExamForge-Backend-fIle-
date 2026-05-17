from django.contrib import admin
from .models import QuestionPaper

@admin.register(QuestionPaper)
class QuestionPaperAdmin(admin.ModelAdmin):
    list_display = ('subject', 'created_by', 'created_at')
    list_filter = ('subject', 'created_by')
    readonly_fields = ('created_at',)
