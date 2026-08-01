<!DOCTYPE html>

<html>

<head>

    <title>
        Borrow Book
    </title>

</head>



<body>



<h1>
    Borrow Book
</h1>




<h3>
    {{ $book->title }}
</h3>



<p>
Author:
{{ $book->author }}
</p>



<p>
Category:
{{ $book->category }}
</p>





<form action="/books/{{ $book->id }}/borrow"
      method="POST">


    @csrf



    <label>
        Select Member:
    </label>



    <br>



    <select name="member_id">


        @foreach($members as $member)


            <option value="{{ $member->id }}">

                {{ $member->name }}

            </option>


        @endforeach


    </select>




    <br><br>



    <button type="submit">

        Borrow Book

    </button>



</form>





<br>



<a href="/books">

    Back to Books

</a>



</body>


</html>
