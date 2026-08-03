<?php

namespace App\Http\Controllers;

use App\Models\Book;
use App\Models\Member;
use Exception;
use Illuminate\Support\Facades\Log;


class DashboardController extends Controller
{


    public function index()
    {

        try {


            // Total number of books
            $totalBooks = Book::count();



            // Books currently borrowed
            $borrowedBooks = Book::whereNotNull('member_id')
                ->count();



            // Books currently available
            $availableBooks = Book::whereNull('member_id')
                ->count();



            // Total members
            $totalMembers = Member::count();



            return response()->json([

                'message' => 'Library statistics retrieved successfully',

                'data' => [

                    'total_books' => $totalBooks,

                    'borrowed_books' => $borrowedBooks,

                    'available_books' => $availableBooks,

                    'total_members' => $totalMembers

                ]

            ],200);



        } catch(Exception $e) {


            Log::error('Dashboard statistics failed', [

                'message'=>$e->getMessage(),

                'line'=>$e->getLine(),

                'file'=>$e->getFile()

            ]);



            return response()->json([

                'message'=>'Unable to retrieve statistics',

                'error'=>$e->getMessage()

            ],500);


        }


    }


}
