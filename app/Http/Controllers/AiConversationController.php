<?php

namespace App\Http\Controllers;
use App\Models\AiConversation;
use Illuminate\Http\Request;

class AiConversationController extends Controller
{
    //
  public function index(Request $request)
    {
        $conversations = AiConversation::where(
            'member_id',
            $request->user()->id
        )
        ->latest()
        ->get();

        return response()->json([
            'success' => true,
            'conversations' => $conversations,
        ]);
    }

    public function store(Request $request)
    {
        $conversation = AiConversation::create([
            'member_id' => $request->user()->id,
            'title' => $request->input('title'),
        ]);

        return response()->json([
            'success' => true,
            'conversation' => $conversation,
        ], 201);
    }

    public function show(Request $request, $id)
    {
        $conversation = AiConversation::where(
            'member_id',
            $request->user()->id
        )
        ->with('messages')
        ->findOrFail($id);

        return response()->json([
            'success' => true,
            'conversation' => $conversation,
        ]);
    }

    public function destroy(Request $request, $id)
    {
        $conversation = AiConversation::where(
            'member_id',
            $request->user()->id
        )
        ->findOrFail($id);

        $conversation->delete();

        return response()->json([
            'success' => true,
            'message' => 'Conversation deleted successfully.',
        ]);
    }
public function addMessage(
    Request $request,
    AiConversation $conversation
) {
    if ($conversation->member_id !== $request->user()->id) {
        abort(403);
    }

    $validated = $request->validate([
        'role' => [
            'required',
            'in:user,assistant',
        ],

        'content' => [
            'required',
            'string',
        ],
    ]);

    $message = $conversation->messages()->create([
        'role' => $validated['role'],
        'content' => $validated['content'],
    ]);

    return response()->json([
        'success' => true,
        'message' => $message,
    ], 201);
}

}
