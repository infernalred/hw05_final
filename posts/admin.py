from django.contrib import admin

# Register your models here.
from .models import Post, Group, Comment, Follow


class PostAdmin(admin.ModelAdmin):
    list_display = ("pk", "text", "pub_date", "author", "group")
    search_fields = ("text",)
    list_filter = ("pub_date", "group",)
    empty_value_display = '-пусто-'


admin.site.register(Post, PostAdmin)


class GroupAdmin(admin.ModelAdmin):
    list_display = ("pk", "title", "slug", "description")
    search_fields = ("title",)
    list_filter = ("slug",)
    empty_value_display = '-пусто-'


admin.site.register(Group, GroupAdmin)


class CommentAdmin(admin.ModelAdmin):
    list_display = ("pk", "text", "created", "author", "post")
    search_fields = ("text",)
    list_filter = ("created", "author", "post",)
    empty_value_display = '-пусто-'


admin.site.register(Comment, CommentAdmin)


class FollowAdmin(admin.ModelAdmin):
    list_display = ("pk", "user", "author")
    search_fields = ("user",)
    list_filter = ("user", "author",)
    empty_value_display = '-пусто-'


admin.site.register(Follow, FollowAdmin)
