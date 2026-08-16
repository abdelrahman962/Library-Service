<?php

namespace App\Http\Controllers;
use App\Models\BorrowHistory;

use Illuminate\Http\Request;
use App\Models\Book;
class BorrowHistoryController extends Controller
{
    //

     public function bookHistory(int $id)
    {

        $book = Book::with([
    'borrowHistories.member:id,name,email'
])->findOrFail($id);


        return response()->json([

            'success'=>true,

            'book'=>$book->title,

            'history'=>$book->borrowHistories

        ]);

    }

public function memberHistory(Request $request)
{
    $member = $request->user();

    $history = BorrowHistory::where(
        'member_id',
        $member->id
    )
    ->with('book')
    ->latest('borrowed_at')
    ->get();

    return response()->json([
        'success' => true,
        'data' => $history
    ]);
}


}
