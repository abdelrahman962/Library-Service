<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Book;
class BorrowHistoryController extends Controller
{
    //

     public function bookHistory($id)
    {

        $book = Book::with('borrowHistories.member')
            ->findOrFail($id);


        return response()->json([

            'success'=>true,

            'book'=>$book->title,

            'history'=>$book->borrowHistories

        ]);

    }
}
