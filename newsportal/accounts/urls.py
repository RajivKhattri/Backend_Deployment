from django.urls import path, include
from .views import (
    RegisterView, LoginView, PasswordResetView, PasswordResetConfirmView, TestConnectionView, AccountsApiRootView, LogoutView,
    EditorDashboardView, EditorPublishedArticlesView, EditorPendingReviewsView, EditorArticleDetailView, EditorEditArticleView, EditorApproveArticleView, EditorRequestRevisionView, EditorUnpublishArticleView, GoogleLogin, AuthorExpertiseChoicesView, AuthorDraftsSummaryView, AuthorReviewsSummaryView, AuthorUpdatesSummaryView, AuthorDraftsListView, AuthorPendingReviewsListView, AuthorUpdatesListView, AuthorDashboardView, PublishedArticlesListView
)
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter

urlpatterns = [
    path('', AccountsApiRootView.as_view(), name='accounts-api-root'),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('test-connection/', TestConnectionView.as_view(), name='test-connection'),
    path('author/expertise-choices/', AuthorExpertiseChoicesView.as_view(), name='author-expertise-choices'),
    path('editor/dashboard/', EditorDashboardView.as_view(), name='editor-dashboard'),
    path('editor/published-articles/', EditorPublishedArticlesView.as_view(), name='editor-published-articles'),
    path('editor/pending-reviews/', EditorPendingReviewsView.as_view(), name='editor-pending-reviews'),
    path('editor/article/<int:pk>/', EditorArticleDetailView.as_view(), name='editor-article-detail'),
    path('editor/article/<int:pk>/edit/', EditorEditArticleView.as_view(), name='editor-article-edit'),
    path('editor/article/<int:pk>/approve/', EditorApproveArticleView.as_view(), name='editor-article-approve'),
    path('editor/article/<int:pk>/request-revision/', EditorRequestRevisionView.as_view(), name='editor-article-request-revision'),
    path('editor/article/<int:pk>/unpublish/', EditorUnpublishArticleView.as_view(), name='editor-article-unpublish'),
    path('social/', include('dj_rest_auth.registration.urls')),
    path('social/login/', GoogleLogin.as_view(), name='google_login'),
    path('author/dashboard/drafts-summary/', AuthorDraftsSummaryView.as_view(), name='author-drafts-summary'),
    path('author/dashboard/reviews-summary/', AuthorReviewsSummaryView.as_view(), name='author-reviews-summary'),
    path('author/dashboard/updates-summary/', AuthorUpdatesSummaryView.as_view(), name='author-updates-summary'),
    path('author/drafts/', AuthorDraftsListView.as_view(), name='author-drafts-list'),
    path('author/pending-reviews/', AuthorPendingReviewsListView.as_view(), name='author-pending-reviews-list'),
    path('author/updates/', AuthorUpdatesListView.as_view(), name='author-updates-list'),
    path('author/dashboard/', AuthorDashboardView.as_view(), name='author-dashboard'),
    path('published-articles/', PublishedArticlesListView.as_view(), name='published-articles-list'),
]