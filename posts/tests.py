from django.core.cache.utils import make_template_fragment_key
from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache
from django.core.files import File

from .models import Post, User, Group


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

    def check_contain_post(self, url, user, group, text):
        resp = self.client.get(url)
        post = None
        if 'paginator' in resp.context:
            if resp.context['paginator'].count == 1:
                post = resp.context['page'][0]
        else:
            post = resp.context['post']
        self.assertEqual(post.text, text)
        self.assertEqual(post.group, group)
        self.assertEqual(post.author, user)
        # self.assertContains(resp, "img")

    def test_check_post(self):
        post = Post.objects.create(text=self.text, group=self.group, author=self.user)
        with open('posts/7-3.jpg', 'rb') as img:
            self.client.post(reverse("post_edit", kwargs={'username': self.user.username, 'post_id': post.id}),
                             data={'group': self.group.id, 'text': self.text, 'image': img}, follow=True)
        list_urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id})
        ]
        for url in list_urls:
            self.check_contain_post(url, self.user, self.group, self.text)

    def test_check_edit(self):
        post = Post.objects.create(text=self.text, group=self.group, author=self.user)
        group = Group.objects.create(title="chim", slug="chim", description="chim kim")
        new_text = "Chim bir fir"
        with open('posts/7-3.jpg', 'rb') as img:
            self.client.post(reverse("post_edit", kwargs={'username': self.user.username, 'post_id': post.id}),
                             data={'group': group.id, 'text': new_text, 'image': img}, follow=True)
        list_urls = [
            reverse('index'),
            reverse('profile', kwargs={'username': self.user.username}),
            reverse('post', kwargs={'username': self.user.username, 'post_id': post.id})
        ]
        for url in list_urls:
            self.check_contain_post(url, self.user, group, new_text)
        resp_post = self.client.get(reverse('post', kwargs={'username': self.user.username,
                                                            'post_id': post.id}))
        resp_group = self.client.get(reverse('groups', kwargs={'slug': self.group.slug}))
        self.assertNotContains(resp_post, self.text)
        self.assertEqual(resp_group.context['paginator'].count, 0)
        with open('posts/admin.py', 'rb') as img:
            resp_no_image = self.client.post(
                reverse("post_edit", kwargs={'username': self.user.username, 'post_id': post.id}),
                data={'group': group.id, 'text': new_text, 'image': img})
        self.assertNotEqual(resp_no_image.status_code, 302)

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
        resp = self.client.post(reverse("add_comment", kwargs={
            'username': self.user.username,
            'post_id': post.id
        }),
                                data={
                                    'text': 'Comment',
                                    'post': post.id,
                                    'author': self.user.id
                                })
        resp_non_auth = self.non_auth_client.post(reverse("add_comment", kwargs={
            'username': self.user.username,
            'post_id': post.id
        }),
                                                  data={
                                                      'text': 'Comment',
                                                      'post': post.id,
                                                      'author': self.user.id
                                                  })
        self.assertRedirects(resp, reverse("post", kwargs={
            'username': post.author,
            'post_id': post.id
        }))
        self.assertRedirects(resp_non_auth, "/auth/login/?next=" +
                             reverse("add_comment", kwargs={
                                 'username': post.author,
                                 'post_id': post.id
                             }))

    def test_check_follow(self):
        leo = User.objects.create_user(username="leo",
                                       email="leo@gmail.com",
                                       password="12345")
        resp = self.client.post(reverse("profile_follow", kwargs={
            'username': leo.username,
        }))
        self.assertRedirects(resp, reverse("profile",
                                           kwargs={
                                               'username': leo.username
                                           }))
        self.assertEqual(leo.following.count(), 1)
        resp = self.client.post(reverse("profile_unfollow", kwargs={
            'username': leo.username,
        }))
        self.assertEqual(leo.following.count(), 0)
        resp_non_auth = self.non_auth_client.post(reverse("profile_follow", kwargs={
            'username': leo.username,
        }))
        self.assertEqual(leo.following.count(), 0)

    def test_check_follow_posts(self):
        leo = User.objects.create_user(username="leo",
                                       email="leo@gmail.com",
                                       password="12345")
        mao = User.objects.create_user(username="mao",
                                       email="mao@gmail.com",
                                       password="12345")
        post_leo = Post.objects.create(text="post leo", group=self.group,
                                       author=leo)
        post_mao = Post.objects.create(text="post mao", group=self.group,
                                       author=mao)
        resp_follow = self.client.post(reverse("profile_follow", kwargs={
            'username': leo.username,
        }))
        resp = self.client.get(reverse("follow_index"))
        self.check_contain_post(reverse("follow_index"), leo, self.group, "post leo")
        self.assertNotContains(resp, post_mao.text)
