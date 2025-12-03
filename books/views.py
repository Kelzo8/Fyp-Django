from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .models import Book


def book_list(request):
    """Display all books."""
    books = Book.objects.all().order_by("id")
    return render(request, "books/book_list.html", {"books": books})


def book_create(request):
    """Show a form to add a new book and process form submissions."""
    if request.method == "POST":
        title = request.POST.get("title")
        author = request.POST.get("author")
        published_date = request.POST.get("published_date")

        if title and author and published_date:
            Book.objects.create(
                title=title,
                author=author,
                published_date=published_date,
            )
            return redirect(reverse("book_list"))

    return render(request, "books/book_form.html")


def book_update(request, id):
    """Show a form to edit an existing book and save changes."""
    book = get_object_or_404(Book, id=id)

    if request.method == "POST":
        title = request.POST.get("title")
        author = request.POST.get("author")
        published_date = request.POST.get("published_date")

        if title and author and published_date:
            book.title = title
            book.author = author
            book.published_date = published_date
            book.save()
            return redirect(reverse("book_list"))

    return render(request, "books/book_form.html", {"book": book})


def book_delete(request, id):
    """Show a confirmation page and delete a book when confirmed."""
    book = get_object_or_404(Book, id=id)

    if request.method == "POST":
        book.delete()
        return redirect(reverse("book_list"))

    return render(request, "books/book_confirm_delete.html", {"book": book})

