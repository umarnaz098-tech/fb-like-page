import base64

from django.test import TestCase
from rest_framework.test import APIClient

from .models import Community, CommunityMember, User
from .models import (
    Comment,
    Follow,
    Post,
    PostView,
    Profile,
    Reaction,
    Report,
    SavePost,
    Share,
)
from .serializer import (
    CommentSerializer,
    CommunityMemberSerializer,
    CommunitySerializer,
    FollowSerializer,
    PostSerializer,
    PostViewSerializer,
    ProfileSerializer,
    ReactionSerializer,
    ReportSerializer,
    SavePostSerializer,
    ShareSerializer,
)


class ApiPermissionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_registration_and_token_login_are_public(self):
        response = self.client.post(
            "/api/users/",
            {
                "username": "new_member",
                "password": "safe-test-password-2026",
                "is_staff": True,
                "is_superuser": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="new_member")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

        response = self.client.post(
            "/api/auth/token/",
            {"username": "new_member", "password": "safe-test-password-2026"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("token", response.data)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {response.data['token']}"
        )
        protected_response = self.client.get("/api/communities/")
        self.assertEqual(protected_response.status_code, 200)

    def test_basic_authentication_can_access_protected_endpoints(self):
        User.objects.create_user(
            username="basic_auth_user",
            password="safe-test-password-2026",
        )
        credentials = base64.b64encode(
            b"basic_auth_user:safe-test-password-2026"
        ).decode("ascii")
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        response = self.client.get("/api/communities/")

        self.assertEqual(response.status_code, 200)

    def test_regular_user_can_create_community_and_join(self):
        user = User.objects.create_user(
            username="regular_member",
            password="safe-test-password-2026",
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(
            "/api/communities/",
            {"name": "Open Community", "creator": user.username},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        community = Community.objects.get(name="Open Community")
        response = self.client.post(
            "/api/community-members/",
            {"user": user.username, "community": community.name},
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(
            CommunityMember.objects.filter(user=user, community=community).exists()
        )

    def test_unauthenticated_users_cannot_use_protected_endpoints(self):
        owner = User.objects.create_user(
            username="private_profile_owner",
            password="test-pass",
        )
        profile = Profile.objects.create(user=owner)
        protected_requests = (
            ("get", "/api/users/"),
            ("get", "/api/profiles/"),
            ("get", "/api/communities/"),
            ("get", "/api/posts/"),
            ("get", "/api/comments/"),
            (
                "post",
                "/api/comments/",
            ),
            ("get", "/api/community-members/"),
            ("get", "/api/shares/"),
            ("get", "/api/post-views/"),
            ("delete", f"/api/profiles/{profile.pk}/"),
        )

        for method, url in protected_requests:
            with self.subTest(method=method, url=url):
                if method == "post":
                    response = self.client.post(
                        url,
                        {"post": 0, "parent": 0, "content": "Not logged in"},
                        format="json",
                    )
                else:
                    response = getattr(self.client, method)(url)
                self.assertEqual(response.status_code, 401)
        self.assertTrue(Profile.objects.filter(pk=profile.pk).exists())

    def test_only_owner_can_delete_profile(self):
        owner = User.objects.create_user(username="profile_owner", password="test-pass")
        other_user = User.objects.create_user(username="other_user", password="test-pass")
        profile = Profile.objects.create(user=owner)
        self.client.force_authenticate(user=other_user)

        response = self.client.delete(f"/api/profiles/{profile.pk}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Profile.objects.filter(pk=profile.pk).exists())

        self.client.force_authenticate(user=owner)
        response = self.client.delete(f"/api/profiles/{profile.pk}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Profile.objects.filter(pk=profile.pk).exists())

    def test_basic_auth_user_cannot_delete_profile_owned_by_another_user(self):
        owner = User.objects.create_user(
            id=9,
            username="profile_owner_9",
            password="owner-password",
        )
        other_user = User.objects.create_user(
            id=10,
            username="other_user_10",
            password="other-password",
        )
        profile = Profile.objects.create(id=8, user=owner)
        credentials = base64.b64encode(
            b"other_user_10:other-password"
        ).decode("ascii")
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        response = self.client.delete(f"/api/profiles/{profile.pk}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Profile.objects.filter(pk=profile.pk, user=owner).exists())
        self.assertNotEqual(profile.pk, other_user.pk)

    def test_basic_auth_user_cannot_delete_another_users_account_and_profile(self):
        owner = User.objects.create_user(
            id=9,
            username="account_owner_9",
            password="owner-password",
        )
        other_user = User.objects.create_user(
            id=10,
            username="account_other_10",
            password="other-password",
        )
        profile = Profile.objects.create(id=8, user=owner)
        credentials = base64.b64encode(
            b"account_other_10:other-password"
        ).decode("ascii")
        self.client.credentials(HTTP_AUTHORIZATION=f"Basic {credentials}")

        response = self.client.delete(f"/api/users/{owner.pk}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=owner.pk).exists())
        self.assertTrue(Profile.objects.filter(pk=profile.pk, user=owner).exists())
        self.assertTrue(User.objects.filter(pk=other_user.pk).exists())

    def test_only_author_can_delete_post(self):
        owner = User.objects.create_user(username="post_owner", password="test-pass")
        other_user = User.objects.create_user(username="post_other", password="test-pass")
        post = Post.objects.create(author=owner, title="Owner post", content="Text")
        self.client.force_authenticate(user=other_user)

        response = self.client.delete(f"/api/posts/{post.pk}/")

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

        self.client.force_authenticate(user=owner)
        response = self.client.delete(f"/api/posts/{post.pk}/")

        self.assertEqual(response.status_code, 204)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_profile_and_post_creation_use_logged_in_user(self):
        user = User.objects.create_user(username="creator", password="test-pass")
        other_user = User.objects.create_user(username="not_creator", password="test-pass")
        self.client.force_authenticate(user=user)

        profile_response = self.client.post(
            "/api/profiles/",
            {"user": other_user.username, "bio": "My profile"},
            format="json",
        )
        post_response = self.client.post(
            "/api/posts/",
            {"author": other_user.username, "title": "My post", "content": "Text"},
            format="json",
        )

        self.assertEqual(profile_response.status_code, 201)
        self.assertEqual(profile_response.data["user"], user.username)
        self.assertEqual(post_response.status_code, 201)
        self.assertEqual(post_response.data["author"], user.username)

    def test_comment_creation_uses_logged_in_author(self):
        author = User.objects.create_user(
            username="comment_author",
            password="safe-test-password-2026",
        )
        other_user = User.objects.create_user(
            username="other_author",
            password="safe-test-password-2026",
        )
        post = Post.objects.create(author=author, title="Post", content="Text")
        self.client.force_authenticate(user=author)

        response = self.client.post(
            "/api/comments/",
            {
                "author": other_user.username,
                "post": post.pk,
                "content": "My comment",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["author"], author.username)

    def test_comments_by_post_requires_valid_post_id(self):
        user = User.objects.create_user(
            username="comment_reader",
            password="safe-test-password-2026",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get("/api/comments/by_post/")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "Provide a valid post_id.")

    def test_post_comments_endpoint_returns_only_that_posts_comments(self):
        user = User.objects.create_user(
            username="post_comment_reader",
            password="safe-test-password-2026",
        )
        first_post = Post.objects.create(
            author=user,
            title="First post",
            content="First",
        )
        second_post = Post.objects.create(
            author=user,
            title="Second post",
            content="Second",
        )
        first_comment = Comment.objects.create(
            author=user,
            post=first_post,
            content="Comment on first post",
        )
        Comment.objects.create(
            author=user,
            post=second_post,
            content="Comment on second post",
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(f"/api/posts/{first_post.pk}/comments/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], first_comment.pk)

        response = self.client.get(
            "/api/comments/by_post/",
            {"post_id": first_post.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], first_comment.pk)

    def test_post_reactions_endpoint_returns_likes_and_dislikes_together(self):
        user = User.objects.create_user(
            username="reaction_reader",
            password="safe-test-password-2026",
        )
        other_user = User.objects.create_user(
            username="other_reaction_user",
            password="safe-test-password-2026",
        )
        post = Post.objects.create(author=user, title="Post", content="Text")
        like = Reaction.objects.create(
            user=user,
            post=post,
            reaction_type=Reaction.ReactionType.LIKE,
        )
        dislike = Reaction.objects.create(
            user=other_user,
            post=post,
            reaction_type=Reaction.ReactionType.DISLIKE,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(f"/api/posts/{post.pk}/reactions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["likes"]], [like.pk])
        self.assertEqual(
            [item["id"] for item in response.data["dislikes"]],
            [dislike.pk],
        )

    def test_profile_reaction_endpoints_return_combined_and_separate_lists(self):
        user = User.objects.create_user(
            username="profile_reaction_user",
            password="test-pass",
        )
        other_user = User.objects.create_user(
            username="other_profile_reaction_user",
            password="test-pass",
        )
        profile = Profile.objects.create(user=user)
        first_post = Post.objects.create(
            author=other_user,
            title="Liked post",
            content="Text",
        )
        second_post = Post.objects.create(
            author=other_user,
            title="Disliked post",
            content="Text",
        )
        like = Reaction.objects.create(
            user=user,
            post=first_post,
            reaction_type=Reaction.ReactionType.LIKE,
        )
        dislike = Reaction.objects.create(
            user=user,
            post=second_post,
            reaction_type=Reaction.ReactionType.DISLIKE,
        )
        Reaction.objects.create(
            user=other_user,
            post=first_post,
            reaction_type=Reaction.ReactionType.DISLIKE,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(f"/api/profiles/{profile.pk}/reactions/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["likes"]], [like.pk])
        self.assertEqual(
            [item["id"] for item in response.data["dislikes"]],
            [dislike.pk],
        )

        response = self.client.get(f"/api/profiles/{profile.pk}/likes/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [like.pk])

        response = self.client.get(f"/api/profiles/{profile.pk}/dislikes/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data], [dislike.pk])

    def test_profile_reports_endpoint_returns_reports_for_profile_user(self):
        user = User.objects.create_user(
            username="profile_report_user",
            password="safe-test-password-2026",
        )
        other_user = User.objects.create_user(
            username="other_profile_report_user",
            password="safe-test-password-2026",
        )
        profile = Profile.objects.create(user=user)
        post = Post.objects.create(author=user, title="Post", content="Text")
        report = Report.objects.create(
            user=user,
            post=post,
            reason=Report.Reason.SPAM,
        )
        reported_profile = Profile.objects.create(user=other_user)
        profile_report = Report.objects.create(
            user=user,
            profile=reported_profile,
            reason=Report.Reason.HARASSMENT,
        )
        comment = Comment.objects.create(
            author=other_user,
            post=post,
            content="Reported comment",
        )
        comment_report = Report.objects.create(
            user=user,
            comment=comment,
            reason=Report.Reason.OTHER,
        )
        Report.objects.create(
            user=other_user,
            post=post,
            reason=Report.Reason.OTHER,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(f"/api/profiles/{profile.pk}/reports/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {item["id"] for item in response.data},
            {report.pk, profile_report.pk, comment_report.pk},
        )
        profile_report_data = next(
            item for item in response.data if item["id"] == profile_report.pk
        )
        comment_report_data = next(
            item for item in response.data if item["id"] == comment_report.pk
        )
        post_report_data = next(
            item for item in response.data if item["id"] == report.pk
        )
        self.assertEqual(profile_report_data["profile"], other_user.username)
        self.assertEqual(post_report_data["post"], post.title)
        self.assertEqual(comment_report_data["comment"], comment.content)

        other_user = User.objects.create_user(
            username="report_viewer",
            password="test-pass",
        )
        self.client.force_authenticate(user=other_user)
        response = self.client.get(f"/api/profiles/{profile.pk}/reports/")
        self.assertEqual(response.status_code, 403)

    def test_profile_views_count_endpoint_is_removed(self):
        user = User.objects.create_user(
            username="profile_view_reader",
            password="test-pass",
        )
        profile = Profile.objects.create(user=user)
        self.client.force_authenticate(user=user)

        response = self.client.get(
            f"/api/profiles/{profile.pk}/profile_views_count/"
        )

        self.assertEqual(response.status_code, 404)

    def test_report_api_endpoints_are_removed(self):
        user = User.objects.create_user(
            username="report_api_reader",
            password="test-pass",
        )
        self.client.force_authenticate(user=user)

        for method, url in (
            ("get", "/api/reports/"),
            ("post", "/api/reports/"),
            ("get", "/api/reports/1/"),
            ("put", "/api/reports/1/"),
            ("patch", "/api/reports/1/"),
            ("delete", "/api/reports/1/"),
        ):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(response.status_code, 404)

    def test_saved_posts_crud_api_is_removed(self):
        user = User.objects.create_user(
            username="saved_posts_api_reader",
            password="test-pass",
        )
        self.client.force_authenticate(user=user)

        for method, url in (
            ("get", "/api/saved-posts/"),
            ("post", "/api/saved-posts/"),
            ("get", "/api/saved-posts/1/"),
            ("put", "/api/saved-posts/1/"),
            ("patch", "/api/saved-posts/1/"),
            ("delete", "/api/saved-posts/1/"),
        ):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(response.status_code, 404)

    def test_separate_follows_crud_api_is_removed_but_profile_lists_remain(self):
        user = User.objects.create_user(
            username="follow_api_user",
            password="test-pass",
        )
        followed_user = User.objects.create_user(
            username="followed_user",
            password="test-pass",
        )
        profile = Profile.objects.create(user=user)
        followed_profile = Profile.objects.create(user=followed_user)
        Follow.objects.create(follower=user, following=followed_user)
        self.client.force_authenticate(user=user)

        for method, url in (
            ("get", "/api/follows/"),
            ("post", "/api/follows/"),
            ("get", "/api/follows/1/"),
            ("put", "/api/follows/1/"),
            ("patch", "/api/follows/1/"),
            ("delete", "/api/follows/1/"),
        ):
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(url, {}, format="json")
                self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/api/profiles/{profile.pk}/following/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["following"], followed_user.username)

        response = self.client.get(f"/api/profiles/{followed_profile.pk}/followers/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["follower"], user.username)

    def test_separate_reaction_endpoints_are_removed(self):
        user = User.objects.create_user(
            username="reaction_api_reader",
            password="safe-test-password-2026",
        )
        post = Post.objects.create(author=user, title="Post", content="Text")
        self.client.force_authenticate(user=user)

        for url in (
            "/api/reactions/",
            "/api/reactions/1/",
            f"/api/posts/{post.pk}/likes/",
            f"/api/posts/{post.pk}/dislikes/",
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)

    def test_comment_like_and_dislike_endpoints_are_removed(self):
        user = User.objects.create_user(
            username="comment_reader",
            password="safe-test-password-2026",
        )
        post = Post.objects.create(author=user, title="Post", content="Text")
        comment = Comment.objects.create(
            author=user,
            post=post,
            content="Comment",
        )
        self.client.force_authenticate(user=user)

        for action_name in ("likes", "dislikes", "reaction_count"):
            with self.subTest(action=action_name):
                response = self.client.get(
                    f"/api/comments/{comment.pk}/{action_name}/"
                )
                self.assertEqual(response.status_code, 404)

        response = self.client.get(f"/api/comments/{comment.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("likes", response.data)
        self.assertNotIn("dislikes", response.data)


class RelatedNameSerializerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="test-pass")
        self.other_user = User.objects.create_user(
            username="bob",
            password="test-pass",
        )
        self.profile = Profile.objects.create(user=self.user)
        self.community = Community.objects.create(
            name="Book Club",
            creator=self.user,
        )
        self.post = Post.objects.create(
            author=self.user,
            community=self.community,
            title="First Post",
            content="Hello",
        )
        self.comment = Comment.objects.create(
            author=self.other_user,
            post=self.post,
            content="Nice post",
        )
        self.reply = Comment.objects.create(
            author=self.user,
            post=self.post,
            parent=self.comment,
            content="Thanks",
        )

    def test_related_objects_display_names(self):
        serializers_and_expected_values = [
            (ProfileSerializer(self.profile), "user", "alice"),
            (CommunitySerializer(self.community), "creator", "alice"),
            (PostSerializer(self.post), "author", "alice"),
            (PostSerializer(self.post), "community", "Book Club"),
            (CommentSerializer(self.comment), "author", "bob"),
            (CommentSerializer(self.comment), "post", "First Post"),
            (CommentSerializer(self.reply), "parent", "Nice post"),
            (FollowSerializer(Follow(follower=self.user, following=self.other_user)),
             "follower", "alice"),
            (FollowSerializer(Follow(follower=self.user, following=self.other_user)),
             "following", "bob"),
            (CommunityMemberSerializer(
                CommunityMember(user=self.user, community=self.community)
            ), "user", "alice"),
            (CommunityMemberSerializer(
                CommunityMember(user=self.user, community=self.community)
            ), "community", "Book Club"),
            (ReactionSerializer(
                Reaction(user=self.user, post=self.post)
            ), "user", "alice"),
            (ReactionSerializer(
                Reaction(user=self.user, post=self.post)
            ), "post", "First Post"),
            (ShareSerializer(Share(user=self.user, post=self.post)),
             "user", "alice"),
            (ShareSerializer(Share(user=self.user, post=self.post)),
             "post", "First Post"),
            (SavePostSerializer(SavePost(user=self.user, post=self.post)),
             "user", "alice"),
            (SavePostSerializer(SavePost(user=self.user, post=self.post)),
             "post", "First Post"),
            (ReportSerializer(Report(user=self.user, reason="Spam")),
             "user", "alice"),
            (ReportSerializer(Report(user=self.user, post=self.post, reason="Spam")),
             "post", "First Post"),
            (ReportSerializer(
                Report(user=self.user, comment=self.comment, reason="Spam")
            ), "comment", "Nice post"),
            (PostViewSerializer(PostView(user=self.user, post=self.post)),
             "user", "alice"),
            (PostViewSerializer(PostView(user=self.user, post=self.post)),
             "post", "First Post"),
        ]

        for serializer, field, expected in serializers_and_expected_values:
            with self.subTest(field=field, expected=expected):
                self.assertEqual(serializer.data[field], expected)

    def test_related_fields_accept_names_for_writes(self):
        serializer = CommunityMemberSerializer(
            data={"user": self.user.username, "community": self.community.name}
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        membership = serializer.save()
        self.assertEqual(membership.user, self.user)
        self.assertEqual(membership.community, self.community)
        self.assertEqual(serializer.data["user"], "alice")
        self.assertEqual(serializer.data["community"], "Book Club")

    def test_swagger_schema_uses_strings_for_user_and_community(self):
        from drf_spectacular.generators import SchemaGenerator

        schema = SchemaGenerator().get_schema(public=True)
        properties = schema["components"]["schemas"]["CommunityMember"]["properties"]

        self.assertEqual(properties["user"]["type"], "string")
        self.assertEqual(properties["community"]["type"], "string")
