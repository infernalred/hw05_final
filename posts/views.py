from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.urls import reverse

from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow


def index(request):
    post_list = Post.objects.order_by('-pub_date').all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, "index.html", {"page": page,
                                          "paginator": paginator})


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = Post.objects.filter(group=group).all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, "group.html", {"page": page,
                                          "group": group,
                                          "paginator": paginator})


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            form.save()
            return redirect("index")
        return render(request, "new_post.html", {'form': form})

    form = PostForm()
    return render(request, "new_post.html", {'form': form,
                                             'is_edit': False})


def profile(request, username):
    user = get_object_or_404(User, username=username)
    post_list = user.posts.all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    is_following = False
    if request.user.is_authenticated:
        is_following = request.user.follower.filter(author=user).exists()
    return render(request, "profile.html", {"page": page,
                                            "author": user,
                                            "paginator": paginator,
                                            "is_following": is_following})


def post_view(request, username, post_id):
    form = CommentForm()
    post = get_object_or_404(Post.objects.select_related('author'),
                             pk=post_id, author__username=username)
    comments = post.comments.select_related('author')
    is_following = False
    if request.user.is_authenticated:
        is_following = request.user.follower.filter(author=post.author).exists()
    return render(request, 'post.html', {"post": post,
                                         "author": post.author,
                                         "form": form,
                                         "comments": comments,
                                         "is_following": is_following})


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    if request.user != post.author:
        return redirect(reverse("post", kwargs={'username': username, 'post_id': post_id}))

    form = PostForm(request.POST or None, files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect(reverse("post", kwargs={'username': username, 'post_id': post_id}))

    return render(request, "new_post.html", {'form': form, 'post': post, 'is_edit': True})


def page_not_found(request, exception):
    # Переменная exception содержит отладочную информацию,
    # выводить её в шаблон пользователской страницы 404 мы не станем
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            form.save()
    return redirect(reverse("post", kwargs={
                'username': username, 'post_id': post_id}))


@login_required
def follow_index(request):
    post_list = Post.objects.select_related('author').\
        filter(author__following__user=request.user)
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request,
                  "follow.html",
                  {"page": page,
                   "paginator": paginator})


@login_required
def profile_follow(request, username):
    if username != request.user.username:
        author = get_object_or_404(User, username=username)
        follow, created = Follow.objects.get_or_create(user=request.user, author=author)
        follow.save()
    return redirect(reverse("profile", kwargs={'username': username}))


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    follow, created = Follow.objects.get_or_create(user=request.user, author=author)
    follow.delete()
    return redirect(reverse("profile", kwargs={'username': username}))
