from django.forms import ModelForm, Textarea
from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('group', 'text', 'image')
        labels = {
            'group': 'Группа',
            'text': 'Текст',
            'image': 'Изображение'
        }
        help_texts = {
            'group': 'Выберите группу',
            'text': 'Впишите текст новости'
        }


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст'
        }
        help_texts = {
            'text': 'Ваш комментарий'
        }
