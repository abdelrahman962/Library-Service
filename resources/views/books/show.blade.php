<!DOCTYPE html>
<html>
<head>
    <title>Book Details</title>
</head>
<body>
    <h1>{{ $book->title }}</h1>

    <p><strong>Author:</strong> {{ $book->author }}</p>
    <p><strong>Category:</strong> {{ $book->category }}</p>
    <p><strong>Publish Year:</strong> {{ $book->publish_year }}</p>

    @if($book->member)
        <p><strong>Borrowed by:</strong> {{ $book->member->name }}</p>
    @else
        <p><strong>Status:</strong> Available</p>
    @endif

    <p><a href="/books">Back to Books</a></p>
</body>
</html>
