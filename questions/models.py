from django.db import models
from django.contrib.auth.models import User

class Question(models.Model):
    DIFFICULTY_CHOICES = (
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    )
    
    text = models.TextField()
    subject = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    marks = models.IntegerField()
    sub_topic = models.CharField(max_length=150, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated tags")
    department = models.CharField(max_length=100, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.difficulty} ({self.marks} marks)"
