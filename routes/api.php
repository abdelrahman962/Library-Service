<?php

use Illuminate\Support\Facades\Route;

use App\Http\Controllers\AuthController;
use App\Http\Controllers\MemberAuthController;
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
| MEMBER AUTHENTICATION
|--------------------------------------------------------------------------
|
| Public routes. No token required.
|
*/

Route::post(
    '/member/register',
    [MemberAuthController::class, 'register']
);

Route::post(
    '/member/login',
    [MemberAuthController::class, 'login']
);


/*
|--------------------------------------------------------------------------
| ADMIN AUTHENTICATION
|--------------------------------------------------------------------------
|
| Public login route. No token required.
|
*/

Route::post(
    '/admin/login',
    [AuthController::class, 'login']
);


/*
|--------------------------------------------------------------------------
| MEMBER PROTECTED ROUTES
|--------------------------------------------------------------------------
|
| A valid Sanctum token is required.
|
*/

Route::middleware('auth:sanctum')->group(function () {

    /*
    |--------------------------------------------------------------------------
    | Member Authentication
    |--------------------------------------------------------------------------
    */

    Route::post(
        '/member/logout',
        [MemberAuthController::class, 'logout']
    );


    /*
    |--------------------------------------------------------------------------
    | Member Borrowing
    |--------------------------------------------------------------------------
    */

    Route::post(
        '/books/{bookId}/borrow',
        [MemberController::class, 'borrow']
    );

    Route::post(
        '/books/{bookId}/return',
        [MemberController::class, 'returnBook']
    );


    /*
    |--------------------------------------------------------------------------
    | Member's Current Books
    |--------------------------------------------------------------------------
    */

    Route::get(
        '/member/books',
        [MemberController::class, 'borrowBooks']
    );


    /*
    |--------------------------------------------------------------------------
    | Member's Borrow History
    |--------------------------------------------------------------------------
    */

    Route::get(
        '/member/history',
        [BorrowHistoryController::class, 'memberHistory']
    );

});


/*
|--------------------------------------------------------------------------
| ADMIN PROTECTED ROUTES
|--------------------------------------------------------------------------
|
| Requires:
|
| 1. Sanctum authentication
| 2. AdminOnly middleware
|
*/

Route::middleware([
    'auth:sanctum',
    'admin',
])->group(function () {

  Route::post(
        '/admin/logout',
        [AuthController::class, 'logout']
    );

    /*
    |--------------------------------------------------------------------------
    | Books
    |--------------------------------------------------------------------------
    */

    Route::patch(
    '/books/{id}/restore',
    [BookController::class, 'restore']
);

Route::patch(
    '/members/{id}/restore',
    [MemberController::class, 'restore']
);

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

});
