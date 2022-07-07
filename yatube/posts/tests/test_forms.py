import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from ..forms import PostForm
from ..models import Group, Post
from .utils import name_to_url

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='author_1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.author,
            group=cls.group,
        )
        cls.form = PostForm()
        cls.PROFILE = ('posts:profile', [cls.author.username])
        cls.POST_DETAIL = ('posts:post_detail', [cls.post.id])
        cls.POST_EDIT = ('posts:post_edit', [cls.post.id])
        cls.POST_CREATE = ('posts:post_create', None)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.author)

    def assert_form_data(self, form_data):
        """Проваеряем поля на соответствие подготовленным данным"""
        new_post = Post.objects.all().first()
        post_fields = (
            [new_post.text, form_data['text']],
            [new_post.author, self.author],
            [new_post.group, self.group],
        )
        for value, expected in post_fields:
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_create_post(self):
        """Отправка валидная форма -> создание поста в БД."""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'Новый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            name_to_url(self.POST_CREATE),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, name_to_url(self.PROFILE))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assert_form_data(form_data)
        self.assertEqual(Post.objects.all().first().image, 'posts/small.gif')
        self.assertTrue(
            Post.objects.filter(
                text=form_data.get('text'),
                author=self.author,
                group=form_data.get('group'),
                image='posts/small.gif'
            ).exists()
        )

    def test_edit_post(self):
        """Отправка валидная форма -> изменение поста в БД."""
        posts_count = Post.objects.count()
        self.group = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug2',
            description='Тестовое описание2',
        )
        form_data = {
            'text': 'Редактированный текст',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            name_to_url(self.POST_EDIT),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, name_to_url(self.POST_DETAIL))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assert_form_data(form_data)
