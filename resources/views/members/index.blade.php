<!DOCTYPE html>

<html>

<head>

<title>
Members
</title>

</head>


<body>


<h1>
Library Members
</h1>
<form action="/members" method="GET">

    <input
        type="text"
        name="search"
        placeholder="Search by name or email"
        value="{{ request('search') }}"
    >

    <button type="submit">
        Search
    </button>

</form>


<a href="/members/create">
Add Member
</a>



<hr>



@if(session('success'))

<h3>
{{session('success')}}
</h3>

@endif



@if($members->count())


@foreach($members as $member)



<div>


<h3>
<a href="/members/{{ $member->id }}">
{{ $member->name }}
</a>
</h3>



<p>
{{ $member->email }}
</p>



<a href="/members/{{ $member->id }}/books">

Borrow Books

</a>



<h4>
Borrowed Books:
</h4>


@if($member->books->count())


<ul>

@foreach($member->books as $book)


<li>


{{ $book->title }}


<form action="/members/{{ $member->id }}/books/{{ $book->id }}/return"
method="POST"
style="display:inline;">


@csrf


<button type="submit">

Return Book

</button>


</form>



</li>



@endforeach


</ul>


@else


<p>
No borrowed books
</p>


@endif


</div>


<hr>



@endforeach
{{ $members->appends(request()->query())->links('pagination.custom') }}

<br>

<a href="/dashboard">
Dashboard
</a>

@else


<h3>
No Members Found
</h3>


@endif



</body>
</html>
