from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
from django.core.mail import send_mail
from django.conf import settings

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('author', 'Author'),
        ('editor', 'Editor'),
        ('admin', 'Admin'),
    ]
    
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    is_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username

# Profile for regular User
class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='user_profile')
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

# Profile for Author
class AuthorProfile(models.Model):
    EXPERTISE_CHOICES = [
        ('News', 'News'),
        ('Politics', 'Politics'),
        ('Sports', 'Sports'),
        ('Entertainment', 'Entertainment'),
        ('Technology', 'Technology'),
        ('Health', 'Health'),
        ('Science', 'Science'),
        ('Business', 'Business'),
    ]
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='author_profile')
    bio = models.TextField(blank=True)
    category_expertise = models.CharField(max_length=50, choices=EXPERTISE_CHOICES)
    certificates = models.FileField(upload_to='author_certificates/', blank=True, null=True)
    approval_status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    approval_comment = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_authors')

# Profile for Editor
class EditorProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='editor_profile')
    areas_of_oversight = models.TextField(blank=True)
    management_responsibilities = models.JSONField(default=list, blank=True)  # Store as list of strings
    approval_status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    approval_comment = models.TextField(blank=True, null=True)
    approved_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_editors')

# Profile for Admin
class AdminProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')
    approval_document = models.FileField(upload_to='admin_approval_docs/', blank=True, null=True)

class EmailVerificationToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def send_verification_email(self, request):
        verify_url = f"{settings.FRONTEND_URL}/verify-email/{self.token}/"
        subject = "Verify Your Email Address"
        message = f"Click the link to verify your email: {verify_url}"
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.user.email])

class PasswordResetToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"PasswordResetToken for {self.user.username}"