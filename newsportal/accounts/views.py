from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, LoginSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer, AuthorProfileSerializer, EditorProfileSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework import permissions
from .models import AuthorProfile, EditorProfile, CustomUser
from rest_framework.reverse import reverse
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from news.models import Article, Category
from news.serializers import ArticleSerializer, EditorDashboardArticleSerializer, EditorPublishedArticleSerializer, EditorPendingReviewArticleSerializer, AuthorDraftArticleSerializer, AuthorPendingReviewArticleSerializer, AuthorUpdatesArticleSerializer
from datetime import timedelta
from django.utils import timezone
from admin_panel.models import AdminLog

User = get_user_model()

class RegisterView(APIView):
    def get(self, request):
        return Response({
            "message": "Please send a POST request with the following fields to register",
            "required_fields": {
                "username": "your username",
                "email": "your email",
                "password": "your password",
                "password2": "confirm password",
                "role": "select one: user, author, editor, or admin"
            }
        })

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            # Log new user registration
            AdminLog.objects.create(
                action='new_user_registration',
                user=user,
                content_type='user',
                object_id=user.id,
                description=f'User {user.username} registered'
            )
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'role': user.role
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# For Login
class LoginView(APIView):
    def get(self, request):
        # Return a simple response for GET requests
        return Response({
            "message": "Please send a POST request with username and password to login",
            "required_fields": {
                "username": "your username",
                "password": "your password"
            }
        })

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, _ = Token.objects.get_or_create(user=user)
            # Log login event
            AdminLog.objects.create(
                action='user_login',
                user=user,
                content_type='user',
                object_id=user.id,
                description=f'{user.role.capitalize()} {user.username} logged in'
            )
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'role': user.role
            }, status=status.HTTP_200_OK)
            
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# For Password Reset
class PasswordResetView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            try:
                user = User.objects.get(email=email)
                # Generate token
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                
                # Create reset link
                reset_link = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}"
                
                # Send email
                send_mail(
                    'Password Reset for NepNews',
                    f'Click the following link to reset your password: {reset_link}',
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                return Response({'message': 'Password reset email sent successfully'})
            except User.DoesNotExist:
                return Response({'error': 'No user found with this email'}, 
                              status=status.HTTP_404_NOT_FOUND)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# For Password Reset Confirm
class PasswordResetConfirmView(APIView):
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            try:
                uid = force_str(urlsafe_base64_decode(serializer.validated_data['uid']))
                user = User.objects.get(pk=uid)
                
                # Verify token
                if default_token_generator.check_token(user, serializer.validated_data['token']):
                    user.set_password(serializer.validated_data['new_password'])
                    user.save()
                    return Response({'message': 'Password reset successful'})
                else:
                    return Response({'error': 'Invalid or expired token'}, 
                                  status=status.HTTP_400_BAD_REQUEST)
            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response({'error': 'Invalid reset link'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TestConnectionView(APIView):
    def get(self, request):
        return Response({"message": "Backend is connected!"}, status=status.HTTP_200_OK)

class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class ApprovalRequestListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    def get(self, request):
        author_pending = AuthorProfile.objects.filter(approval_status='pending')
        editor_pending = EditorProfile.objects.filter(approval_status='pending')
        authors = AuthorProfileSerializer(author_pending, many=True).data
        editors = EditorProfileSerializer(editor_pending, many=True).data
        return Response({
            'pending_authors': authors,
            'pending_editors': editors
        })

class ApproveRequestView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    def post(self, request):
        user_id = request.data.get('user_id')
        role = request.data.get('role')
        action = request.data.get('action')  # 'approve' or 'reject'
        comment = request.data.get('comment', '')
        try:
            user = CustomUser.objects.get(id=user_id, role=role)
            if role == 'author':
                profile = AuthorProfile.objects.get(user=user)
            elif role == 'editor':
                profile = EditorProfile.objects.get(user=user)
            else:
                return Response({'error': 'Invalid role'}, status=400)
            if action == 'approve':
                profile.approval_status = 'approved'
                user.is_active = True
            elif action == 'reject':
                profile.approval_status = 'rejected'
                user.is_active = False
            else:
                return Response({'error': 'Invalid action'}, status=400)
            profile.approval_comment = comment
            profile.approved_by = request.user
            profile.save()
            user.save()
            return Response({'success': f'{role.capitalize()} request {action}d.'})
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        except (AuthorProfile.DoesNotExist, EditorProfile.DoesNotExist):
            return Response({'error': 'Profile not found'}, status=404)

class AccountsApiRootView(APIView):
    def get(self, request, format=None):
        return Response({
            'register': reverse('register', request=request),
            'login': reverse('login', request=request),
            'logout': reverse('logout', request=request),
            'password-reset': reverse('password-reset', request=request),
            'password-reset-confirm': reverse('password-reset-confirm', request=request),
            'test-connection': reverse('test-connection', request=request),
            'social': reverse('google_login', request=request),
        })

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        # If signup, set role to 'user'
        if response.status_code == 201:
            user = CustomUser.objects.get(email=response.data['user']['email'])
            if user.role != 'user':
                user.role = 'user'
                user.save()
        # If login, only allow if role is 'user'
        if response.status_code == 200:
            user = CustomUser.objects.get(email=response.data['user']['email'])
            if user.role != 'user':
                return Response({'error': 'Google login is only allowed for users with role "user".'}, status=status.HTTP_403_FORBIDDEN)
        return response

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # Delete the auth token
            request.user.auth_token.delete()
            return Response({
                'message': 'Successfully logged out.'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Error during logout.'
            }, status=status.HTTP_400_BAD_REQUEST)

class EditorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'role', None) == 'editor'

class EditorDashboardView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def get(self, request):
        published_articles = Article.objects.filter(status='approved').count()
        rejected_articles = Article.objects.filter(status='rejected').count()
        pending_reviews = Article.objects.filter(status='pending').count()
        recent_articles = Article.objects.order_by('-created_at')[:7]
        recent_data = AuthorUpdatesArticleSerializer(recent_articles, many=True).data
        return Response({
            'published_articles': published_articles,
            'rejected_articles': rejected_articles,
            'pending_reviews': pending_reviews,
            'recent_articles': recent_data
        })

class EditorPublishedArticlesView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def get(self, request):
        articles = Article.objects.filter(status='approved')
        data = EditorPublishedArticleSerializer(articles, many=True).data
        return Response(data)

class EditorPendingReviewsView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def get(self, request):
        articles = Article.objects.filter(status='pending')
        data = EditorPendingReviewArticleSerializer(articles, many=True).data
        return Response(data)

class EditorArticleDetailView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def get(self, request, pk):
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        data = ArticleSerializer(article).data
        return Response(data)

class EditorEditArticleView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def put(self, request, pk):
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        serializer = ArticleSerializer(article, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

class EditorApproveArticleView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def post(self, request, pk):
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        article.status = 'approved'
        article.save()
        return Response({'status': 'approved'})

class EditorRequestRevisionView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def post(self, request, pk):
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        article.status = 'rejected'
        article.editor_comments = request.data.get('editor_comments', '')
        article.save()
        return Response({'status': 'rejected', 'editor_comments': article.editor_comments})

class EditorUnpublishArticleView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    def post(self, request, pk):
        try:
            article = Article.objects.get(pk=pk)
        except Article.DoesNotExist:
            return Response({'error': 'Article not found'}, status=404)
        article.status = 'draft'
        article.save()
        return Response({'status': 'draft'})

class AuthorExpertiseChoicesView(APIView):
    def get(self, request):
        from .models import AuthorProfile
        return Response({
            'expertise_choices': [
                {'value': choice[0], 'label': choice[1]} for choice in AuthorProfile.EXPERTISE_CHOICES
            ]
        })

class AuthorDraftsSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        now = timezone.now()
        last_month = now - timedelta(days=30)
        last_week = now - timedelta(days=7)
        # Drafts
        total_drafts = Article.objects.filter(author=user, status='draft').count()
        last_month_drafts = Article.objects.filter(author=user, status='draft', created_at__gte=last_month).count()
        # Submitted Drafts
        submitted_drafts = Article.objects.filter(author=user, status='pending').count()
        last_month_submitted = Article.objects.filter(author=user, status='pending', created_at__gte=last_month).count()
        # Pending Approval
        pending_approval = Article.objects.filter(author=user, status='pending').count()
        last_week_pending = Article.objects.filter(author=user, status='pending', created_at__gte=last_week).count()
        return Response({
            'total_drafts': total_drafts,
            'total_drafts_delta': total_drafts - last_month_drafts,
            'submitted_drafts': submitted_drafts,
            'submitted_drafts_delta': submitted_drafts - last_month_submitted,
            'pending_approval': pending_approval,
            'pending_approval_delta': pending_approval - last_week_pending,
        })

class AuthorReviewsSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        now = timezone.now()
        last_month = now - timedelta(days=30)
        last_week = now - timedelta(days=7)
        # Submitted Articles
        submitted_articles = Article.objects.filter(author=user, status='pending').count()
        last_month_submitted = Article.objects.filter(author=user, status='pending', created_at__gte=last_month).count()
        # Under Review
        under_review = Article.objects.filter(author=user, status='pending').count()
        last_month_under_review = Article.objects.filter(author=user, status='pending', created_at__gte=last_month).count()
        # Awaiting Feedback (rejected in last week)
        awaiting_feedback = Article.objects.filter(author=user, status='rejected', updated_at__gte=last_week).count()
        last_week_awaiting = Article.objects.filter(author=user, status='rejected', updated_at__gte=last_week).count()
        return Response({
            'submitted_articles': submitted_articles,
            'submitted_articles_delta': submitted_articles - last_month_submitted,
            'under_review': under_review,
            'under_review_delta': under_review - last_month_under_review,
            'awaiting_feedback': awaiting_feedback,
            'awaiting_feedback_delta': awaiting_feedback - last_week_awaiting,
        })

class AuthorUpdatesSummaryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        now = timezone.now()
        last_month = now - timedelta(days=30)
        last_week = now - timedelta(days=7)
        # Published Articles
        published_articles = Article.objects.filter(author=user, status='approved').count()
        last_month_published = Article.objects.filter(author=user, status='approved', created_at__gte=last_month).count()
        # Rejected Articles
        rejected_articles = Article.objects.filter(author=user, status='rejected').count()
        last_month_rejected = Article.objects.filter(author=user, status='rejected', created_at__gte=last_month).count()
        # Article Views (sum of all views for author's articles)
        from news.models import ArticleInteraction
        article_ids = Article.objects.filter(author=user).values_list('id', flat=True)
        article_views = ArticleInteraction.objects.filter(article_id__in=article_ids).count()
        last_week_views = ArticleInteraction.objects.filter(article_id__in=article_ids, created_at__gte=last_week).count()
        return Response({
            'published_articles': published_articles,
            'published_articles_delta': published_articles - last_month_published,
            'rejected_articles': rejected_articles,
            'rejected_articles_delta': rejected_articles - last_month_rejected,
            'article_views': article_views,
            'article_views_delta': article_views - last_week_views,
        })

class AuthorDraftsListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        drafts = Article.objects.filter(author=user, status='draft').order_by('-created_at')
        data = AuthorDraftArticleSerializer(drafts, many=True).data
        return Response(data)

class AuthorPendingReviewsListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        pending = Article.objects.filter(author=user, status='pending').order_by('-created_at')
        data = AuthorPendingReviewArticleSerializer(pending, many=True).data
        return Response(data)

class AuthorUpdatesListView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        updates = Article.objects.filter(author=user, status__in=['approved', 'rejected']).order_by('-created_at')
        data = AuthorUpdatesArticleSerializer(updates, many=True).data
        return Response(data)

class AuthorDashboardView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        published_articles = Article.objects.filter(author=user, status='approved').count()
        rejected_articles = Article.objects.filter(author=user, status='rejected').count()
        pending_reviews = Article.objects.filter(author=user, status='pending').count()
        recent_articles = Article.objects.filter(author=user).order_by('-created_at')[:7]
        recent_data = AuthorUpdatesArticleSerializer(recent_articles, many=True).data
        # Remove 'views' from each article dict
        for article in recent_data:
            if 'views' in article:
                del article['views']
            # Add 'content' field
            article['content'] = article.get('content', '')
        return Response({
            'published_articles': published_articles,
            'rejected_articles': rejected_articles,
            'pending_reviews': pending_reviews,
            'recent_articles': recent_data
        })

# New public view for published articles
class PublishedArticlesListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        # Get all published articles (status='approved')
        articles = Article.objects.filter(status='approved').order_by('-created_at')

        # Serialize the articles with necessary fields
        data = []
        for article in articles:
            article_data = {
                'id': article.id,
                'title': article.title,
                'description': article.content,  # Changed from article.description
                'category': article.category.name,
                'author': article.author.username,
                'created_at': article.created_at.strftime("%b %d, %Y"),
                'image': request.build_absolute_uri(article.image.url) if article.image else None,
            }
            data.append(article_data)

        return Response(data)