<?php

namespace App\Http\Controllers;

use App\Models\Member;
use App\Models\Book;
use Illuminate\Http\Request;
use App\Services\LibraryService;


class MemberController extends Controller
{

protected $library;


public function __construct(LibraryService $library)
{
    $this->library = $library;
}


   public function index(Request $request)
{

    $search = $request->search;


    if($search){

        $members = Member::where('name','like','%'.$search.'%')
        ->orWhere('email','like','%'.$search.'%')
        ->with('books')
        ->paginate(5);


    }else{


        $members = Member::with('books')
        ->paginate(5);

    }


    return view('members.index', compact('members'));

}



    public function create()
    {
        return view('members.create');
    }



    public function store(Request $request)
    {

        $request->validate([

            'name'=>'required|string|max:255',

            'email'=>'required|email|unique:members,email'

        ]);


        $this->library->addMember([

            'name'=>$request->name,

            'email'=>$request->email

        ]);


        return redirect('/members')
        ->with('success','Member added successfully');

    }




    public function edit(Member $member)
    {
        return view('members.edit',compact('member'));
    }



    public function show(Member $member)
    {
        $member->load('books');

        return view('members.show', compact('member'));
    }




    public function update(Request $request, Member $member)
    {

        $request->validate([

            'name'=>'required|string|max:255',

            'email'=>'required|email|unique:members,email,'.$member->id

        ]);


        $member->update([

            'name'=>$request->name,

            'email'=>$request->email

        ]);


        return redirect('/members');

    }





    public function destroy(Member $member)
    {

        $member->delete();


        return redirect('/members');

    }



public function borrowBooks(Request $request, Member $member)
{

    $search = $request->search;


    if($search){

        $books = Book::where('title','like','%'.$search.'%')
            ->orWhere('category','like','%'.$search.'%')
            ->paginate(5);

    }
    else{

        $books = Book::paginate(5);

    }


    return view('members.borrow',
    compact('member','books'));

}



    // Borrow book

    public function borrow(Member $member, Book $book)
    {


        if(!$book->isAvailable()){


            return redirect()
            ->back()
            ->with('error',
            'This book is already borrowed.');

        }



        $book->update([

            'member_id'=>$member->id

        ]);



        return redirect()
        ->back()
        ->with('success',
        'Book borrowed successfully.');

    }
public function returnBook(Member $member, Book $book)
{

    // Check that this book belongs to this member

    if($book->member_id != $member->id){

        return redirect()
        ->back()
        ->with('error',
        'This book is not borrowed by this member.');

    }



    // Make the book available again

    $book->update([

        'member_id'=>null

    ]);



    return redirect()
    ->back()
    ->with('success',
    'Book returned successfully.');

}

}
