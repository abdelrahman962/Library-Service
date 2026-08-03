<?php

namespace App\Services;

use App\Models\ActivityLog;

class ActivityLogService
{

    public function log(
        string $action,
        $model = null,
        string $description = null,
        array $data = []
    ) {

        ActivityLog::create([

            'action' => $action,

            'model_type' => $model ? get_class($model) : null,

            'model_id' => $model?->id,

            'description' => $description,

            'ip_address' => request()->ip(),

            'data' => $data

        ]);

    }

}
