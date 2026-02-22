from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from posts.pagination import Pagination
from .models import Like, Post, Comment
from .serializers import UserSerializer, PostSerializer, CommentSerializer, LikeSerializer, LoginSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from .permissions import IsPostAuthor
from rest_framework.authentication import TokenAuthentication
from singletons.logger_singleton import LoggerSingleton
from factories.post_factory import PostFactory
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from google.auth.transport import requests
from google.oauth2 import id_token
import logging


logger = LoggerSingleton().get_logger()
logger.info("API initialized successfully.")


# Update Views with Validation and Relational Logic (DRF)
class UserListCreate(APIView):
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(list(users))


    def post(self, request):
        user = User.objects.create_user(username="new_user", password="secure_pass123")
        print(user.password)  # Outputs a hashed password



class PostListCreate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        posts = Post.objects.all()
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)


    def post(self, request):
        serializer = PostSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CommentListCreate(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    def get(self, request):
        comments = Comment.objects.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)


    def post(self, request):
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class PostDetailView(APIView):

    permission_classes = [IsAuthenticated, IsPostAuthor]


    def get(self, request, pk):
        post = Post.objects.get(pk=pk)
        self.check_object_permissions(request, post)
        return Response({"content": post.content})

class ProtectedView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]


    def get(self, request):
        return Response({"message": "Authenticated!"})


class CreatePostView(APIView):
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
                author=request.user # Assuming the user is authenticated and available in the request
            )
            return Response({'message': 'Post created successfully!', 'post_id': post.id}, status=status.HTTP_201_CREATED)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class LikePostView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # Allow unlike if the user has already liked the post
    def post(self, request, post_id):
        try:
            post = Post.objects.get(id=post_id)
            like, created = Like.objects.get_or_create(author=request.user, post=post)
            if created:
                return Response({'message': 'Post liked successfully!'}, status=status.HTTP_201_CREATED)
            else:
                like.delete()  # Unlike the post if already liked
                return Response({'message': 'Post unliked successfully!'}, status=status.HTTP_200_OK)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)


class CommentPostView(APIView):
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
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Post.DoesNotExist:
            return Response({'error': 'Post not found.'}, status=status.HTTP_404_NOT_FOUND)
        

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            token, created = Token.objects.get_or_create(user=user)
            logger.info(f"User {user.username} logged in successfully.")
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'email': user.email
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


class GoogleLoginView(APIView):
    def post(self, request):
        try:
            id_token_str = request.data.get('id_token')
            
            if not id_token_str:
                return Response(
                    {'error': 'id_token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verify the token with Google
            idinfo = id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                '516073834973-dg6ifcmd3shm4c8u4gc89h3bl5f03b1t.apps.googleusercontent.com'
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
            
            # Get or create token
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
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            logger.error(f"OAuth error: {str(e)}")
            return Response(
                {'error': 'Authentication failed'},
                status=status.HTTP_400_BAD_REQUEST
            )