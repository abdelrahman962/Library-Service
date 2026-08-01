<!DOCTYPE html>

<html>

<head>

<title>
Borrow Books
</title>

</head>


<body>


<h1>
{{ $member->name }} - Borrow Books
</h1>


@if(session('error'))

<h3>
{{ session('error') }}
</h3>

@endif


@if(session('success'))

<h3>
{{ session('success') }}
</h3>

@endif



<!-- Search -->

<form action="/members/{{ $member->id }}/books" method="GET">


<input
    type="text"
    name="search"
    placeholder="Search by title or category"
    value="{{ request('search') }}"
>


<button type="submit">

Search

</button>


</form>



<hr>



@if($books->count())


@foreach($books as $book)


<div>


<h2>
{{ $book->title }}
</h2>



<p>
<strong>
Author:
</strong>

{{ $book->author }}

</p>



<p>
<strong>
Category:
</strong>

{{ $book->category }}

</p>



<p>
<strong>
Publish Year:
</strong>

{{ $book->publish_year }}

</p>



@if($book->member)


<p>

<strong>
Status:
</strong>

Borrowed by {{ $book->member->name }}

</p>



<p>
This book is not available.
</p>



@else


<p>

<strong>
Status:
</strong>

Available

</p>



<form action="/members/{{ $member->id }}/books/{{ $book->id }}/borrow"
method="POST">


@csrf


<button type="submit">

Borrow Book

</button>


</form>



@endif



<hr>


</div>



@endforeach



@else


<h3>
No Books Found
</h3>


@endif




<a href="/members">

Back to Members

</a>



</body>


</html>
