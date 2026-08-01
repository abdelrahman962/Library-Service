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



}
