<?php

namespace App\AiAgents;

use LarAgent\Agent;
use LarAgent\Attributes\Tool;
use App\Models\Book;
use App\Models\Member;
use App\Models\BorrowHistory;
use App\Services\LibraryService;

class LibraryAssistant extends Agent
{
    protected $history = 'file';
    protected $provider = 'ollama';
    protected $tools = [];

    public function instructions()
    {
        $totalBooks     = Book::count();
        $availableBooks = Book::whereNull('member_id')->count();
        $borrowedBooks  = Book::whereNotNull('member_id')->count();

        return "You are a helpful library assistant. You help members search for books,
check availability, borrow books, and return them.

Library statistics:
- Total books: {$totalBooks}
- Available books: {$availableBooks}
- Currently borrowed: {$borrowedBooks}

Rules:
- Before borrowing or returning a book, always confirm the member's email address.
- Always search for a book first before trying to borrow it.
- Keep responses short and clear.
- Do not invent book titles, authors, or availability — always use the tools.
- Do not pretend to be a human. Only use information returned by your tools.
- For greetings, small talk, or general questions that don't involve books or members,
  respond directly without calling any tool.
- When a tool returns book information, always present that information to the member.
- Never replace a successful tool result with a generic question or follow-up.
- If listAvailableBooks returns books, display the returned list exactly or summarize it clearly.
- If listAllBooks returns books, display the returned list exactly or summarize it clearly.";
    }

    public function prompt($message)
    {
        return "Today is " . now()->format('Y-m-d') . ". Member says: {$message}";
    }



// ─── TOOL 1: Search books ──────────────────────────────────────────────────

    #[Tool("Search for books by title or category. ONLY call this when the member explicitly
mentions a book title, author name, or reading topic. NEVER call this for greetings
or general conversation.")]
    public static function searchBooks(string $query): string
    {
        $service = new LibraryService();

        $byTitle    = $service->searchBookByTitle($query);
        $byCategory = $service->searchBookByCategory($query);

        $books = $byTitle->merge($byCategory)->unique('id')->values();

        if ($books->isEmpty()) {
            return "No books found matching '{$query}'.";
        }

        $list = $books->map(function ($b) {
            $info   = $b->getInfo();
            $status = $info['available'] ? 'Available' : 'Borrowed';
            return "- [{$info['id']}] {$info['title']} by {$info['author']} ({$info['category']}, {$info['publish_year']}) — {$status}";
        })->implode("\n");

        return "Books matching '{$query}':\n{$list}";
    }

    // ─── TOOL 2: List available books ─────────────────────────────────────────

    #[Tool("List all currently available books that can be borrowed right now.")]
    public static function listAvailableBooks(): string
    {
        $books = Book::whereNull('member_id')->get();

        if ($books->isEmpty()) {
            return "No books are currently available. All books are borrowed.";
        }

        $list = $books->map(function ($b) {
            $info = $b->getInfo();
            return "- [{$info['id']}] {$info['title']} by {$info['author']} ({$info['category']}, {$info['publish_year']})";
        })->implode("\n");

        return "Available books:\n{$list}";
    }

    // ─── TOOL 3: Check a specific book ────────────────────────────────────────

    #[Tool("Check whether a specific book is available or borrowed. Requires the book ID.")]
    public static function checkBook(int $bookId): string
    {
        $book = Book::find($bookId);

        if (!$book) {
            return "Book with ID {$bookId} not found.";
        }

        $info = $book->getInfo();

        if ($book->isAvailable()) {
            return "'{$info['title']}' by {$info['author']} is available and can be borrowed.";
        }

        $member = Member::find($book->member_id);
        $name   = $member ? $member->name : 'another member';

        return "'{$info['title']}' is currently borrowed by {$name} and is not available.";
    }

    // ─── TOOL 4: Borrow a book ────────────────────────────────────────────────

    #[Tool("Borrow a book for a member. Requires the book ID and the member's email address. Always confirm the email before calling this.")]
    public static function borrowBook(int $bookId, string $memberEmail): string
    {
        if (trim($memberEmail) === '') {
            return "I need the member's email address before borrowing. Please ask them for it.";
        }

        $member = Member::where('email', $memberEmail)->first();

        if (!$member) {
            return "No member found with email '{$memberEmail}'. Please check the email and try again.";
        }

        $book = Book::find($bookId);

        if (!$book) {
            return "Book with ID {$bookId} not found.";
        }

        $service = new LibraryService();
        $result  = $service->borrowBookForMember($member, $book);

        if (!$result['ok']) {
            return $result['message'];
        }

        return "'{$book->title}' has been borrowed successfully by {$member->name}.";
    }

    // ─── TOOL 5: Return a book ────────────────────────────────────────────────

    #[Tool("Return a borrowed book. Requires the book ID and the member's email address.")]
    public static function returnBook(int $bookId, string $memberEmail): string
    {
        if (trim($memberEmail) === '') {
            return "I need the member's email address before returning. Please ask them for it.";
        }

        $member = Member::where('email', $memberEmail)->first();

        if (!$member) {
            return "No member found with email '{$memberEmail}'.";
        }

        $book = Book::find($bookId);

        if (!$book) {
            return "Book with ID {$bookId} not found.";
        }

        $service = new LibraryService();
        $result  = $service->returnBook($book, $member);

        if (!$result['ok']) {
            return $result['message'];
        }

        return "'{$book->title}' has been returned successfully. Thank you, {$member->name}!";
    }

