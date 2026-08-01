<!DOCTYPE html>

<html>

<head>

<title>
Library Dashboard
</title>

</head>


<body>


<h1>
Library Statistics
</h1>



<div>


<h2>
Books
</h2>


<p>
Total Books:
{{ $totalBooks }}
</p>


<p>
Borrowed Books:
{{ $borrowedBooks }}
</p>


<p>
Available Books:
{{ $availableBooks }}
</p>


</div>



<hr>



<div>


<h2>
Members
</h2>


<p>
Total Members:
{{ $totalMembers }}
</p>


</div>



<br>



<a href="/books">
Manage Books
</a>


<br>


<a href="/members">
Manage Members
</a>



</body>

</html>
