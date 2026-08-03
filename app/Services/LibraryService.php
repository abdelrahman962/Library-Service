<?php

namespace App\Services;


use App\Models\Book;
use App\Models\Member;


class LibraryService
{

public function addBook($data)
{
    return Book::create($data);
}



public function removeBook(Book $book)
{
    return $book->delete();
}



public function addMember($data)
{
    return Member::create($data);
}




public function searchBookByTitle($title)
{

    return Book::where(
        'title',
        'like',
        '%'.$title.'%'
    )->get();

}




public function searchBookByCategory($category)
{

    return Book::where(
        'category',
        'like',
        '%'.$category.'%'
    )->get();

}




public function displayBooks()
{
    return Book::query();
}

public function borrowBookForMember(Member $member, Book $book): array
{
    if (!$book->isAvailable()) {
        return [
            'ok' => false,
            'message' => 'This book is already borrowed.',
        ];
    }

    $book->update([
        'member_id' => $member->id,
    ]);

    return [
        'ok' => true,
        'message' => 'Book borrowed successfully.',
    ];
}

public function returnBook(Book $book, ?Member $member = null): array
{
    if ($member && $book->member_id != $member->id) {
        return [
            'ok' => false,
            'message' => 'This book is not borrowed by this member.',
        ];
    }

    if ($book->isAvailable()) {
        return [
            'ok' => false,
            'message' => 'This book is already available.',
        ];
    }

    $book->update([
        'member_id' => null,
    ]);

    return [
        'ok' => true,
        'message' => 'Book returned successfully.',
    ];
}



}
