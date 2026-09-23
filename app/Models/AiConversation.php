<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
class AiConversation extends Model
{
    protected $fillable = [
        'member_id',
        'title'
    ];

    protected $casts = [
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /**
     * Get the member who sent the message
     */
    public function member(): BelongsTo
    {
        return $this->belongsTo(Member::class);
    }

    public function messages():HasMany
    {
        // Explicit FK: without it, Eloquent's default guess is
        // "ai_conversation_id" (derived from this model's own class
        // name), but the actual column (see the create_ai_messages_table
        // migration) is "conversation_id" — this is what
        // AiConversationController@addMessage's
        // $conversation->messages()->create(...) actually hits.
        return $this->hasMany(AiMessage::class, 'conversation_id');
    }
}
