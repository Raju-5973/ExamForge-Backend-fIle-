from django.db import models
from django.contrib.auth.models import User
from questions.models import Question

class QuestionPaper(models.Model):
    subject = models.CharField(max_length=100)
    institution = models.ForeignKey('users.Institution', on_delete=models.CASCADE, related_name='papers', blank=True, null=True)
    questions = models.ManyToManyField(Question, related_name='papers')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='papers')
    created_at = models.DateTimeField(auto_now_add=True)
    distribution = models.JSONField(help_text="Marks distribution configuration")

    def __str__(self):
        return f"{self.subject} Paper by {self.created_by.email} - {self.created_at.strftime('%Y-%m-%d')}"

class Blueprint(models.Model):
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True, null=True)
    institution = models.ForeignKey('users.Institution', on_delete=models.CASCADE, related_name='blueprints', blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blueprints')
    created_at = models.DateTimeField(auto_now_add=True)
    total_marks = models.IntegerField(default=100)
    duration_minutes = models.IntegerField(default=180)
    
    # Store complex configurations in JSON format
    # structure: { unit_weightage: {1: 20, 2: 20...}, bloom_distribution: {"Remember": 10, ...}, difficulty: {"Easy": 30...} }
    configuration = models.JSONField(default=dict, help_text="Blueprint configuration rules")

    def __str__(self):
        return f"{self.name} - {self.subject}"

class ApprovalWorkflow(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('pending_hod', 'Pending HOD Approval'),
        ('pending_controller', 'Pending Exam Controller Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    paper = models.OneToOneField(QuestionPaper, on_delete=models.CASCADE, related_name='approval')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='submitted_approvals')
    submitted_at = models.DateTimeField(auto_now_add=True)
    hod_reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='hod_approvals')
    hod_reviewed_at = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True, null=True)
    controller_reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='controller_approvals')
    controller_reviewed_at = models.DateTimeField(null=True, blank=True)
    controller_remarks = models.TextField(blank=True, null=True)
    institution = models.ForeignKey('users.Institution', on_delete=models.CASCADE, null=True, blank=True, related_name='approvals')

    def __str__(self):
        return f"Approval: {self.paper.subject} - {self.status}"

class Notification(models.Model):
    TYPE_CHOICES = (
        ('approval_submitted', 'Paper Submitted for Approval'),
        ('approval_approved', 'Paper Approved'),
        ('approval_rejected', 'Paper Rejected'),
        ('info', 'General Info'),
    )
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='info')
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    related_paper = models.ForeignKey(QuestionPaper, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"[{self.notification_type}] → {self.recipient.email}"

    class Meta:
        ordering = ['-created_at']
