from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count
from datetime import datetime, timedelta
from rest_framework.reverse import reverse

from .models import AdminLog
from .serializers import AdminLogSerializer, AdminArticleSerializer, AdminUserSerializer, AuthorProfileSerializer, EditorProfileSerializer, RoleChangeRequestSerializer
from news.models import Article
from accounts.models import CustomUser, AuthorProfile, EditorProfile, RoleChangeRequest

class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'admin'

class DashboardView(APIView):
    permission_classes = [AdminPermission]

    def get(self, request):
        total_users = CustomUser.objects.count()
        active_authors = CustomUser.objects.filter(role='author', is_active=True).count()
        pending_role_requests = RoleChangeRequest.objects.filter(status='pending').count()

        # Dummy trend values (replace with real calculations if needed)
        total_users_trend = "+12% from last month"
        active_authors_trend = "+8% from last month"
        pending_role_requests_trend = "-5% from last month"

        # Recent Activities: user_login, role_change_request, new_user_registration
        recent_logs = AdminLog.objects.filter(
            action__in=['user_login', 'role_change_request', 'new_user_registration']
        ).order_by('-timestamp')[:10]
        activities = []
        for log in recent_logs:
            if log.action == 'user_login':
                activity_title = 'User Login'
                status = 'Completed'
                activity = {
                    "activity_title": activity_title,
                    "user_name": log.user.username,
                    "role": getattr(log.user, 'role', ''),
                    "date": log.timestamp.strftime("%b %d, %Y"),
                    "status": status
                }
            elif log.action == 'role_change_request':
                activity_title = 'Role Change Request'
                status = 'Pending'
                # Try to get requested_role from the latest RoleChangeRequest for this user
                requested_role = None
                from accounts.models import RoleChangeRequest as RCR
                rcr = RCR.objects.filter(user=log.user).order_by('-request_date').first()
                if rcr:
                    requested_role = rcr.requested_role
                activity = {
                    "activity_title": activity_title,
                    "user_name": log.user.username,
                    "role": getattr(log.user, 'role', ''),
                    "requested_role": requested_role,
                    "date": log.timestamp.strftime("%b %d, %Y"),
                    "status": status
                }
            elif log.action == 'new_user_registration':
                activity_title = 'New User Registration'
                status = 'Completed'
                activity = {
                    "activity_title": activity_title,
                    "user_name": log.user.username,
                    "role": getattr(log.user, 'role', ''),
                    "date": log.timestamp.strftime("%b %d, %Y"),
                    "status": status
                }
            else:
                activity_title = log.action.replace('_', ' ').title()
                status = 'Completed'
                activity = {
                    "activity_title": activity_title,
                    "user_name": log.user.username,
                    "role": getattr(log.user, 'role', ''),
                    "date": log.timestamp.strftime("%b %d, %Y"),
                    "status": status
                }
            activities.append(activity)

        return Response({
            "stats": [
                {
                    "title": "Total Users",
                    "value": total_users,
                    "trend": total_users_trend,
                    "trendPositive": True
                },
                {
                    "title": "Active Authors",
                    "value": active_authors,
                    "trend": active_authors_trend,
                    "trendPositive": True
                },
                {
                    "title": "Pending Role Requests",
                    "value": pending_role_requests,
                    "trend": pending_role_requests_trend,
                    "trendPositive": False
                }
            ],
            "recent_activities": activities
        })

class AdminArticleViewSet(viewsets.ModelViewSet):
    queryset = Article.objects.all()
    serializer_class = AdminArticleSerializer
    permission_classes = [AdminPermission]

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        article = self.get_object()
        status = request.data.get('status')
        if status in ['draft', 'pending', 'approved', 'rejected']:
            article.status = status
            article.save()
            
            # Log the action
            AdminLog.objects.create(
                action='change_article_status',
                user=request.user,
                content_type='article',
                object_id=article.id,
                description=f'Changed article status to {status}'
            )
            
            return Response({'status': status})
        return Response({'error': 'Invalid status'}, status=status.HTTP_400_BAD_REQUEST)

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [AdminPermission]

    def list(self, request, *args, **kwargs):
        users = self.get_queryset()
        user_data = []
        for user in users:
            user_data.append({
                "name": user.username,
                "email": user.email,
                "current_role": user.role.capitalize()
            })
        return Response(user_data)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        
        # Log the action
        AdminLog.objects.create(
            action='toggle_user_active',
            user=request.user,
            content_type='user',
            object_id=user.id,
            description=f'{"Activated" if user.is_active else "Deactivated"} user account'
        )
        
        return Response({'is_active': user.is_active})

    @action(detail=True, methods=['post'])
    def change_role(self, request, pk=None):
        user = self.get_object()
        role = request.data.get('role')
        valid_roles = ['reader', 'author', 'editor']
        if role not in valid_roles:
            return Response({'error': 'Invalid role'}, status=status.HTTP_400_BAD_REQUEST)
        old_role = user.role
        user.role = role
        user.save()
        AdminLog.objects.create(
            action='change_user_role',
            user=request.user,
            content_type='user',
            object_id=user.id,
            description=f'Changed user role from {old_role} to {role}'
        )
        return Response({'role': user.role})

class AdminLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AdminLog.objects.all()
    serializer_class = AdminLogSerializer
    permission_classes = [AdminPermission]

class ApprovalRequestAuthorsView(APIView):
    permission_classes = [AdminPermission]
    def get(self, request):
        author_pending = AuthorProfile.objects.filter(approval_status='pending')
        authors = AuthorProfileSerializer(author_pending, many=True).data
        return Response({'pending_authors': authors})

