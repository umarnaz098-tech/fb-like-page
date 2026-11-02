from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, extend_schema
from .models import(
    User, Profile, Community, Post, Comment, 
    CommunityMember, Reaction, Share,
    PostView
    )
from .serializer import (
    UserSerializer,
    ProfileSerializer,
    CommunitySerializer,
    PostSerializer,
    CommentSerializer,
    FollowSerializer,
    CommunityMemberSerializer,
    ReactionSerializer,
    ShareSerializer,
    SavePostSerializer,
    ReportSerializer,
    PostViewSerializer
)


class CanDeleteOwnProfileOrPost(BasePermission):
    def has_object_permission(self, request, view, obj):
        if view.action != "destroy":
            return True

        if isinstance(obj, User):
            return obj.id == request.user.id
        if isinstance(obj, Profile):
            return obj.user_id == request.user.id
        if isinstance(obj, Post):
            return obj.author_id == request.user.id
        return False


class UserViewSet(ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, CanDeleteOwnProfileOrPost,]

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return super().get_permissions()

class ProfileViewSet(ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated, CanDeleteOwnProfileOrPost]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    # See followers
    @action(detail=True, methods=["get"])
    def followers(self, request, pk=None):
        profile = self.get_object()
        followers = profile.user.followers.all()
        serializer = FollowSerializer(followers, many=True)
        return Response(serializer.data)

    # See following
    @action(detail=True, methods=["get"])
    def following(self, request, pk=None):
        profile = self.get_object()
        following = profile.user.following.all()
        serializer = FollowSerializer(following, many=True)
        return Response(serializer.data)

    # See saved posts
    @action(detail=True, methods=["get"])
    def saved_posts(self, request, pk=None):
        profile = self.get_object()
        saved = profile.user.saved_posts.all()
        serializer = SavePostSerializer(saved, many=True)
        return Response(serializer.data)

    # See this user's likes and dislikes together
    @action(detail=True, methods=["get"])
    def reactions(self, request, pk=None):
        profile = self.get_object()
        reactions = profile.user.reactions.all().order_by("-created_at")
        likes = reactions.filter(reaction_type=Reaction.ReactionType.LIKE)
        dislikes = reactions.filter(reaction_type=Reaction.ReactionType.DISLIKE)

        return Response({
            "likes": ReactionSerializer(likes, many=True).data,
            "dislikes": ReactionSerializer(dislikes, many=True).data,
        })

    # See this user's likes
    @action(detail=True, methods=["get"])
    def likes(self, request, pk=None):
        profile = self.get_object()
        likes = profile.user.reactions.filter(
            reaction_type=Reaction.ReactionType.LIKE
        ).order_by("-created_at")
        serializer = ReactionSerializer(likes, many=True)
        return Response(serializer.data)

    # See this user's dislikes
    @action(detail=True, methods=["get"])
    def dislikes(self, request, pk=None):
        profile = self.get_object()
        dislikes = profile.user.reactions.filter(
            reaction_type=Reaction.ReactionType.DISLIKE
        ).order_by("-created_at")
        serializer = ReactionSerializer(dislikes, many=True)
        return Response(serializer.data)

    # See reports made by this profile's user
    @action(detail=True, methods=["get"])
    def reports(self, request, pk=None):
        profile = self.get_object()
        if profile.user_id != request.user.id:
            raise PermissionDenied("You can only view reports from your own profile.")
        reports = profile.user.reports.all().order_by("-created_at")
        serializer = ReportSerializer(reports, many=True)
        return Response(serializer.data)

    # See my posts
    @action(detail=True, methods=["get"])
    def my_posts(self, request, pk=None):
        profile = self.get_object()
        posts = profile.user.posts.all().order_by("-created_at")
        serializer = PostSerializer(posts, many=True)
        return Response(serializer.data)

class CommunityViewSet(ModelViewSet):
    queryset = Community.objects.all()
    serializer_class = CommunitySerializer
    permission_classes = [IsAuthenticated]

class PostViewSet(ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated, CanDeleteOwnProfileOrPost]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # See comments on a particular post
    @action(detail=True, methods=["get"])
    def comments(self, request, pk=None):
        post = self.get_object()
        comments = post.comments.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    # See likes and dislikes on a particular post
    @action(detail=True, methods=["get"])
    def reactions(self, request, pk=None):
        post = self.get_object()
        likes = post.reactions.filter(reaction_type="Like")
        dislikes = post.reactions.filter(reaction_type="Dislike")

        return Response({
            "likes": ReactionSerializer(likes, many=True).data,
            "dislikes": ReactionSerializer(dislikes, many=True).data,
        })

    # See total number of shares
    @action(detail=True, methods=["get"])
    def shares_count(self, request, pk=None):
        post = self.get_object()
        total_shares = post.shares.count()

        return Response({
            "post": post.id,
            "total_shares": total_shares
        })

class CommentViewSet(ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # Get all comments on a particular post
    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="post_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="ID of the post whose comments you want to see.",
            )
        ]
    )
    @action(detail=False, methods=["get"])
    def by_post(self, request):
        post_id = request.query_params.get("post_id")

        if not post_id or not post_id.isdigit():
            return Response(
                {"error": "Provide a valid post_id."},
                status=400,
            )

        comments = Comment.objects.filter(post_id=post_id)
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

class CommunityMemberViewSet(ModelViewSet):
    queryset = CommunityMember.objects.all()
    serializer_class = CommunityMemberSerializer
    permission_classes = [IsAuthenticated]

class ShareViewSet(ModelViewSet):
    queryset = Share.objects.all()
    serializer_class = ShareSerializer
    permission_classes = [IsAuthenticated]

class PostViewViewSet(ModelViewSet):
    queryset = PostView.objects.all()
    serializer_class = PostViewSerializer
    permission_classes = [IsAuthenticated]
