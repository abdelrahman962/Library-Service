<?php

namespace App\Http\Controllers;

use App\Models\Member;
use App\Models\Book;
use Illuminate\Http\Request;
use App\Services\LibraryService;
use App\Http\Requests\StoreMemberRequest;
use App\Http\Requests\UpdateMemberRequest;
use Exception;
use Illuminate\Support\Facades\Log;

class MemberController extends Controller
{
    protected LibraryService $library;

    public function __construct(LibraryService $library)
    {
        $this->library = $library;
    }


    // GET /api/members
    // Admin: Get all members
    public function index(Request $request)
    {
        try {

            $query = Member::with('books');

            if ($request->filled('search')) {

                $search = $request->search;

                $query->where(function ($q) use ($search) {

                    $q->where('name', 'like', '%' . $search . '%')
                        ->orWhere('email', 'like', '%' . $search . '%');

                });
            }

            $members = $query->paginate(5);

            return response()->json([
                'success' => true,
                'data' => $members
            ]);

        } catch (Exception $e) {

            Log::error('Getting members failed', [
                'message' => $e->getMessage(),
                'line' => $e->getLine()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Unable to get members'
            ], 500);
        }
    }


    // POST /api/members
    // Admin: Create a member
    public function store(StoreMemberRequest $request)
    {
        try {

            $member = $this->library->addMember(
                $request->validated()
            );

            return response()->json([
                'success' => true,
                'message' => 'Member created successfully',
                'data' => $member
            ], 201);

        } catch (Exception $e) {

            Log::error('Member creation failed', [
                'message' => $e->getMessage(),
                'line' => $e->getLine()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Unable to create member'
            ], 500);
        }
    }


    // GET /api/members/{id}
    // Admin: Get one member
    public function show(int $id)
    {
        try {

            $member = Member::with('books')->findOrFail($id);

            return response()->json([
                'success' => true,
                'data' => $member
            ]);

        } catch (Exception $e) {

            Log::error('Getting member failed', [
                'member_id' => $id,
                'message' => $e->getMessage()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Member not found'
            ], 404);
        }
    }


    // PUT /api/members/{id}
    // Admin: Update member
    public function update(UpdateMemberRequest $request, int $id)
    {
        try {

            $member = Member::findOrFail($id);

            $member->update(
                $request->validated()
            );

            return response()->json([
                'success' => true,
                'message' => 'Member updated successfully',
                'data' => $member
            ]);

        } catch (Exception $e) {

            Log::error('Member update failed', [
                'member_id' => $id,
                'message' => $e->getMessage()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Member not found'
            ], 404);
        }
    }


    // DELETE /api/members/{id}
    // Admin: Delete member
    public function destroy(int $id)
    {
        try {

            $member = Member::findOrFail($id);

            $member->delete();

            return response()->json([
                'success' => true,
                'message' => 'Member deleted successfully'
            ]);

        } catch (Exception $e) {

            Log::error('Member deletion failed', [
                'member_id' => $id,
                'message' => $e->getMessage()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Member not found'
            ], 404);
        }
    }


    // GET /api/member/books
    // Member: Show books currently borrowed by logged-in member
    public function borrowBooks(Request $request)
    {
        try {

            $member = $request->user();

            $books = $member->books()->paginate(5);

            return response()->json([
                'success' => true,
                'data' => $books
            ]);

        } catch (Exception $e) {

            Log::error('Loading member books failed', [
                'member_id' => optional($request->user())->id,
                'message' => $e->getMessage(),
                'line' => $e->getLine()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Unable to load member books'
            ], 500);
        }
    }


    // POST /api/books/{bookId}/borrow
    // Member: Borrow a book
    public function borrow(Request $request, int $bookId)
    {
        try {

            // Get currently authenticated member
            $member = $request->user();

            // Find requested book
            $book = Book::findOrFail($bookId);

            // Let service handle borrowing business logic
            $result = $this->library->borrowBookForMember(
                $member,
                $book
            );

            if (!$result['ok']) {

                return response()->json([
                    'success' => false,
                    'message' => $result['message']
                ], 400);
            }

            return response()->json([
                'success' => true,
                'message' => $result['message'],
                'data' => $book->fresh()
            ], 200);

        } catch (Exception $e) {

            Log::error('Borrow book failed', [
                'member_id' => optional($request->user())->id,
                'book_id' => $bookId,
                'message' => $e->getMessage(),
                'line' => $e->getLine()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Unable to borrow book'
            ], 500);
        }
    }


    // POST /api/books/{bookId}/return
    // Member: Return a book
    public function returnBook(Request $request, int $bookId)
    {
        try {

            // Get currently authenticated member
            $member = $request->user();

            // Find requested book
            $book = Book::findOrFail($bookId);

            // Let service handle return business logic
            $result = $this->library->returnBook(
                $book,
                $member
            );

            if (!$result['ok']) {

                return response()->json([
                    'success' => false,
                    'message' => $result['message']
                ], 400);
            }

            return response()->json([
                'success' => true,
                'message' => $result['message'],
                'data' => $book->fresh()
            ], 200);

        } catch (Exception $e) {

            Log::error('Return book failed', [
                'member_id' => optional($request->user())->id,
                'book_id' => $bookId,
                'message' => $e->getMessage(),
                'line' => $e->getLine()
            ]);

            return response()->json([
                'success' => false,
                'message' => 'Unable to return book'
            ], 500);
        }
    }

    public function restore(int $id)
{
    try {

        $result = $this->library->restoreMember($id);

        if (!$result['ok']) {

            return response()->json([
                'success' => false,
                'message' => $result['message']
            ], 400);
        }

        return response()->json([
            'success' => true,
            'message' => $result['message'],
            'data' => $result['member']
        ], 200);

    } catch (Exception $e) {

        Log::error('Member restoration failed', [
            'member_id' => $id,
            'message' => $e->getMessage(),
            'line' => $e->getLine()
        ]);

        return response()->json([
            'success' => false,
            'message' => 'Member not found'
        ], 404);
    }
}
}
