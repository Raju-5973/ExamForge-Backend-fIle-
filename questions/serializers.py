from rest_framework import serializers
from .models import Question

class QuestionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.ReadOnlyField(source='created_by.first_name')

    class Meta:
        model = Question
        fields = ('id', 'text', 'subject', 'difficulty', 'marks', 'sub_topic', 'tags', 'department', 'created_by', 'created_by_name', 'created_at')
        read_only_fields = ('id', 'created_by', 'created_by_name', 'created_at', 'department')

    def validate_marks(self, value):
        if value <= 0:
            raise serializers.ValidationError("Marks must be a positive integer.")
        return value

    def validate_text(self, value):
        if not value.strip():
            raise serializers.ValidationError("Question text cannot be empty.")
        return value
