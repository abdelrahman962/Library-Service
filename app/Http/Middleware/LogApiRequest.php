<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;
use Illuminate\Support\Facades\Log;

class LogApiRequest
{
    /**
     * Handle an incoming request.
     *
     * @param  Closure(Request): (Response)  $next
     */
    public function handle(Request $request, Closure $next): Response
    {
Log::info('Api Request',
['method'=>$request->method(),
'url'=>$request->fullUrl(),
'ip'=>$request->ip(),
'time'=>now()

]);


        return $next($request);
    }
}
