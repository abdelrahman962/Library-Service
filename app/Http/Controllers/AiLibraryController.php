<?php

namespace App\Http\Controllers;

use App\Models\Book;
use App\Models\BorrowHistory;
use App\Models\Member;
use App\Services\LibraryService;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class AiLibraryController extends Controller
{
    protected LibraryService $library;

    public function __construct(LibraryService $library)
    {
        $this->library = $library;
    }

    /**
     * Get the currently authenticated member.
     *
     * GET /api/ai/me
     */
    public function me(Request $request)
    {
        $member = $request->user();

        return response()->json([
            'success' => true,
            'data' => [
                'id' => $member->id,
                'name' => $member->name,
                'email' => $member->email,
                'is_admin' => $member->is_admin,
            ],
        ]);
    }

    /**
     * Search books by title, author, or category.
     *
     * GET /api/ai/books/search?search=...
     */
    public function searchBooks(Request $request)
    {
        $search = $request->query('search');

        if (!$search) {
            return response()->json([
                'success' => false,
                'message' => 'Search query is required.',
            ], 422);
        }

        $books = Book::query()
            ->where('title', 'like', "%{$search}%")
            ->orWhere('author', 'like', "%{$search}%")
            ->orWhere('category', 'like', "%{$search}%")
            ->get();

        return response()->json([
            'success' => true,
            'data' => $books->map(function ($book) {
                return $book->getInfo();
            }),
        ]);
    }

    /**
     * Get all available books.
     *
     * GET /api/ai/books/available
     */
    public function availableBooks()
    {
        $books = Book::query()
            ->whereNull('member_id')
            ->get();

        return response()->json([
            'success' => true,
            'data' => $books->map(function ($book) {
                return $book->getInfo();
            }),
        ]);
    }

    /**
     * Get all currently borrowed books, with who borrowed each one.
     *
     * Filtered server-side (whereNotNull('member_id')) rather than
     * making a caller fetch allBooks() and filter out the available
     * ones itself — that would mean re-deriving, per book, exactly
     * the availability the API already knows, purely from prose
     * reasoning over a list, which is a real source of error rather
     * than a saved step.
     *
     * GET /api/ai/books/borrowed
     */
    public function borrowedBooks()
    {
        $books = Book::with('member')
            ->whereNotNull('member_id')
            ->get();

        return response()->json([
            'success' => true,
            'data' => $books->map(function ($book) {
                return [
                    'id' => $book->id,
                    'title' => $book->title,
                    'author' => $book->author,
                    'category' => $book->category,
                    'publish_year' => $book->publish_year,
                    'borrowed_by' => $book->member ? [
                        'id' => $book->member->id,
                        'name' => $book->member->name,
                        'email' => $book->member->email,
                    ] : null,
                ];
            }),
        ]);
    }

    /**
     * Get all books.
     *
     * GET /api/ai/books
     */
    public function allBooks()
    {
        $books = Book::with('member')->get();

        return response()->json([
            'success' => true,
            'data' => $books->map(function ($book) {
                return [
                    'id' => $book->id,
                    'title' => $book->title,
                    'author' => $book->author,
                    'category' => $book->category,
                    'publish_year' => $book->publish_year,
                    'available' => $book->isAvailable(),
                    'borrowed_by' => $book->member ? [
                        'id' => $book->member->id,
                        'name' => $book->member->name,
                        'email' => $book->member->email,
                    ] : null,
                ];
            }),
        ]);
    }

    /**
     * Get details about one book.
     *
     * GET /api/ai/books/{id}
     */
    public function bookDetails(int $id)
    {
        $book = Book::with('member')->find($id);

        if (!$book) {
            return response()->json([
                'success' => false,
                'message' => 'Book not found.',
            ], 404);
        }

        return response()->json([
            'success' => true,
            'data' => [
                'id' => $book->id,
                'title' => $book->title,
                'author' => $book->author,
                'category' => $book->category,
                'publish_year' => $book->publish_year,
                'available' => $book->isAvailable(),
                'borrowed_by' => $book->member ? [
                    'id' => $book->member->id,
                    'name' => $book->member->name,
                    'email' => $book->member->email,
                ] : null,
            ],
        ]);
    }

    /**
     * Get books currently borrowed by authenticated member.
     *
     * GET /api/ai/member/books
     */
    public function myBorrowedBooks(Request $request)
    {
        $member = $request->user();

        $books = $member->books()->get();

        return response()->json([
            'success' => true,
            'data' => $books->map(function ($book) {
                return $book->getInfo();
            }),
        ]);
    }

    /**
     * Get borrow history for authenticated member.
     *
     * GET /api/ai/member/history
     */
    public function myBorrowHistory(Request $request)
    {
        $member = $request->user();

        $history = BorrowHistory::where('member_id', $member->id)
            ->with('book')
            ->latest('borrowed_at')
            ->get();

        return response()->json([
            'success' => true,
            'data' => $history,
        ]);
    }

    /**
     * Borrow a book for the authenticated member.
     *
     * POST /api/ai/books/{id}/borrow
     */
    public function borrow(Request $request, int $id)
    {
        $member = $request->user();

        $book = Book::find($id);

        if (!$book) {
            return response()->json([
                'success' => false,
                'message' => 'Book not found.',
            ], 404);
        }

        $result = $this->library->borrowBookForMember(
            $member,
            $book
        );

        if (!$result['ok']) {
            return response()->json([
                'success' => false,
                'message' => $result['message'],
            ], 400);
        }

        return response()->json([
            'success' => true,
            'message' => $result['message'],
            'data' => $book->fresh(),
        ]);
    }

    /**
     * Return a book for the authenticated member.
     *
     * POST /api/ai/books/{id}/return
     */
    public function returnBook(Request $request, int $id)
    {
        $member = $request->user();

        $book = Book::find($id);

        if (!$book) {
            return response()->json([
                'success' => false,
                'message' => 'Book not found.',
            ], 404);
        }

        $result = $this->library->returnBook(
            $book,
            $member
        );

        if (!$result['ok']) {
            return response()->json([
                'success' => false,
                'message' => $result['message'],
            ], 400);
        }

        return response()->json([
            'success' => true,
            'message' => $result['message'],
            'data' => $book->fresh(),
        ]);
    }

    /**
     * Get basic library statistics.
     *
     * GET /api/ai/stats
     */
    public function stats()
    {
        $totalBooks = Book::count();

        $availableBooks = Book::whereNull('member_id')->count();

        $borrowedBooks = Book::whereNotNull('member_id')->count();

        $totalMembers = Member::count();

        $totalBorrowHistory = BorrowHistory::count();

        return response()->json([
            'success' => true,
            'data' => [
                'total_books' => $totalBooks,
                'available_books' => $availableBooks,
                'borrowed_books' => $borrowedBooks,
                'total_members' => $totalMembers,
                'total_borrow_history' => $totalBorrowHistory,
            ],
        ]);
    }
}