    // ─── TOOL 6: Currently borrowed books ─────────────────────────────────────

    #[Tool("Show the books a member currently has borrowed and not yet returned. Requires their email address.")]
    public static function myBorrowedBooks(string $memberEmail): string
    {
        $member = Member::where('email', $memberEmail)->with('books')->first();

        if (!$member) {
            return "No member found with email '{$memberEmail}'.";
        }

        $books = $member->books;

        if ($books->isEmpty()) {
            return "{$member->name} currently has no borrowed books.";
        }

        $list = $books->map(function ($b) {
            $info = $b->getInfo();
            return "- [{$info['id']}] {$info['title']} by {$info['author']}";
        })->implode("\n");

        return "{$member->name}'s currently borrowed books:\n{$list}";
    }

    // ─── TOOL 7: Full borrow history ──────────────────────────────────────────

    #[Tool("Show a member's full borrow history including books already returned. Requires their email address.")]
    public static function myBorrowHistory(string $memberEmail): string
    {
        $member = Member::where('email', $memberEmail)->first();

        if (!$member) {
            return "No member found with email '{$memberEmail}'.";
        }

        $history = BorrowHistory::where('member_id', $member->id)
            ->with('book')
            ->latest('borrowed_at')
            ->get();

        if ($history->isEmpty()) {
            return "{$member->name} has no borrow history yet.";
        }

        $list = $history->map(function ($h) {
            $returned = $h->returned_at
                ? "returned on {$h->returned_at}"
                : "not yet returned";
            return "- {$h->book->title} by {$h->book->author} (borrowed {$h->borrowed_at}, {$returned})";
        })->implode("\n");

        return "{$member->name}'s borrow history:\n{$list}";
    }

    // ─── TOOL 8: List ALL books ───────────────────────────────────────────────────

#[Tool("List all books in the library with full details including availability status. Use this when the member asks to see all books or browse the collection.")]
public static function listAllBooks(): string
{
    $books = Book::all();

    if ($books->isEmpty()) {
        return "No books found in the library.";
    }

    $list = $books->map(function ($b) {
        $status = $b->isAvailable() ? 'Available' : 'Borrowed';
        $borrowedBy = '';
        if (!$b->isAvailable()) {
            $member = Member::find($b->member_id);
            $borrowedBy = $member ? " (borrowed by {$member->name})" : '';
        }
        return "- [{$b->id}] \"{$b->title}\" by {$b->author} | Category: {$b->category} | Year: {$b->publish_year} | Status: {$status}{$borrowedBy}";
    })->implode("\n");

    $total     = $books->count();
    $available = $books->filter(fn($b) => $b->isAvailable())->count();
    $borrowed  = $total - $available;

    return "All books in the library ({$total} total, {$available} available, {$borrowed} borrowed):\n\n{$list}";
}

// ─── TOOL 9: Get full details of one book ────────────────────────────────────

#[Tool("Get full details of a single book by its ID, including borrow history count and current status.")]
public static function getBookDetails(int $bookId): string
{
    $book = Book::with('borrowHistories')->find($bookId);

    if (!$book) {
        return "Book with ID {$bookId} not found.";
    }

    $status = $book->isAvailable() ? 'Available' : 'Borrowed';
    $borrowedBy = '';
    if (!$book->isAvailable()) {
        $member = Member::find($book->member_id);
        $borrowedBy = "\n- Currently borrowed by: " . ($member ? $member->name . " ({$member->email})" : 'Unknown');
    }

    $timesBooked = $book->borrowHistories->count();

    return "Book details:
- ID: {$book->id}
- Title: {$book->title}
- Author: {$book->author}
- Category: {$book->category}
- Published: {$book->publish_year}
- Status: {$status}{$borrowedBy}
- Times borrowed historically: {$timesBooked}
- Added to library: {$book->created_at}";
}

// ─── TOOL 10: Search members ──────────────────────────────────────────────────

#[Tool("Search for a member by name or email. Useful to look up a member before borrowing or returning a book.")]
public static function searchMember(string $query): string
{
    $members = Member::where('name', 'like', "%{$query}%")
        ->orWhere('email', 'like', "%{$query}%")
        ->get();

    if ($members->isEmpty()) {
        return "No member found matching '{$query}'.";
    }

    $list = $members->map(function ($m) {
        $borrowedCount = $m->books()->count();
        return "- [{$m->id}] {$m->name} ({$m->email}) — currently borrowing {$borrowedCount} book(s)";
    })->implode("\n");

    return "Members matching '{$query}':\n{$list}";
}

// ─── TOOL 11: Library statistics ──────────────────────────────────────────────

#[Tool("Show overall library statistics: total books, available, borrowed, and total members.")]
public static function libraryStats(): string
{
    $totalBooks     = Book::count();
    $availableBooks = Book::whereNull('member_id')->count();
    $borrowedBooks  = Book::whereNotNull('member_id')->count();
    $totalMembers   = Member::count();
    // $totalBorrows   = BorrowHistory::count();

    return "Library statistics:
- Total books: {$totalBooks}
- Available books: {$availableBooks}
- Currently borrowed: {$borrowedBooks}
- Total members: {$totalMembers}
";
// - Total borrows ever recorded: {$totalBorrows}
}



}

