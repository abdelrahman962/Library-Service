<!DOCTYPE html>

<html>

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

<h1>Add Member</h1>

<form action="/members" method="POST">

    @csrf

    <label>Name</label>

    <input
        type="text"
        name="name"
    >

    <br><br>

    <label>Email</label>

    <input
        type="email"
        name="email"
    >

    <br><br>

    <button>

        Save Member

    </button>

</form>

</body>

</html>
