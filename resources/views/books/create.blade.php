<!DOCTYPE html>

<html>

<head>
    <title>Add Book</title>
</head>


<body>
@if($errors->any())

<div>

@foreach($errors->all() as $error)

<p>
{{ $error }}
</p>

@endforeach

</div>

@endif

<h1>
Add New Book
</h1>


<form action="/books" method="POST">

    @csrf


    <label>
        Title
    </label>

    <input type="text" name="title">

    <br><br>


    <label>
        Author
    </label>

    <input type="text" name="author">

    <br><br>


    <label>
        Category
    </label>

    <input type="text" name="category">

    <br><br>


    <label>
        Publish Year
    </label>

    <input type="number" name="publish_year">

    <br><br>


    <button type="submit">
        Save Book
    </button>


</form>


</body>

</html>
