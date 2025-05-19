from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from rest_framework.authtoken.models import Token
from .models import EmailVerificationToken, UserProfile, AuthorProfile, EditorProfile, AdminProfile
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

User = get_user_model()

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['profile_picture']

class AuthorProfileSerializer(serializers.ModelSerializer):
    category_expertise = serializers.ChoiceField(choices=AuthorProfile.EXPERTISE_CHOICES)
    class Meta:
        model = AuthorProfile
        fields = ['bio', 'category_expertise', 'certificates', 'approval_status', 'approval_comment', 'approved_by', 'profile_picture']
        read_only_fields = ['approval_status', 'approval_comment', 'approved_by']

class EditorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EditorProfile
        fields = ['areas_of_oversight', 'management_responsibilities', 'approval_status', 'approval_comment', 'approved_by', 'profile_picture']
        read_only_fields = ['approval_status', 'approval_comment', 'approved_by']

class AdminProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminProfile
        fields = ['approval_document', 'profile_picture']

class UserSerializer(serializers.ModelSerializer):
    password2 = serializers.CharField(write_only=True, required=True)
    # Add extra fields for each role
    profile_picture = serializers.ImageField(write_only=True, required=False)
    bio = serializers.CharField(write_only=True, required=False)
    category_expertise = serializers.ChoiceField(choices=AuthorProfile.EXPERTISE_CHOICES, write_only=True, required=False)
    certificates = serializers.FileField(write_only=True, required=False)
    areas_of_oversight = serializers.CharField(write_only=True, required=False)
    email_verification = serializers.BooleanField(write_only=True, required=False)
    user_management = serializers.BooleanField(write_only=True, required=False)
    article_management = serializers.BooleanField(write_only=True, required=False)
    analytics = serializers.BooleanField(write_only=True, required=False)
    admin_document = serializers.FileField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'password', 'password2',
                  'profile_picture', 'bio', 'category_expertise', 'certificates',
                  'areas_of_oversight', 'email_verification', 'user_management',
                  'article_management', 'analytics', 'admin_document')
        extra_kwargs = {
            'password': {'write_only': True},
            'role': {'required': True}
        }
    
    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        
        # Role-specific validations
        role = data.get('role', '').lower()
        
        if role == 'author':
            if not data.get('bio'):
                raise serializers.ValidationError({"bio": "Bio is required for authors"})
            if not data.get('category_expertise'):
                raise serializers.ValidationError({"category_expertise": "Category expertise is required for authors"})
        
        elif role == 'editor':
            if not data.get('areas_of_oversight'):
                raise serializers.ValidationError({"areas_of_oversight": "Areas of oversight is required for editors"})
            # Check if at least one management responsibility is selected
            if not any([
                data.get('email_verification'),
                data.get('user_management'),
                data.get('article_management'),
                data.get('analytics')
            ]):
                raise serializers.ValidationError({"management_responsibilities": "At least one management responsibility must be selected"})
        
        elif role == 'admin':
            if not data.get('admin_document'):
                raise serializers.ValidationError({"admin_document": "Approval document is required for admin registration"})
        
        return data

    def create(self, validated_data):
        with transaction.atomic():
            password2 = validated_data.pop('password2')
            role = validated_data.get('role')
            # Extract profile fields
            profile_picture = validated_data.pop('profile_picture', None)
            bio = validated_data.pop('bio', None)
            category_expertise = validated_data.pop('category_expertise', None)
            certificates = validated_data.pop('certificates', None)
            areas_of_oversight = validated_data.pop('areas_of_oversight', None)
            email_verification = validated_data.pop('email_verification', False)
            user_management = validated_data.pop('user_management', False)
            article_management = validated_data.pop('article_management', False)
            analytics = validated_data.pop('analytics', False)
            admin_document = validated_data.pop('admin_document', None)

            user = User(
                username=validated_data['username'],
                email=validated_data['email'],
                role=role
            )
            user.set_password(validated_data['password'])
            if role in ['author', 'editor']:
                user.is_active = False
            user.save()

            # Create profile based on role
            if role == 'user':
                UserProfile.objects.create(user=user, profile_picture=profile_picture)
            elif role == 'author':
                AuthorProfile.objects.create(
                    user=user,
                    bio=bio,
                    category_expertise=category_expertise,
                    certificates=certificates,
                    approval_status='pending',
                    profile_picture=profile_picture
                )
            elif role == 'editor':
                # Convert boolean fields to management responsibilities list
                management_responsibilities = []
                if email_verification:
                    management_responsibilities.append('email_verification')
                if user_management:
                    management_responsibilities.append('user_management')
                if article_management:
                    management_responsibilities.append('article_management')
                if analytics:
                    management_responsibilities.append('analytics')

                EditorProfile.objects.create(
                    user=user,
                    areas_of_oversight=areas_of_oversight,
                    management_responsibilities=management_responsibilities,
                    approval_status='pending',
                    profile_picture=profile_picture
                )
            elif role == 'admin':
                AdminProfile.objects.create(
                    user=user, 
                    approval_document=admin_document,
                    profile_picture=profile_picture
                )
            return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    data['user'] = user
                    return data
                else:
                    raise serializers.ValidationError('User account is disabled.')
            else:
                raise serializers.ValidationError('Invalid username or password.')
        else:
            raise serializers.ValidationError('Must include "username" and "password".')


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)