class ApprovalRequestEditorsView(APIView):
    permission_classes = [AdminPermission]
    def get(self, request):
        editor_pending = EditorProfile.objects.filter(approval_status='pending')
        editors = EditorProfileSerializer(editor_pending, many=True).data
        return Response({'pending_editors': editors})

class ApproveAuthorView(APIView):
    permission_classes = [AdminPermission]
    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action')  # 'approve' or 'reject'
        comment = request.data.get('comment', '')
        try:
            user = CustomUser.objects.get(id=user_id, role='author')
            profile = AuthorProfile.objects.get(user=user)
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
            return Response({'success': f'Author request {action}d.'})
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        except AuthorProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)

class ApproveEditorView(APIView):
    permission_classes = [AdminPermission]
    def post(self, request):
        user_id = request.data.get('user_id')
        action = request.data.get('action')  # 'approve' or 'reject'
        comment = request.data.get('comment', '')
        try:
            user = CustomUser.objects.get(id=user_id, role='editor')
            profile = EditorProfile.objects.get(user=user)
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
            return Response({'success': f'Editor request {action}d.'})
        except CustomUser.DoesNotExist:
            return Response({'error': 'User not found'}, status=404)
        except EditorProfile.DoesNotExist:
            return Response({'error': 'Profile not found'}, status=404)

class AccountsApiRootView(APIView):
    def get(self, request, format=None):
        return Response({
            'register': reverse('register', request=request),
            'login': reverse('login', request=request),
            'password-reset': reverse('password-reset', request=request),
            'password-reset-confirm': reverse('password-reset-confirm', request=request),
            'test-connection': reverse('test-connection', request=request),
            'social': reverse('social_login', request=request),
            # Add more as needed
        })

class AdminPanelApiRootView(APIView):
    def get(self, request, format=None):
        return Response({
            'dashboard': reverse('admin_panel:admin-dashboard', request=request),
            'articles': request.build_absolute_uri(reverse('admin_panel:articles-list', request=request)),
            'users': request.build_absolute_uri(reverse('admin_panel:users-list', request=request)),
            'logs': request.build_absolute_uri(reverse('admin_panel:logs-list', request=request)),
            'approval-requests-authors': reverse('admin_panel:approval-requests-authors', request=request),
            'approval-requests-editors': reverse('admin_panel:approval-requests-editors', request=request),
            'approve-author': reverse('admin_panel:approve-author', request=request),
            'approve-editor': reverse('admin_panel:approve-editor', request=request),
        })

class RoleChangeRequestViewSet(viewsets.ModelViewSet):
    queryset = RoleChangeRequest.objects.all()
    serializer_class = RoleChangeRequestSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated()]
        return [AdminPermission()]

    def create(self, request, *args, **kwargs):
        user = request.user
        requested_role = request.data.get('requested_role')
        # Prevent duplicate pending requests for the same role
        if RoleChangeRequest.objects.filter(user=user, requested_role=requested_role, status='pending').exists():
            return Response(
                {'error': f'You already have a pending request for the role "{requested_role}". Please wait for it to be processed.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().create(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        requests = self.get_queryset().order_by('-request_date')
        data = []
        for req in requests:
            data.append({
                "id": req.id,
                "user_name": req.user.username,
                "role": req.user.role,
                "requested_role": req.requested_role,
                "date": req.request_date.strftime("%b %d, %Y"),
                "action": "accept?reject"
            })
        return Response(data)

    def post(self, request, *args, **kwargs):
        # Admin can approve or reject a role change request from the list endpoint
        req_id = request.data.get('id')
        action = request.data.get('action')  # 'accept' or 'reject'
        if not req_id or action not in ['accept', 'reject']:
            return Response({'error': 'id and action (accept or reject) are required.'}, status=400)
        try:
            req = RoleChangeRequest.objects.get(id=req_id)
        except RoleChangeRequest.DoesNotExist:
            return Response({'error': 'Role change request not found.'}, status=404)
        if req.status != 'pending':
            return Response({'error': 'Request already processed'}, status=400)
        if action == 'accept':
            req.status = 'approved'
            req.decision_date = datetime.now()
            req.save()
            user = req.user
            user.role = req.requested_role
            user.save()
            return Response({'status': 'approved'})
        else:
            req.status = 'rejected'
            req.decision_date = datetime.now()
            req.save()
            return Response({'status': 'rejected'})

@api_view(['GET', 'POST'])
@permission_classes([AdminPermission])
def role_change_action(request):
    if request.method == 'GET':
        requests = RoleChangeRequest.objects.filter(status='pending').order_by('-request_date')
        data = []
        for req in requests:
            data.append({
                "id": req.id,
                "user_name": req.user.username,
                "role": req.user.role,
                "requested_role": req.requested_role,
                "date": req.request_date.strftime("%b %d, %Y"),
                "action": "accept?reject"
            })
        return Response(data)
    # POST method for approve/reject
    req_id = request.data.get('id')
    action = request.data.get('action')  # 'accept' or 'reject'
    if not req_id or action not in ['accept', 'reject']:
        return Response({'error': 'id and action (accept or reject) are required.'}, status=400)
    try:
        req = RoleChangeRequest.objects.get(id=req_id)
    except RoleChangeRequest.DoesNotExist:
        return Response({'error': 'Role change request not found.'}, status=404)
    if req.status != 'pending':
        return Response({'error': 'Request already processed'}, status=400)
    if action == 'accept':
        req.status = 'approved'
        req.decision_date = datetime.now()
        req.save()
        user = req.user
        user.role = req.requested_role
        user.save()
        return Response({'status': 'approved'})
    else:
        req.status = 'rejected'
        req.decision_date = datetime.now()
        req.save()
        return Response({'status': 'rejected'})
