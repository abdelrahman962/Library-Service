<?php

use Illuminate\Support\Facades\Route;

use App\Http\Controllers\MemberAuthController;
use App\Http\Controllers\BookController;
use App\Http\Controllers\MemberController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\BorrowHistoryController;


/*
|--------------------------------------------------------------------------
| Library API Routes
|--------------------------------------------------------------------------
|
| Single authenticatable model: Member. Some members are flagged as
| admins via the is_admin column, gating a separate set of routes
| below through the 'admin' middleware.
|
*/


/*
|--------------------------------------------------------------------------
| AUTHENTICATION
|--------------------------------------------------------------------------
|
| Public routes. No token required.
|
*/

Route::post(
    '/register',
    [MemberAuthController::class, 'register']
);

Route::post(
    '/login',
    [MemberAuthController::class, 'login']
);


/*
|--------------------------------------------------------------------------
| MEMBER PROTECTED ROUTES
|--------------------------------------------------------------------------
|
| A valid Sanctum token is required. Any authenticated member
| (admin or not) can access these.
|
*/

Route::middleware('auth:sanctum')->group(function () {

    /*
    |--------------------------------------------------------------------------
    | Authentication
    |--------------------------------------------------------------------------
    */

    Route::post(
        '/logout',
        [MemberAuthController::class, 'logout']
    );


    /*
    |--------------------------------------------------------------------------
    | Borrowing
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
| 2. AdminOnly middleware (checks $request->user()->is_admin)
|
*/

Route::middleware([
    'auth:sanctum',
    'admin',
])->group(function () {

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
