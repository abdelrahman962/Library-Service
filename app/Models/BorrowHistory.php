<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class BorrowHistory extends Model
{
    //

      protected $fillable = [
        'book_id',
        'member_id',
        'borrowed_at',
        'returned_at',
    ];

    public function book()
    {
        return $this->belongsTo(Book::class);
    }

    public function member()
    {
        return $this->belongsTo(Member::class);
    }
}
