<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\BookController;
use App\Http\Controllers\MemberController;
use App\Http\Controllers\DashboardController;



Route::middleware('log.api')->group(function () {


    /*
    |--------------------------------------------------------------------------
    | Books API
    |--------------------------------------------------------------------------
    */


    Route::get('/books', [BookController::class, 'index']);

    Route::post('/books', [BookController::class, 'store']);

    Route::get('/books/{id}', [BookController::class, 'show']);

    Route::put('/books/{id}', [BookController::class, 'update']);

    Route::delete('/books/{id}', [BookController::class, 'destroy']);




    /*
    |--------------------------------------------------------------------------
    | Members API
    |--------------------------------------------------------------------------
    */


    Route::get('/members', [MemberController::class, 'index']);

    Route::post('/members', [MemberController::class, 'store']);

    Route::get('/members/{id}', [MemberController::class, 'show']);

    Route::put('/members/{id}', [MemberController::class, 'update']);

    Route::delete('/members/{id}', [MemberController::class, 'destroy']);



    /*
    |--------------------------------------------------------------------------
    | Member Borrowing APIs
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
    | Dashboard API
    |--------------------------------------------------------------------------
    */


    Route::get('/dashboard', [DashboardController::class, 'index']);

});
