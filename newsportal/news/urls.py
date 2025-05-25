from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthorArticleViewSet, author_api_overview, FeaturedArticlesViewSet, EditorArticleViewSet, EditorPublishedArticlesView

router = DefaultRouter()
router.register(r'articles', FeaturedArticlesViewSet, basename='articles')
router.register(r'author/articles', AuthorArticleViewSet, basename='author-articles')
router.register(r'editor/articles', EditorArticleViewSet, basename='editor-articles')

urlpatterns = [
    path('', include(router.urls)),
    path('author/overview/', author_api_overview, name='author-api-overview'),
    path('editor/published/', EditorPublishedArticlesView.as_view(), name='editor-published-articles'),
]