from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Article, Comment, ArticleInteraction  # Add ArticleInteraction here
from .serializers import ArticleSerializer, CommentSerializer, ArticleInteractionSerializer, EditorPublishedArticleSerializer  # Add these serializers
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


class FeaturedArticlesViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ArticleSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def add_comment(self, request, pk=None):
        article = self.get_object()
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, article=article)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        article = self.get_object()
        comments = Comment.objects.filter(article=article)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def interact(self, request, pk=None):
        article = self.get_object()
        interaction, created = ArticleInteraction.objects.get_or_create(
            article=article,
            user=request.user,
            defaults={'liked': False, 'disliked': False}
        )

        action = request.data.get('action')
        if action == 'like':
            interaction.liked = not interaction.liked
            interaction.disliked = False
        elif action == 'dislike':
            interaction.disliked = not interaction.disliked
            interaction.liked = False

        interaction.save()
        return Response({
            'liked': interaction.liked,
            'disliked': interaction.disliked
        })

    def get_queryset(self):
        try:
            queryset = Article.objects.filter(status='approved')
            featured = self.request.query_params.get('featured', None)
            if featured is not None:
                # Check if 'featured' field exists in your Article model
                queryset = queryset.filter(featured=True)
            return queryset
        except Exception as e:
            print(f"Error in get_queryset: {str(e)}")
            return Article.objects.none()

class AuthorArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Article.objects.filter(author=self.request.user)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user, status='pending')

    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        article = self.get_object()
        if article.status == 'draft':
            article.status = 'pending'
            article.save()
            return Response({'status': 'submitted for review'})
        return Response({'error': 'Article is not in draft status'},
                       status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def get_status(self, request, pk=None):
        article = self.get_object()
        return Response({
            'status': article.status,
            'editor_comments': article.editor_comments
        })


@api_view(['GET'])
def author_api_overview(request):
    api_urls = {
        'List All Articles': {
            'endpoint': '/accounts/author/drafts/',
            'method': 'GET',
            'description': 'List all draft articles for the author (dashboard)'
        },
        'List Pending Reviews': {
            'endpoint': '/accounts/author/pending-reviews/',
            'method': 'GET',
            'description': 'List all articles under review for the author (dashboard)'
        },
        'List Updates': {
            'endpoint': '/accounts/author/updates/',
            'method': 'GET',
            'description': 'List all published/rejected articles for the author (dashboard)'
        },
        'Create Article': {
            'endpoint': '/api/author/articles/',
            'method': 'POST',
            'fields': {
                'title': 'string',
                'content': 'string',
                'image': 'file (optional)',
                'category': 'integer'
            }
        },
        'View Single Article': {
            'endpoint': '/api/author/articles/<id>/',
            'method': 'GET'
        },
        'Update Article': {
            'endpoint': '/api/author/articles/<id>/',
            'method': 'PUT/PATCH'
        },
        'Delete Article': {
            'endpoint': '/api/author/articles/<id>/',
            'method': 'DELETE'
        },
        'Submit for Review': {
            'endpoint': '/api/author/articles/<id>/submit_for_review/',
            'method': 'POST'
        }
    }
    return Response(api_urls)


class EditorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'editor'

class EditorArticleViewSet(viewsets.ModelViewSet):
    serializer_class = ArticleSerializer
    permission_classes = [EditorPermission]

    def get_queryset(self):
        # Editors can see all articles
        return Article.objects.all()

    @action(detail=True, methods=['post'])
    def review_article(self, request, pk=None):
        article = self.get_object()
        if article.status != 'pending':
            return Response(
                {'error': 'Only pending articles can be reviewed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get review decision and comments from request
        decision = request.data.get('decision')
        comments = request.data.get('editor_comments')

        if decision not in ['approved', 'rejected']:
            return Response(
                {'error': 'Invalid decision'},
                status=status.HTTP_400_BAD_REQUEST
            )

        article.status = decision
        article.editor_comments = comments
        article.save()

        return Response({
            'status': article.status,
            'editor_comments': article.editor_comments
        })

class PublishedArticlesListView(APIView):
    # No permission_classes needed for public access
    def get(self, request):
        articles = Article.objects.filter(status='approved').order_by('-created_at') # Fetch approved articles, order by creation date
        # Use EditorPublishedArticleSerializer to serialize the data
        data = EditorPublishedArticleSerializer(articles, many=True).data
        return Response(data)

class EditorPublishedArticlesView(APIView):
    permission_classes = [IsAuthenticated, EditorPermission]
    
    def get(self, request):
        # Get all articles that have been approved by editors
        articles = Article.objects.filter(status='approved').order_by('-created_at')
        
        # Serialize the articles with detailed information
        serializer = EditorPublishedArticleSerializer(articles, many=True)
        
        return Response({
            'articles': serializer.data,
            'total_count': articles.count()
        })
