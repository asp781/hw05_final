from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='author_1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост12345',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        str_names = {
            self.post.text[:15]: str(self.post),
            self.group.title: str(self.group),
        }
        for expected_object_name, object_name_from_model in str_names.items():
            with self.subTest(expected_object_name=expected_object_name):
                self.assertEqual(
                    expected_object_name, object_name_from_model)
