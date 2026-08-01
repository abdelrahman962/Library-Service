<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Book;
use App\Services\LibraryService;

class BookController extends Controller
{
protected $library;

public function __construct(LibraryService $library)
{
    $this->library = $library;
}

public function index(Request $request)
{
    $query = $this->library->displayBooks();

    if ($request->filled('search')) {
        $search = $request->search;

        $bookIds = $this->library->searchBookByTitle($search)
            ->pluck('id')
            ->merge($this->library->searchBookByCategory($search)->pluck('id'))
            ->unique()
            ->values();

        $query->whereIn('id', $bookIds);
    }



    // Sorting
    switch($request->sort)
    {

        case 'title_asc':

            $query->orderBy('title','asc');

            break;



        case 'title_desc':

            $query->orderBy('title','desc');

            break;



        case 'newest':

            $query->orderBy('publish_year','desc');

            break;



        case 'oldest':

            $query->orderBy('publish_year','asc');

            break;

    }



    $books = $query->paginate(10);



    return view('books.index', compact('books'));

}


public function show(Book $book)
{
    return view('books.show', compact('book'));
}



    // Show create form
    public function create()
    {
        return view('books.create');
    }



    // Store new book
    public function store(Request $request)
    {

     $request->validate([

        'title'=>'required|string|max:255',

        'author'=>'required|string|max:255',

        'category'=>'required|string|max:255',

        'publish_year'=>'required|integer|min:0|max:'.date('Y')

    ]);

        $this->library->addBook([

            'title'=>$request->title,

            'author'=>$request->author,

            'category'=>$request->category,

            'publish_year'=>$request->publish_year

        ]);


        return redirect('/books')
        ->with('success','Book added successfully');

    }




    // Show edit form
    public function edit(Book $book)
    {

        return view('books.edit', compact('book'));

    }




    // Update book
    public function update(Request $request, Book $book)
    {
$request->validate([

        'title'=>'required|string|max:255',

        'author'=>'required|string|max:255',

        'category'=>'required|string|max:255',

        'publish_year'=>'required|integer|min:0|max:'.date('Y')

    ]);
        $book->update([

            'title'=>$request->title,

            'author'=>$request->author,

            'category'=>$request->category,

            'publish_year'=>$request->publish_year

        ]);


          return redirect('/books')
    ->with('success','Book updated successfully');

    }




    // Delete book
    public function destroy(Book $book)
    {

        $this->library->removeBook($book);


        return redirect('/books');

    }





    // Return book
    public function returnBook(Book $book)
    {


        $book->update([

            'member_id'=>null

        ]);



        return redirect('/books')
        ->with('success','Book returned successfully');

    }



}
