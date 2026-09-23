
<?php

use Illuminate\Support\Facades\Route;

use App\Http\Controllers\MemberAuthController;
use App\Http\Controllers\BookController;
use App\Http\Controllers\MemberController;
use App\Http\Controllers\DashboardController;
use App\Http\Controllers\BorrowHistoryController;
use App\Http\Controllers\AiLibraryController;
use App\Http\Controllers\AiConversationController;
/*
|--------------------------------------------------------------------------
| Library API Routes
|--------------------------------------------------------------------------
|
| Single authenticatable model: Member.
|
| Public:
|   - View books
|   - Search books
|   - View available books
|   - View book details
|
| Authenticated members:
|   - Borrow books
|   - Return books
|   - View their borrowed books
|   - View their borrowing history
|
| Admins:
|   - Create/update/delete books
|   - Manage members
|   - Restore books/members
|   - View dashboard
|   - View book history
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
| PUBLIC BOOK ROUTES
|--------------------------------------------------------------------------
|
| Anyone can view the library catalog.
| No authentication required.
|
*/

Route::get(
    '/books',
    [BookController::class, 'index']
);

Route::get(
    '/books/{id}',
    [BookController::class, 'show']
);


/*
|--------------------------------------------------------------------------
| MEMBER PROTECTED ROUTES
|--------------------------------------------------------------------------
|
| A valid Sanctum token is required.
| Any authenticated member can access these routes.
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
| AI AGENT ROUTES
|--------------------------------------------------------------------------
|
| These routes are used by the Python LangChain AI agent.
|
| Public AI operations:
|   - View all books
|   - Search books
|   - View available books
|   - View book details
|
| Authenticated AI operations:
|   - Get current member
|   - View borrowed books
|   - View borrow history
|   - Borrow
|   - Return
|
*/


/*
|--------------------------------------------------------------------------
| PUBLIC AI BOOK ROUTES
|--------------------------------------------------------------------------
|
| No authentication required.
|
*/

Route::prefix('ai')->group(function () {

/*

AI Conversation History

*/


Route::middleware('auth:sanctum')->group(function () {

    Route::post('/conversations', [
        AiConversationController::class,
        'store'
    ]);

    Route::get('/conversations', [
        AiConversationController::class,
        'index'
    ]);

    Route::get('/conversations/{id}', [
        AiConversationController::class,
        'show'
    ]);

    Route::delete('/conversations/{id}', [
        AiConversationController::class,
        'destroy'
    ]);

    Route::post(
        '/conversations/{conversation}/messages',
        [AiConversationController::class, 'addMessage']
    );
});




/*
    |--------------------------------------------------------------------------
    | Books
    |--------------------------------------------------------------------------
    */



    Route::get(
        '/books',
        [AiLibraryController::class, 'allBooks']
    );

    Route::get(
        '/books/search',
        [AiLibraryController::class, 'searchBooks']
    );

    Route::get(
        '/books/available',
        [AiLibraryController::class, 'availableBooks']
    );

    Route::get(
        '/books/borrowed',
        [AiLibraryController::class, 'borrowedBooks']
    );

    Route::get(
        '/books/{id}',
        [AiLibraryController::class, 'bookDetails']
    );


    /*
    |--------------------------------------------------------------------------
    | AUTHENTICATED AI ROUTES
    |--------------------------------------------------------------------------
    |
    | These operations require the current member's Sanctum token.
    |
    */

    Route::middleware('auth:sanctum')->group(function () {

        /*
        |----------------------------------------------------------------------
        | Current Member
        |----------------------------------------------------------------------
        */

        Route::get(
            '/me',
            [AiLibraryController::class, 'me']
        );


        /*
        |----------------------------------------------------------------------
        | Member
        |----------------------------------------------------------------------
        */

        Route::get(
            '/member/books',
            [AiLibraryController::class, 'myBorrowedBooks']
        );

        Route::get(
            '/member/history',
            [AiLibraryController::class, 'myBorrowHistory']
        );


        /*
        |----------------------------------------------------------------------
        | Borrowing
        |----------------------------------------------------------------------
        */

        Route::post(
            '/books/{id}/borrow',
            [AiLibraryController::class, 'borrow']
        );

        Route::post(
            '/books/{id}/return',
            [AiLibraryController::class, 'returnBook']
        );
    });


    /*
    |--------------------------------------------------------------------------
    | Statistics
    |--------------------------------------------------------------------------
    |
    | Currently public.
    | If statistics should only be available to authenticated users,
    | move this route into the auth:sanctum group above.
    |
    */

    Route::get(
        '/stats',
        [AiLibraryController::class, 'stats']
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
| The admin middleware checks:
|
|     $request->user()->is_admin
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
    |
    | GET /books and GET /books/{id} are intentionally NOT here.
    | They are public.
    |
    | Only modifying book operations require admin privileges.
    |
    */

    Route::post(
        '/books',
        [BookController::class, 'store']
    );

    Route::put(
        '/books/{id}',
        [BookController::class, 'update']
    );

    Route::patch(
        '/books/{id}',
        [BookController::class, 'update']
    );

    Route::delete(
        '/books/{id}',
        [BookController::class, 'destroy']
    );

    Route::patch(
        '/books/{id}/restore',
        [BookController::class, 'restore']
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

    Route::patch(
        '/members/{id}/restore',
        [MemberController::class, 'restore']
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

    Route::get(
        '/members/{id}/history',
        [BorrowHistoryController::class, 'memberHistoryById']
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
