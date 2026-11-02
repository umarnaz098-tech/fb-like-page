from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    UserViewSet,
    ProfileViewSet,
    CommunityViewSet,
    PostViewSet,
    CommentViewSet,
    CommunityMemberViewSet,
    ShareViewSet,
    PostViewViewSet
)

router = DefaultRouter()

router.register("users", UserViewSet)
router.register("profiles", ProfileViewSet)
router.register("communities", CommunityViewSet)
router.register("posts", PostViewSet)
router.register("comments", CommentViewSet)
router.register("community-members", CommunityMemberViewSet)
router.register("shares", ShareViewSet)
router.register("post-views", PostViewViewSet)

urlpatterns = [
    path("auth/token/", obtain_auth_token, name="api-token-auth"),
    path("", include(router.urls)),
]
