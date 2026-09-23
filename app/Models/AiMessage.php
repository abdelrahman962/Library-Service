<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AiMessage extends Model
{
    //

    protected $fillable = [
        'conversation_id',
        'role',
        'content'
    ];

    public function conversation():BelongsTo
    {
        // Explicit FK: without it, Eloquent's default guess is
        // "ai_conversation_id" (derived from the related class name),
        // but the actual column (see the create_ai_messages_table
        // migration) is "conversation_id".
        return $this->belongsTo(AiConversation::class, 'conversation_id');
    }
}
