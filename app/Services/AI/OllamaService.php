<?php
namespace App\Services\AI;
use Illuminate\Support\Facades\Http;
class OllamaService
{
    public function chat(array $messages): array
    {
        $response = Http::post(
            config('ai.ollama_url').'/api/chat',
            [
                'model'=>config('ai.ollama_model'),
                'messages'=> $messages,
                'stream' =>false,
            ]
        );

        $response->throw();
        return $response->json();
    }
}
