<!DOCTYPE html>

<html>


<head>

<title>
Edit Book
</title>


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

Edit Book

</h1>



<form action="/books/{{ $book->id }}"

method="POST">



@csrf


@method('PUT')





<label>

Title:

</label>


<br>


<input

type="text"

name="title"

value="{{ $book->title }}"

>



<br><br>





<label>

Author:

</label>


<br>



<input

type="text"

name="author"

value="{{ $book->author }}"

>




<br><br>





<label>

Category:

</label>


<br>



<input

type="text"

name="category"

value="{{ $book->category }}"

>




<br><br>





<label>

Publish Year:

</label>


<br>



<input

type="number"

name="publish_year"

value="{{ $book->publish_year }}"

>




<br><br>





<button type="submit">

Update Book

</button>




</form>





<br>


<a href="/books">

Back to Books

</a>




</body>



</html>
