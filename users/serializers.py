from rest_framework import serializers
from django.contrib.auth.models import User
from .models import UserProfile

class UserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(write_only=True)
    name = serializers.CharField(write_only=True)
    username = serializers.CharField(write_only=True)
    department = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'name', 'role', 'password', 'department')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        role = validated_data.pop('role', 'staff')
        username = validated_data.pop('username', '')
        name = validated_data.pop('name', '')
        department = validated_data.pop('department', '')
        email = validated_data.get('email')
        
        # Use email as the internal unique username to avoid restrictions
        user = User.objects.create_user(
            username=email, 
            email=email,
            password=validated_data['password'],
            first_name=name
        )
        UserProfile.objects.create(
            user=user, 
            role=role, 
            display_username=username,
            department=department
        )
        return user
