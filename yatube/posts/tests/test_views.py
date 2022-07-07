import shutil
import tempfile

import django.core.paginator
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from ..models import Comment, Follow, Group, Post
from .utils import name_to_url

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author_1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
            image=uploaded,
        )

        cls.INDEX = ('posts:index', None, 'posts/index.html')
        cls.GROUP = (
            'posts:group_list', [cls.group.slug], 'posts/group_list.html'
        )
        cls.PROFILE = (
            'posts:profile', [cls.author.username], 'posts/profile.html'
        )
        cls.POST_DETAIL = (
            'posts:post_detail', [cls.post.id], 'posts/post_detail.html'
        )
        cls.POST_EDIT = (
            'posts:post_edit', [cls.post.id], 'posts/create_post.html'
        )
        cls.POST_CREATE = ('posts:post_create', None, 'posts/create_post.html')
        cls.names_urls_templates = (
            cls.INDEX, cls.GROUP, cls.PROFILE, cls.POST_DETAIL, cls.POST_EDIT,
            cls.POST_CREATE,
        )
        cls.post_list = (cls.INDEX,
                         cls.GROUP, cls.PROFILE,)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_pages_uses_correct_template(self):
        """Проверка namespase:name и шаблонов"""
        cache.clear()
        for name, url, template in self.names_urls_templates:
            with self.subTest(name=name):
                response = self.authorized_client.get(name_to_url((name, url)))
                self.assertTemplateUsed(response, template)

    def assert_post_response(self, some_object):
        """Проверка полей"""
        post_fields = (
            [some_object.text, self.post.text],
            [some_object.author, self.author],
            [some_object.group, self.group],
            [some_object.id, self.post.id],
            [some_object, self.post],
            [some_object.image, self.post.image],
        )
        for value, expected in post_fields:
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_list_page_show_correct_context(self):
        """Шаблоны сформированы с правильным контекстом."""
        cache.clear()
        for name in self.post_list:
            with self.subTest(name=name):
                response = self.authorized_client.get(name_to_url(name))
                some_object = response.context['page_obj'][0]
                self.assert_post_response(some_object)
                self.assertIn('page_obj', response.context)
                self.assertIsInstance(response.context['page_obj'],
                                      django.core.paginator.Page)

    def test_post_detail_pages_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = (self.authorized_client.get(
                    name_to_url(self.POST_DETAIL)))
        some_object = response.context['post']
        self.assert_post_response(some_object)

    def test_post_edit_page_show_correct_context(self):
        """При вызове post_edit передан правильный context."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        response = self.authorized_client.get(name_to_url(self.POST_EDIT))
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_create_page_show_correct_context(self):
        """При вызове post_create передан правильный context."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        response = (self.authorized_client.get(
                    name_to_url(self.POST_CREATE)))
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_in_pages(self):
        """Пост имеющий группу на страницах."""
        cache.clear()
        for name in self.post_list:
            with self.subTest(name=name):
                response = self.authorized_client.get(name_to_url(name))
                self.assertIn(self.post, response.context['page_obj'])

    def test_post_not_in_group2(self):
        """Пост не попал в группу2, для которой не был предназначен."""
        self.group = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        self.GROUP2 = ('posts:group_list', [self.group.slug])
        response = self.authorized_client.get(name_to_url(self.GROUP2))
        self.assertNotIn(self.post, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author_2')
        cls.group = Group.objects.create(
            title='Тестовая группа3',
            slug='test-slug3',
            description='Тестовое описание3',
        )
        for post in range(13):
            Post.objects.create(
                text=f'text{post}',
                author=cls.author,
                group=cls.group
            )
        cls.INDEX = ('posts:index', None)
        cls.GROUP = ('posts:group_list', [cls.group.slug])
        cls.PROFILE = ('posts:profile', [cls.author.username])

        cls.page_list = (cls.INDEX, cls.GROUP, cls.PROFILE,)
        cls.POSTS_ON_PAGE = 10
        cls.REMAIN_OF_POSTS = 3

    def test_first_page_contains_ten_records(self):
        cache.clear()
        for name in self.page_list:
            with self.subTest(name=name):
                response = self.client.get(name_to_url(name))
                self.assertEqual(
                    len(response.context['page_obj']), self.POSTS_ON_PAGE
                )

    def test_second_page_contains_three_records(self):
        for name in self.page_list:
            with self.subTest(name=name):
                response = self.client.get(name_to_url(name) + '?page=2')
                self.assertEqual(
                    len(response.context['page_obj']), self.REMAIN_OF_POSTS
                )


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author_1')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def test_cache_index(self):
        """Тест кэширования страницы index.html"""
        self.INDEX = ('posts:index', None)
        response1 = self.authorized_client.get(name_to_url(self.INDEX))
        self.post.delete()
        response2 = self.authorized_client.get(name_to_url(self.INDEX))
        self.assertEqual(response1.content, response2.content)
        cache.clear()
        response3 = self.authorized_client.get(name_to_url(self.INDEX))
        self.assertNotEqual(response1.content, response3.content)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_follower = User.objects.create_user(username='follower')
        cls.user_following = User.objects.create_user(username='following')
        cls.user_not_follower = User.objects.create_user(
            username='not_follower'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user_following,
        )
        cls.PROFILE_FOLLOW = (
            'posts:profile_follow', [cls.user_following.username]
        )
        cls.PROFILE_UNFOLLOW = (
            'posts:profile_unfollow', [cls.user_following.username]
        )

    def setUp(self):
        self.client_follower = Client()
        self.client_follower.force_login(self.user_follower)
        self.client_following = Client()
        self.client_following.force_login(self.user_following)
        self.client_not_follower = Client()
        self.client_not_follower.force_login(self.user_not_follower)

    def test_follow_and_unfollow(self):
        """Авторизованный пользователь может подписаться и отписаться"""
        self.client_follower.get(name_to_url(self.PROFILE_FOLLOW))
        self.assertEqual(Follow.objects.all().count(), 1)
        self.client_follower.get(name_to_url(self.PROFILE_UNFOLLOW))
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_subscribe_to_author(self):
        """Запись появляется в ленте Избранные авторы"""
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        response = self.client_follower.get('/follow/')
        post = response.context['page_obj'][0]
        self.assertEqual(post.text, self.post.text)
        response = self.client_not_follower.get('/follow/')
        self.assertNotContains(response, self.post.text)


class CommentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='commentator_1')
        cls.author = User.objects.create_user(username='author_1')
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
        )
        cls.POST_DETAIL = ('posts:post_detail', [cls.post.id])
        cls.COMMENT = ('posts:add_comment', [cls.post.id])

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_add_comment(self):
        """Отправка валидная форма -> создание комментария к посту."""
        comments_count = Comment.objects.count()
        form_data = {
            'post': self.post,
            'author': self.user,
            'text': 'Комментарий',
        }
        response = self.authorized_client.post(
            name_to_url(self.COMMENT),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, name_to_url(self.POST_DETAIL))
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        new_comment = Comment.objects.all().first()
        self.assertEqual(new_comment.text, form_data['text'])
        self.assertEqual(new_comment.author, self.user)
        self.assertEqual(new_comment.post, self.post)
