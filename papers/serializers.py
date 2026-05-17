from rest_framework import serializers
from .models import QuestionPaper
from questions.serializers import QuestionSerializer

class QuestionPaperSerializer(serializers.ModelSerializer):
    # For nested display in GET
    questions_detail = QuestionSerializer(source='questions', many=True, read_only=True)
    
    class Meta:
        model = QuestionPaper
        fields = ('id', 'subject', 'questions', 'questions_detail', 'distribution', 'created_by', 'created_at')
        read_only_fields = ('id', 'created_by', 'created_at')

    def validate_distribution(self, value):
        if not value:
            raise serializers.ValidationError("Distribution cannot be empty.")
        for item in value:
            if 'marks' not in item or 'count' not in item:
                raise serializers.ValidationError("Each distribution item must have marks and count.")
            if item['marks'] <= 0 or item['count'] <= 0:
                raise serializers.ValidationError("Marks and count must be positive.")
        return value

    def validate(self, data):
        if not data.get('questions'):
            raise serializers.ValidationError("Question paper must have at least one question.")
        return data
