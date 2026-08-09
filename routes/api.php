<?php

use Illuminate\Support\Facades\Route;

use App\Http\Controllers\BookController;
use App\Http\Controllers\MemberController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\BorrowHistoryController;


/*
|--------------------------------------------------------------------------
| Library API Routes
|--------------------------------------------------------------------------
*/


/*
|--------------------------------------------------------------------------
| Books
|--------------------------------------------------------------------------
*/

Route::apiResource(
    'books',
    BookController::class
);


/*
|--------------------------------------------------------------------------
| Members
|--------------------------------------------------------------------------
*/

Route::apiResource(
    'members',
    MemberController::class
);


/*
|--------------------------------------------------------------------------
| Borrowing
|--------------------------------------------------------------------------
*/

Route::get(
    '/members/{id}/books',
    [MemberController::class, 'borrowBooks']
);

Route::post(
    '/members/{id}/books/{bookId}/borrow',
    [MemberController::class, 'borrow']
);

Route::post(
    '/members/{id}/books/{bookId}/return',
    [MemberController::class, 'returnBook']
);


/*
|--------------------------------------------------------------------------
| Borrow History
|--------------------------------------------------------------------------
*/

Route::get(
    '/books/{id}/history',
    [BorrowHistoryController::class, 'bookHistory']
);


/*
|--------------------------------------------------------------------------
| Dashboard
|--------------------------------------------------------------------------
*/

Route::get(
    '/dashboard',
    [DashboardController::class, 'index']
);
