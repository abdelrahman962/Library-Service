<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Book;
use App\Services\LibraryService;
use App\Http\Requests\StoreBookRequest;
use App\Http\Requests\UpdateBookRequest;
use Exception;
use Illuminate\Support\Facades\Log;
use Illuminate\Database\Eloquent\ModelNotFoundException;
use App\Services\ActivityLogService;
class BookController extends Controller
{

    protected LibraryService $library;


    public function __construct(LibraryService $library)
    {
        $this->library = $library;
    }


    // GET /api/books
    public function index(Request $request)
    {
        try {

            $query = $this->library->displayBooks();


            // Search by title or category
            if ($request->filled('search')) {

                $search = $request->search;


                $bookIds = $this->library
                    ->searchBookByTitle($search)
                    ->pluck('id')
                    ->merge(
                        $this->library
                            ->searchBookByCategory($search)
                            ->pluck('id')
                    )
                    ->unique()
                    ->values();


                $query->whereIn('id', $bookIds);

            }



            // Sorting
            switch ($request->sort) {

                case 'title_asc':

                    $query->orderBy('title', 'asc');

                    break;


                case 'title_desc':

                    $query->orderBy('title', 'desc');

                    break;


                case 'newest':

                    $query->orderBy('publish_year', 'desc');

                    break;


                case 'oldest':

                    $query->orderBy('publish_year', 'asc');

                    break;
            }



            $books = $query->paginate(10);


            return response()->json([

                'success' => true,

                'data' => $books

            ]);


        } catch (Exception $e) {


            Log::error('Getting books failed', [

                'message' => $e->getMessage(),

                'line' => $e->getLine()

            ]);


            return response()->json([

                'success' => false,

                'message' => 'Unable to get books'

            ], 500);

        }
    }





    // GET /api/books/{id}
    public function show(int $id)
    {

        try {


            $book = Book::findOrFail($id);


            return response()->json([

                'success' => true,

                'data' => $book

            ]);


        } catch (ModelNotFoundException $e) {


        return response()->json([

            'success' => false,

            'message' => 'Book not found'

        ],404);



    } catch (Exception $e) {


        Log::error('Getting book failed',[

            'book_id'=>$id,

            'message'=>$e->getMessage()

        ]);


        return response()->json([

            'success'=>false,

            'message'=>'Unable to get book'

        ],500);
        }
    }





    // POST /api/books
    public function store(StoreBookRequest $request)
    {

        try {


            $book = $this->library->addBook(

                $request->validated()

            );




            return response()->json([

                'success' => true,

                'message' => 'Book created successfully',

                'data' => $book

            ], 201);



        } catch (Exception $e) {


            Log::error('Book creation failed', [

                'message' => $e->getMessage(),

                'file' => $e->getFile(),

                'line' => $e->getLine()

            ]);


            return response()->json([

                'success' => false,

                'message' => 'Unable to create book'

            ], 500);

        }

    }





    // PUT /api/books/{id}
    public function update(UpdateBookRequest $request, int $id)
    {

        try {


            $book = Book::findOrFail($id);


            $book->update(

                $request->validated()

            );




            return response()->json([

                'success' => true,

                'message' => 'Book updated successfully',

                'data' => $book

            ]);



        } catch(ModelNotFoundException $e)
{

    return response()->json([

        'success'=>false,

        'message'=>'Book not found'

    ],404);

}catch (Exception $e) {


            Log::error('Book update failed', [

                'book_id' => $id,

                'message' => $e->getMessage(),

                'line' => $e->getLine()

            ]);


            return response()->json([

                'success' => false,

                'message' => 'Unable to update book'

            ], 500);

        }

    }





    // DELETE /api/books/{id}
    public function destroy(int $id)
    {

        try {


            $book = Book::findOrFail($id);


            $this->library->removeBook($book);



            return response()->json([

                'success' => true,

                'message' => 'Book deleted successfully'

            ]);



        } catch (Exception $e) {


            Log::error('Book deletion failed', [

                'book_id' => $id,

                'message' => $e->getMessage()

            ]);


            return response()->json([

                'success' => false,

                'message' => 'Unable to delete book'

            ], 500);

        }

    }

}
