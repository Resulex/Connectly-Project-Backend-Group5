from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination

from django.contrib.auth import get_user_model
from django.db.models import Count, Prefetch, Q
from django.core.cache import cache

from rest_framework.authtoken.models import Token
from google.auth.transport import requests
from google.oauth2 import id_token

from posts.pagination import Pagination
from .models import Like, Post, Comment
from .serializers import (
    UserSerializer, PostSerializer, CommentSerializer,
    LikeSerializer, LoginSerializer, FeedPostSerializer
)
from .permissions import IsPostAuthor, IsAdminRole

from singletons.logger_singleton import LoggerSingleton
from factories.post_factory import PostFactory


# Get the Django user model
User = get_user_model()

logger = LoggerSingleton().get_logger()
logger.info("API initialized successfully.")



# User Endpoints

class UserListCreate(APIView):
    """
    GET: List all users.
    POST: Create a new user (example user creation for testing).
    """
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        user = User.objects.create_user(username="new_user", password="secure_pass123")
        return Response({'message': f'User {user.username} created.'})



# Post Endpoints

class PostListCreate(APIView):
    """
    GET: List all posts.
    POST: Create a new post.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)  # Automatically assign the author
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostDetailView(APIView):
    """
    GET: Retrieve a post by ID with privacy enforcement.
    Only the post author can view private posts.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsPostAuthor]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            if post.privacy == "private" and post.author != request.user:
                return Response({"error": "This post is private"}, status=status.HTTP_403_FORBIDDEN)
            self.check_object_permissions(request, post)
            serializer = PostSerializer(post)
            return Response(serializer.data)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)


class CreatePostView(APIView):
    """
    POST: Create a post using PostFactory.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        try:
            post = PostFactory.create_post(
            post_type=data['post_type'],
            title=data['title'],
            content=data.get('content', ''),
            metadata=data.get('metadata', {}),
            author=request.user,
            privacy=data.get('privacy', 'public') 
        )

            # Invalidate feed cache
            feed_version = cache.get('feed_version', 1)
            cache.set('feed_version', feed_version + 1)

            return Response({'message': 'Post created successfully!', 'post_id': post.id}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DeletePostView(APIView):
    """
    DELETE: Delete a post by ID (admin only).
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, IsAdminRole]

    def delete(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
            post.delete()
            return Response({"message": "Post deleted successfully"}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({"error": "Post not found"}, status=status.HTTP_404_NOT_FOUND)



# Like Endpoints

class LikePostView(APIView):
    """
    POST: Like or unlike a post.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            like, created = Like.objects.get_or_create(author=request.user, post=post)

            # Invalidate feed cache
            feed_version = cache.get('feed_version', 1)
            cache.set('feed_version', feed_version + 1)

            if created:
                return Response({'message': 'Post liked successfully!'}, status=status.HTTP_201_CREATED)
            else:
                like.delete()
                return Response({'message': 'Post unliked successfully!'}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)



# Comment Endpoints

class CommentListCreate(APIView):
    """
    GET: List all comments.
    POST: Create a new comment.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(author=request.user)
            feed_version = cache.get('feed_version', 1)
            cache.set('feed_version', feed_version + 1)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentPostView(APIView):
    """
    GET: Paginated list of comments for a post.
    POST: Add a comment to a post.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            comments = post.comments.all()
            paginator = Pagination()
            paginated_comments = paginator.paginate_queryset(comments, request)
            serializer = CommentSerializer(paginated_comments, many=True)
            return paginator.get_paginated_response(serializer.data)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            serializer = CommentSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(author=request.user, post=post)
                feed_version = cache.get('feed_version', 1)
                cache.set('feed_version', feed_version + 1)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)



# Authentication Endpoints

class LoginView(APIView):
    """
    POST: Login user and return auth token.
    """
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, _ = Token.objects.get_or_create(user=user)
            logger.info(f"User {user.username} logged in successfully.")
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    """
    POST: Login/register user via Google OAuth.
    """
    def post(self, request):
        try:
            id_token_str = request.data.get('id_token')
            if not id_token_str:
                return Response({'error': 'id_token is required'}, status=status.HTTP_400_BAD_REQUEST)

            # Verify token with Google
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                'YOUR_GOOGLE_CLIENT_ID'
            )

            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')

            # Get or create user
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email.split('@')[0],
                    'first_name': first_name,
                    'last_name': last_name,
                }
            )

            token, _ = Token.objects.get_or_create(user=user)
            logger.info(f"User {user.username} {'registered' if created else 'logged in'} via Google.")

            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_new': created
            }, status=status.HTTP_200_OK)

        except ValueError as e:
            logger.error(f"Invalid token: {str(e)}")
            return Response({'error': 'Invalid token'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}")
            return Response({'error': 'Authentication failed'}, status=status.HTTP_400_BAD_REQUEST)



# Feed Endpoint

class FeedView(APIView):
    """
    GET: Paginated feed of posts with latest comments and like counts.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        page_size = request.query_params.get('page_size')
        page = request.query_params.get('page', '1')

        # Feed version caching
        feed_version = cache.get('feed_version', 1)
        cache_key = f"feed:v{feed_version}:user:{request.user.id}:page:{page}:size:{page_size or 'default'}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached)

        posts_qs = (
            Post.objects
            .select_related('author')
            .prefetch_related(
                Prefetch(
                    'comments',
                    queryset=Comment.objects.select_related('author').order_by('-created_at')
                )
            )
            .annotate(like_count=Count('likes'))
            .filter(Q(privacy="public") | Q(author=request.user))
            .order_by('-created_at')
        )

        paginator = Pagination()
        paginated_qs = paginator.paginate_queryset(posts_qs, request)

        result = [FeedPostSerializer(post, context={"request": request}).data for post in paginated_qs]
        response = paginator.get_paginated_response(result)
        cache.set(cache_key, response.data, 60)
        return response



# Protected Test Endpoint


class ProtectedView(APIView):
    """
    GET: Test authenticated access.
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "Authenticated!"})
    

