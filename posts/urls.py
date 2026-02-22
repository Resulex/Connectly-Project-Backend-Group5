from django.urls import path
from .views import CommentPostView, CreatePostView, GoogleLoginView, LikePostView, LoginView, PostDetailView, ProtectedView, UserListCreate, PostListCreate, CommentListCreate


urlpatterns = [
    # path('users/', views.get_users, name='get_users'),
    # path('users/create/', views.create_user, name='create_user'),
    # path('posts/', views.get_posts, name='get_posts'),
    # path('posts/create/', views.create_post, name='create_post'),
    path('users/', UserListCreate.as_view(), name='user-list-create'), # users API
    path('posts/', PostListCreate.as_view(), name='post-list-create'), # posts API
    path('comments/', CommentListCreate.as_view(), name='comment-list-create'), #comments API
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post-detail'), # post detail API
    path('protected/', ProtectedView.as_view(), name='protected'), # protected API
    path('factory-test/', CreatePostView.as_view(), name='factory-test'), # factory test API
    path('posts/<int:post_id>/like/', LikePostView.as_view(), name='like-post'), # like/unlike post API
    path('posts/<int:post_id>/comments/', CommentPostView.as_view(), name='comment-post'), # comment post API
    path('login/', LoginView.as_view(), name='login'), # login API
    path('auth/google/login/', GoogleLoginView.as_view(), name='google-login'), # Google OAuth2 login API
]



