from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  # Allows using the CustomUser model via AUTH_USER_MODEL


# Custom User Model
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('user', 'User'),
        ('guest', 'Guest'),
    ]

    # Add a role field directly to the user model
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

    def __str__(self):
        return f"{self.username} ({self.role})"


# Post Model
class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    
    POST_TYPES = [('text', 'Text'), ('image', 'Image'), ('video', 'Video')]
    post_type = models.CharField(max_length=10, choices=POST_TYPES)
    
    PRIVACY_CHOICES = [('public', 'Public'), ('private', 'Private')]
    privacy = models.CharField(max_length=10, choices=PRIVACY_CHOICES, default='public')
    
    # Optional JSON metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Automatically set when the post is created
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} by {self.author.username}"


# Comment Model
class Comment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.author.username} on Post {self.post.id}"


# Like Model
class Like(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Like by {self.author.username} on Post {self.post.id}"