<?php

namespace App\Models;

use Illuminate\Foundation\Auth\User as Authenticatable;
use Laravel\Sanctum\HasApiTokens;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\SoftDeletes;
use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;
use App\Models\BorrowHistory;
use Spatie\Activitylog\Traits\CausesActivity;

class Member extends Authenticatable
{
    use HasFactory,LogsActivity, CausesActivity;
    //
    use SoftDeletes, HasApiTokens;
    protected $fillable = ['name','email','password'];
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


protected function casts():array{
    return[
        'password'=>'hashed',
    ];
}
    }
