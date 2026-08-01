<!DOCTYPE html>
<!DOCTYPE html>

<html>

<head>
    <title>Books</title>
</head>

<body>

@if(session('success'))
<h3>
    {{ session('success') }}
</h3>
@endif

@if(session('error'))
<h3>
    {{ session('error') }}
</h3>
@endif

<!-- Search + Sorting -->
<form action="/books" method="GET">

<input
type="text"
name="search"
placeholder="Search by title or category"
value="{{ request('search') }}"
>

<select name="sort">
<option value="">Sort By</option>

<option value="title_asc" @if(request('sort') == 'title_asc') selected @endif>
Title A-Z
</option>

<option value="title_desc" @if(request('sort') == 'title_desc') selected @endif>
Title Z-A
</option>

<option value="newest" @if(request('sort') == 'newest') selected @endif>
Newest Books
</option>

<option value="oldest" @if(request('sort') == 'oldest') selected @endif>
Oldest Books
</option>
</select>

<button type="submit">
Search
</button>

</form>

<br>

<a href="/books/create">
Add Book
</a>

<hr>

@if($books->count() > 0)

@foreach($books as $book)
<div>

<h3>
<a href="/books/{{ $book->id }}">
{{ $book->title }}
</a>
</h3>

<p>
Author:
{{ $book->author }}
</p>

<p>
Category:
{{ $book->category }}
</p>

<p>
Year:
{{ $book->publish_year }}
</p>

@if($book->member)
<p>
<strong>
Borrowed by:
</strong>

{{ $book->member->name }}
</p>
@else
<p>
<strong>
Available
</strong>
</p>
@endif

<br>

<a href="/books/{{ $book->id }}/edit">
Edit
</a>

<form action="/books/{{ $book->id }}" method="POST" style="display:inline;">
@csrf
@method('DELETE')

<button type="submit">
Delete
</button>
</form>

</div>

<hr>
@endforeach

<!-- Pagination -->
{{ $books->appends(request()->query())->links('pagination.custom') }}

<br>

<a href="/dashboard">
Dashboard
</a>

@else

<h3>
No Books Found
</h3>

@endif

</body>

</html>



<br>


<a href="/dashboard">

Dashboard

</a>



</body>

</html>
