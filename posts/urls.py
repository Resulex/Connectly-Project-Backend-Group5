from django.urls import path
from .views import (
    PostListCreate, PostDetailView, CommentPostView,
    CreatePostView, LikePostView, FeedView, DeletePostView,
    LoginView, GoogleLoginView
)

urlpatterns = [
    # Posts
    path('posts/', PostListCreate.as_view(), name='post-list-create'),
    path('posts/create/', CreatePostView.as_view(), name='create-post'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'),
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'),
    path('posts/<int:post_id>/comment/', CommentPostView.as_view(), name='comment-post'),
    path('posts/<int:pk>/delete/', DeletePostView.as_view(), name='delete-post'),

    # Feed
    path('feed/', FeedView.as_view(), name='feed'),

    # Auth
    path('login/', LoginView.as_view(), name='login'),
    path('google-login/', GoogleLoginView.as_view(), name='google-login'),
]