<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\SoftDeletes;
use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;
use App\Models\BorrowHistory;
class Member extends Model
{
    use HasFactory,LogsActivity;
    //
    use SoftDeletes;
    protected $fillable = ['name','email'];
public function getActivitylogOptions(): LogOptions
    {
        return LogOptions::defaults()
            ->logAll()
            ->logOnlyDirty()
            ->dontSubmitEmptyLogs();
    }
    public function borrowHistories()
{
    return $this->hasMany(BorrowHistory::class);
}
    public function books(){
    return $this->hasMany(Book::class);
}
public function getBorrowedBooks()
{
    return $this->books;
}
    }
