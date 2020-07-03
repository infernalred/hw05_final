from django.core.cache.utils import make_template_fragment_key
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.core.cache import cache

from .models import Post, User, Group, Comment, Follow

POST_CACHE = {
    'default': {
        'BACKEND': 'django.core.cache.backends.dummy.DummyCache'
    }
}


class TestStringMethods(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="pupkin",
                                             email="pupkin@gmail.com", password="12345")
        self.non_auth_client = Client()
        self.client.force_login(self.user)
        self.text = "mama papa"
        self.group = Group.objects.create(title="mao", slug="mao",
                                          description="mao dzedun")

    def test_signup(self):
        resp = self.client.get(reverse("signup"))
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, template_name="signup.html")

    def test_profile(self):
        resp_profile = self.client.get(reverse("profile", kwargs={'username': self.user.username}))
        self.assertEqual(resp_profile.status_code, 200)

    def test_auth_user_can_publish(self):
        resp = self.client.post(reverse("new_post"), data={'group': self.group.id,
                                                           'text': self.text}, follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Post.objects.count(), 1)
        created_post = Post.objects.first()
        self.assertEqual(created_post.text, self.text)
        self.assertEqual(created_post.group, self.group)
        self.assertEqual(created_post.author, self.user)

    def test_non_auth_cant_post(self):
        resp = self.non_auth_client.post(reverse("new_post"), data={'post': self.text})
        self.assertRedirects(resp, "/auth/login/?next=/new/")
        self.assertEqual(Post.objects.count(), 0)

    @override_settings(CACHES=POST_CACHE)
    def check_contain_post(self, url, user, group, text):
        resp = self.client.get(url)
        post = None
        if 'paginator' in resp.context:
            self.assertEqual(resp.context['paginator'].count, 1)
            post = resp.context['page'][0]
        else:
            post = resp.context['post']
        self.assertEqual(post.text, text)
        self.assertEqual(post.group, group)
        self.assertEqual(post.author, user)
        self.assertTrue(post.image)
        self.assertContains(resp, '<img')

    def test_check_post(self):
        post = Post.objects.create(text=self.text, group=self.group, author=self.user)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile('small.gif', small_gif,
                                 content_type='image/gif')
        self.client.post(reverse("post_edit", kwargs={
            'username': self.user.username,
            'post_id': post.id}),
                         data={
                             'group': self.group.id,
                             'text': self.text,
                             'image': img
                         }, follow=True)
        list_urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id}),
            reverse('groups', kwargs={'slug': self.group.slug}),
        ]
        for url in list_urls:
            with self.subTest(url=url):
                self.check_contain_post(url, self.user, self.group, self.text)

    def test_check_not_image_file(self):
        post = Post.objects.create(text=self.text, group=self.group, author=self.user)
        img = SimpleUploadedFile('file.txt', b'i-am-a-text-file')
        resp = self.client.post(reverse("post_edit", kwargs={
            'username': self.user.username,
            'post_id': post.id}),
                                data={
                                    'group': self.group.id,
                                    'text': self.text,
                                    'image': img
                                }, forward=True)
        self.assertFormError(resp, 'form', 'image', 'Загрузите правильное изображение. Файл, который вы загрузили, '
                                                    'поврежден или не является изображением.')

    def test_check_edit(self):
        post = Post.objects.create(text=self.text, group=self.group, author=self.user)
        group = Group.objects.create(title="chim", slug="chim", description="chim kim")
        new_text = "Chim bir fir"
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile('small.gif', small_gif,
                                 content_type='image/gif')
        self.client.post(reverse("post_edit", kwargs={'username': self.user.username, 'post_id': post.id}),
                         data={'group': group.id, 'text': new_text, 'image': img}, follow=True)
        list_urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id})
        ]
        for url in list_urls:
            with self.subTest(url=url):
                self.check_contain_post(url, self.user, group, new_text)
        resp = self.client.get(reverse('groups', kwargs={'slug': self.group.slug}))
        self.assertEqual(resp.context['paginator'].count, 0)

    def test_cache(self):
        self.client.get(reverse('index'))
        post = Post.objects.create(text='new text', group=self.group,
                                   author=self.user)
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, post.text)
        key = make_template_fragment_key('index_page')
        cache.delete(key)
        response = self.client.get(reverse('index'))
        self.assertContains(response, post.text)

    def test_check_comments(self):
        post = Post.objects.create(text=self.text, group=self.group,
                                   author=self.user)
        self.client.post(reverse("add_comment", kwargs={
            'username': self.user.username,
            'post_id': post.id
        }), data={
            'text': 'Comment',
            'post': post.id,
            'author': self.user.id})
        comment = post.comments.select_related('author').first()
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(comment.text, 'Comment')
        self.assertEqual(comment.post, post)
        self.assertEqual(comment.author, self.user)

    def test_check_non_auth_comments(self):
        post = Post.objects.create(text=self.text, group=self.group,
                                   author=self.user)
        self.non_auth_client.post(reverse("add_comment", kwargs={
            'username': self.user.username,
            'post_id': post.id
        }), data={
            'text': 'Comment',
            'post': post.id,
            'author': self.user.id})
        self.assertEqual(Comment.objects.count(), 0)

    def test_check_follow(self):
        leo = User.objects.create_user(username="leo",
                                       email="leo@gmail.com",
                                       password="12345")
        self.client.post(reverse("profile_follow", kwargs={
            'username': leo.username,
        }))
        self.assertEqual(Follow.objects.count(), 1)
        follow = Follow.objects.first()
        self.assertEqual(follow.author, leo)
        self.assertEqual(follow.user, self.user)

    def test_check_follow_non_auth(self):
        leo = User.objects.create_user(username="leo",
                                       email="leo@gmail.com",
                                       password="12345")
        self.non_auth_client.post(reverse("profile_follow", kwargs={
            'username': leo.username,
        }))
        self.assertEqual(leo.following.count(), 0)

    def test_check_unfollow(self):
        leo = User.objects.create_user(username="leo",
                                       email="leo@gmail.com",
                                       password="12345")
        Follow.objects.create(user=self.user, author=leo)
        self.client.post(reverse("profile_unfollow", kwargs={
            'username': leo.username,
        }))
        self.assertEqual(leo.following.count(), 0)

    def test_check_follow_posts(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile('small.gif', small_gif,
                                 content_type='image/gif')
        leo = User.objects.create_user(username="leo",
                                       email="leo@gmail.com",
                                       password="12345")
        Post.objects.create(text="post leo", group=self.group,
                            author=leo, image=img)
        self.client.post(reverse("profile_follow", kwargs={
            'username': leo.username,
        }))
        self.check_contain_post(reverse("follow_index"), leo, self.group, "post leo")

    def test_check_non_follow_posts(self):
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        img = SimpleUploadedFile('small.gif', small_gif,
                                 content_type='image/gif')
        mao = User.objects.create_user(username="mao",
                                       email="mao@gmail.com",
                                       password="12345")
        post_mao = Post.objects.create(text="post mao", group=self.group,
                                       author=mao, image=img)
        resp = self.client.get(reverse("follow_index"))
        self.assertNotContains(resp, post_mao.text)
