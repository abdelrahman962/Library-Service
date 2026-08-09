<?php

namespace App\Models;
use App\Models\BorrowHistory;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\SoftDeletes;
use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;

class Book extends Model
{
    //
    use SoftDeletes,LogsActivity;
use HasFactory;
    protected $fillable=[

'title',
'author',
'category',
'publish_year',
'member_id'

];


public function borrowHistories()
{
    return $this->hasMany(BorrowHistory::class);
}

    public function getActivitylogOptions(): LogOptions
    {
        return LogOptions::defaults()
            ->logAll()
            ->logOnlyDirty()
            ->dontSubmitEmptyLogs();
    }
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
