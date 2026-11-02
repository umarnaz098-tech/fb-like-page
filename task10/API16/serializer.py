from rest_framework import serializers
from .models import(
    User, Profile, Community, Post, Comment, 
    Follow, CommunityMember, Reaction, Share,
    SavePost, Report, PostView)


class NamedPrimaryKeyRelatedField(serializers.PrimaryKeyRelatedField):
    def __init__(self, *args, display_field, **kwargs):
        self.display_field = display_field
        super().__init__(*args, **kwargs)
    def use_pk_only_optimization(self):
        return False
    def to_representation(self, value):
        return getattr(value, self.display_field)

class NamedRelatedField(serializers.SlugRelatedField):
    def __init__(self, *args, display_field, **kwargs):
        super().__init__(*args, slug_field=display_field, **kwargs)


class ProfileUsernameField(serializers.SlugRelatedField):
    def __init__(self, **kwargs):
        super().__init__(slug_field="username", **kwargs)

    def to_internal_value(self, data):
        try:
            return self.get_queryset().get(user__username=data)
        except Profile.DoesNotExist:
            self.fail("does_not_exist", slug_name="username", value=data)
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, value):
        return value.user.username


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True}}
        read_only_fields = ["is_staff", "is_superuser", "groups", "user_permissions"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class ProfileSerializer(serializers.ModelSerializer):
    user = NamedRelatedField(display_field="username", read_only=True)
    total_followers = serializers.SerializerMethodField()
    total_following = serializers.SerializerMethodField()
    total_profile_views = serializers.SerializerMethodField()
    saved_posts = serializers.SerializerMethodField()
    total_posts = serializers.SerializerMethodField()
    my_posts = serializers.SerializerMethodField()
    class Meta:
        model = Profile
        fields = "__all__"
    def get_total_followers(self, obj):
        return obj.user.followers.count()
    def get_total_following(self, obj):
        return obj.user.following.count()
    def get_total_profile_views(self, obj):
        return obj.profile_views.count()
    def get_saved_posts(self, obj):
        saved = obj.user.saved_posts.all()
        return SavePostSerializer(saved, many=True).data
    def get_total_posts(self, obj):
        return obj.user.posts.count()
    def get_my_posts(self, obj):
        posts = obj.user.posts.all().order_by("-created_at")
        return PostSerializer(posts, many=True).data
    
class CommunitySerializer(serializers.ModelSerializer):
    creator = NamedRelatedField(queryset=User.objects.all(),display_field="username",)
    class Meta:
        model = Community
        fields = "__all__"
    
class PostSerializer(serializers.ModelSerializer):
    author = NamedRelatedField(display_field="username", read_only=True)
    community = NamedRelatedField(queryset=Community.objects.all(),display_field="name",allow_null=True,required=False,)
    likes = serializers.SerializerMethodField()
    dislikes = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    total_shares = serializers.SerializerMethodField()
    class Meta:
        model = Post
        fields = "__all__"

    def get_likes(self, obj):
        return obj.reactions.filter(
            reaction_type="Like"
        ).count()
    def get_dislikes(self, obj):
        return obj.reactions.filter(
            reaction_type="Dislike"
        ).count()
    def get_comments(self, obj):
        return CommentSerializer(
            obj.comments.all(),
            many=True
        ).data
    def get_total_shares(self, obj):
        return obj.shares.count()

class CommentSerializer(serializers.ModelSerializer):
    author = NamedRelatedField(display_field="username", read_only=True)
    post = NamedPrimaryKeyRelatedField(queryset=Post.objects.all(),display_field="title")
    parent = NamedPrimaryKeyRelatedField(queryset=Comment.objects.all(), display_field="content", allow_null=True, required=False,)

    class Meta:
        model = Comment
        fields = "__all__"

class FollowSerializer(serializers.ModelSerializer):
    follower = NamedRelatedField(queryset=User.objects.all(),display_field="username",)
    following = NamedRelatedField(queryset=User.objects.all(),display_field="username",)

    class Meta:
        model = Follow
        fields = "__all__"

class CommunityMemberSerializer(serializers.ModelSerializer):
    user = NamedRelatedField(queryset=User.objects.all(),display_field="username",)
    community = NamedRelatedField(queryset=Community.objects.all(),display_field="name",)

    class Meta:
        model = CommunityMember
        fields = "__all__"

class ReactionSerializer(serializers.ModelSerializer):
    user = NamedRelatedField(queryset=User.objects.all(),display_field="username",)
    post = NamedPrimaryKeyRelatedField(queryset=Post.objects.all(),display_field="title",)

    class Meta:
        model = Reaction
        fields = "__all__"

class ShareSerializer(serializers.ModelSerializer):
    user = NamedRelatedField(queryset=User.objects.all(),display_field="username",)
    post = NamedPrimaryKeyRelatedField(queryset=Post.objects.all(),display_field="title",)

    class Meta:
        model = Share
        fields = "__all__"

class SavePostSerializer(serializers.ModelSerializer):
    user = NamedRelatedField(queryset=User.objects.all(),display_field="username",)
    post = NamedPrimaryKeyRelatedField(queryset=Post.objects.all(),display_field="title",)

    class Meta:
        model = SavePost
        fields = "__all__"

class ReportSerializer(serializers.ModelSerializer):
    user = serializers.SlugRelatedField(read_only=True, slug_field="username")
    profile = ProfileUsernameField(
        queryset=Profile.objects.select_related("user").all(),
        allow_null=True,
        required=False,
    )
    post = NamedPrimaryKeyRelatedField(queryset=Post.objects.all(),display_field="title",allow_null=True,required=False,)
    comment = NamedPrimaryKeyRelatedField(queryset=Comment.objects.all(),display_field="content",allow_null=True,required=False,)

    class Meta:
        model= Report
        fields = "__all__"
        read_only_fields = ["id", "status", "created_at"]

class PostViewSerializer(serializers.ModelSerializer):
    user = NamedRelatedField(queryset=User.objects.all(),display_field="username",allow_null=True,required=False,)
    post = NamedPrimaryKeyRelatedField(queryset=Post.objects.all(),display_field="title",)

    class Meta:
        model= PostView
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
