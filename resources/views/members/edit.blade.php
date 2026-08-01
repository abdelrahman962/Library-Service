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

<h1>Edit Member</h1>

<form action="/members/{{ $member->id }}" method="POST">

    @csrf

    @method('PUT')

    <label>Name</label>

    <input
        type="text"
        name="name"
        value="{{ $member->name }}"
    >

    <br><br>

    <label>Email</label>

    <input
        type="email"
        name="email"
        value="{{ $member->email }}"
    >

    <br><br>

    <button>

        Update Member

    </button>

</form>

</body>

</html>
