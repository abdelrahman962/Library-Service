<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;



use App\Models\Book;
use App\Models\Member;


class DashboardController extends Controller
{


    public function index()
    {


        // Count all books
        $totalBooks = Book::count();



        // Books that have a member_id
        // means they are borrowed

        $borrowedBooks = Book::whereNotNull('member_id')
                            ->count();



        // Books that do not have member_id
        // means they are available

        $availableBooks = Book::whereNull('member_id')
                            ->count();



        // Count members

        $totalMembers = Member::count();



        return view('dashboard', compact(

            'totalBooks',

            'borrowedBooks',

            'availableBooks',

            'totalMembers'

        ));

    }


}
