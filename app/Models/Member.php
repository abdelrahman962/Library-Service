<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;

class Member extends Model
{
    use HasFactory;
    //
    protected $fillable = ['name','email'];
public function books(){
    return $this->hasMany(Book::class);
}
public function getBorrowedBooks()
{
    return $this->books;
}
    }
