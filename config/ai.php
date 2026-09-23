<?php

return [

    'ollama_url' => env(
        'OLLAMA_URL',
        'http://localhost:11434'
    ),

    'ollama_model' => env(
        'OLLAMA_MODEL',
        'qwen2.5-coder:3b'
    ),

];
