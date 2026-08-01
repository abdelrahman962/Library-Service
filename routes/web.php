<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\BookController;
use App\Http\Controllers\MemberController;
use App\Http\Controllers\DashboardController;


Route::redirect('/', '/dashboard');

Route::resource('books', BookController::class);
Route::resource('members', MemberController::class);



// Show books for a member to borrow
Route::get('/members/{member}/books',
    [MemberController::class,'borrowBooks'])
    ->name('members.borrow.books');


// Borrow selected book
Route::post('/members/{member}/books/{book}/borrow',
    [MemberController::class,'borrow'])
    ->name('members.borrow');


// Return book
Route::post('/books/{book}/return',
    [BookController::class,'returnBook'])
    ->name('books.return');



Route::post('/members/{member}/books/{book}/return',
    [MemberController::class,'returnBook'])
    ->name('members.return');

    Route::get('/dashboard',
[DashboardController::class,'index'])
->name('dashboard');

