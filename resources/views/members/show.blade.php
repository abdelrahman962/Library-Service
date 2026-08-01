<!DOCTYPE html>
<html>
<head>
    <title>Member Details</title>
</head>
<body>
    <h1>{{ $member->name }}</h1>

    <p><strong>Email:</strong> {{ $member->email }}</p>

    <h2>Borrowed Books</h2>

    @if($member->books->count())
        <ul>
            @foreach($member->books as $book)
                <li>{{ $book->title }} ({{ $book->publish_year }})</li>
            @endforeach
        </ul>
    @else
        <p>No borrowed books.</p>
    @endif

    <p><a href="/members">Back to Members</a></p>
</body>
</html>
