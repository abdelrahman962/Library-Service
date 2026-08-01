<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Book extends Model
{
    //
use HasFactory;
    protected $fillable=[

'title',
'author',
'category',
'publish_year',
'member_id'

];
public function member()
{
    return $this->belongsTo(Member::class);
}


public function isAvailable():bool
{
    return $this->member_id == null;
}
public function getInfo()
{
    return [
        'id' => $this->id,
        'title' => $this->title,
        'author' => $this->author,
        'category' => $this->category,
        'publish_year' => $this->publish_year,
        'available' => $this->isAvailable()
    ];
}

}
