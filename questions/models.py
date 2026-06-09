from django.db import models
from django.contrib.auth.models import User

class Question(models.Model):
    DIFFICULTY_CHOICES = (
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    )
    
    BLOOM_CHOICES = (
        ('Remember', 'Remember'),
        ('Understand', 'Understand'),
        ('Apply', 'Apply'),
        ('Analyze', 'Analyze'),
        ('Evaluate', 'Evaluate'),
        ('Create', 'Create'),
    )

    text = models.TextField()
    subject = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    marks = models.IntegerField()
    unit = models.IntegerField(blank=True, null=True, help_text="Unit number (1-5)")
    bloom_level = models.CharField(max_length=50, choices=BLOOM_CHOICES, blank=True, null=True)
    co_mapping = models.CharField(max_length=50, blank=True, null=True, help_text="Course Outcome (e.g. CO1, CO2)")
    po_mapping = models.CharField(max_length=100, blank=True, null=True, help_text="Program Outcomes (comma separated)")
    image_url = models.URLField(max_length=500, blank=True, null=True)
    
    sub_topic = models.CharField(max_length=150, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated tags")
    department = models.CharField(max_length=100, blank=True, null=True)
    institution = models.ForeignKey('users.Institution', on_delete=models.CASCADE, related_name='questions', blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='questions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.subject} - {self.difficulty} ({self.marks} marks) - {self.institution.name if self.institution else 'No Inst'}"
