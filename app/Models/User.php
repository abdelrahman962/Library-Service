<?php

namespace App\Models;

use Database\Factories\UserFactory;
use Illuminate\Foundation\Auth\User as Authenticatable;
use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Notifications\Notifiable;
use Laravel\Sanctum\HasApiTokens;

use Spatie\Activitylog\Traits\CausesActivity;
use Spatie\Activitylog\Traits\LogsActivity;
use Spatie\Activitylog\LogOptions;


class User extends Authenticatable
{

    use HasFactory,
        Notifiable,
        HasApiTokens,
        CausesActivity,
        LogsActivity;


    protected $fillable = [
        'name',
        'email',
        'password',
    ];


    protected $hidden = [
        'password',
        'remember_token',
    ];



    protected function casts(): array
    {
        return [
            'email_verified_at'=>'datetime',
            'password'=>'hashed',
        ];
    }



    public function getActivitylogOptions(): LogOptions
    {
        return LogOptions::defaults()

            ->logOnly([
                'name',
                'email'
            ])

            ->logOnlyDirty()

            ->dontSubmitEmptyLogs();
    }


}
