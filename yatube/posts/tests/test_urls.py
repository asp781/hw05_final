from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author_1')
        cls.user = User.objects.create_user(username='author_2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group
        )

        cls.INDEX = ('/', 'posts/index.html')
        cls.GROUP = (f'/group/{cls.group.slug}/', 'posts/group_list.html')
        cls.PROFILE = (
            f'/profile/{cls.author.username}/', 'posts/profile.html'
        )
        cls.POST_DETAIL = (
            f'/posts/{cls.post.id}/', 'posts/post_detail.html'
        )
        cls.POST_EDIT = (
            f'/posts/{cls.post.id}/edit/', 'posts/create_post.html'
        )
        cls.POST_CREATE = ('/create/', 'posts/create_post.html')

        cls.url_200_unauth = [
            cls.INDEX, cls.GROUP, cls.PROFILE, cls.POST_DETAIL
        ]
        cls.url_302_unauth = [cls.POST_EDIT, cls.POST_CREATE]
        cls.url_200_auth = (
            cls.INDEX, cls.GROUP, cls.PROFILE, cls.POST_DETAIL, cls.POST_CREATE
        )
        cls.url = cls.url_200_unauth + cls.url_302_unauth

    def setUp(self):
        self.guest_client = Client()
        self.author_post_client = Client()
        self.author_post_client.force_login(self.author)
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_unauthorized_user_access_code_200(self):
        """Cтраницы доступные неавторизованому пользователю."""
        for address, template in self.url_200_unauth:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unauthorized_user_access_code_302(self):
        """Страницы перенаправляющие неавторизованого пользователя."""
        for address, template in self.url_302_unauth:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_unauthorized_user_access_code_404(self):
        """Несуществующая страница для неавторизованого пользователя."""
        response = self.guest_client.get('/unexistint_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_authorized_user_access_code_200(self):
        """Cтраницы доступные авторизованому пользователю."""
        for address, template in self.url_200_auth:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorized_user_access_code_302(self):
        """Страница перенаправляющая авторизованого пользователя."""
        response = self.authorized_client.get(self.POST_EDIT[0])
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_authorized_user_access_code_404(self):
        """Несуществующая страница для авторизованого пользователя."""
        response = self.authorized_client.get('/unexistint_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_edit_only_author(self):
        """Страница /posts/<post_id>/edit/ доступна только автору поста."""
        response = self.author_post_client.get(self.POST_EDIT[0])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """Проверка вызываемых шаблонов для каждого адреса."""
        cache.clear()
        for address, template in self.url:
            with self.subTest(address=address):
                response = self.author_post_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_page_not_found_404(self):
        """Страница 404 отдает кастомный шаблон"""
        response = self.author_post_client.get('/unexistint_page/')
        self.assertTemplateUsed(response, 'core/404.html')
