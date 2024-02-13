from django.shortcuts import render
from categories.models import Category
from books.models import Book


def home(request):
    categories = Category.objects.all()
    books = Book.objects.all()
    context = {'categories': categories, 'books': books}
    return render(request, 'home.html', context)


def filter_by_category(request, category_id):
    categories = Category.objects.all()
    books = Book.objects.filter(category=category_id)
    context = {'categories': categories, 'books': books}
    return render(request, 'home.html', context)
