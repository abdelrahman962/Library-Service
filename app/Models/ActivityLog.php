<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ActivityLog extends Model
{
    //
    protected $fillable = [

        'action',

        'model_type',

        'model_id',

        'description',

        'ip_address',

        'data'
    ];

      protected $casts = [

        'data'=>'array'

    ];
}
