from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.username


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="profile",)
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pictures/",blank=True,)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.user.username


class ProfileView(models.Model):
    viewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile_views_made"
    )
    profile = models.ForeignKey(
        "Profile",
        on_delete=models.CASCADE,
        related_name="profile_views"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.viewer.username} viewed {self.profile.user.username}"


class Community(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="created_communities",)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="posts"
    )
    community = models.ForeignKey(
        Community,
        on_delete=models.CASCADE,
        related_name="posts",
        null=True,
        blank=True
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    picture = models.ImageField(upload_to="post_pictures/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Comment(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        related_name="replies",
        null=True,
        blank=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} - {self.post.title}"


class Follow(models.Model):
    follower = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="following",)
    following = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="followers",)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class CommunityMember(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="community_memberships",)
    community = models.ForeignKey(Community,on_delete=models.CASCADE,related_name="members",)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "community")

    def __str__(self):
        return f"{self.user.username} - {self.community.name}"


class Reaction(models.Model):
    class ReactionType(models.TextChoices):
        LIKE = "Like", "Like"
        DISLIKE = "Dislike", "Dislike"

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="reactions",)
    post = models.ForeignKey(Post,on_delete=models.CASCADE,related_name="reactions",)
    reaction_type = models.CharField(max_length=10,choices=ReactionType.choices,default=ReactionType.LIKE,)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")

    def __str__(self):
        return f"{self.user.username} - {self.post.title} - {self.reaction_type}"


class Share(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="shares",)
    post = models.ForeignKey(Post,on_delete=models.CASCADE,related_name="shares",)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} shared {self.post.title}"


class SavePost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="saved_posts",)
    post = models.ForeignKey(Post,on_delete=models.CASCADE,related_name="saved_by",)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")

    def __str__(self):
        return f"{self.user.username} saved {self.post.title}"

class Report(models.Model):
    class Reason(models.TextChoices):
        SPAM = "Spam", "Spam"
        HARASSMENT = "Harassment", "Harassment"
        HATE_SPEECH = "Hate Speech", "Hate Speech"
        VIOLENCE = "Violence", "Violence"
        OTHER = "Other", "Other"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        REVIEWED = "Reviewed", "Reviewed"
        RESOLVED = "Resolved", "Resolved"

    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="reports",)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        related_name="reported_in_reports",
        null=True,
        blank=True,
    )
    post = models.ForeignKey(Post,on_delete=models.CASCADE,related_name="reports",null=True,blank=True)
    comment = models.ForeignKey(Comment,on_delete=models.CASCADE,related_name="reports",null=True,blank=True)
    reason = models.CharField(max_length=20,choices=Reason.choices)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20,choices=Status.choices,default=Status.PENDING,)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.reason}"

class PostView(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="post_views",null=True,blank=True)
    post = models.ForeignKey(Post,on_delete=models.CASCADE,related_name="views",)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")

    def __str__(self):
        return self.post.title
