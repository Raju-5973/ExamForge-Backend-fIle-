from django.db import models
from django.contrib.auth.models import User
from questions.models import Question

class QuestionPaper(models.Model):
    subject = models.CharField(max_length=100)
    questions = models.ManyToManyField(Question, related_name='papers')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='papers')
    created_at = models.DateTimeField(auto_now_add=True)
    distribution = models.JSONField(help_text="Marks distribution configuration")

    def __str__(self):
        return f"{self.subject} Paper by {self.created_by.email} - {self.created_at.strftime('%Y-%m-%d')}"
