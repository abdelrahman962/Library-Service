<?php

namespace App\Http\Controllers;

use App\Models\Member;
use App\Http\Requests\MemberRegisterRequest;
use App\Http\Requests\MemberLoginRequest;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;

class MemberAuthController extends Controller
{
    public function register(MemberRegisterRequest $request)
    {
        $validated = $request->validated();

        $member = Member::create([
            'name' => $validated['name'],

            'email' => $validated['email'],

            'password' => $validated['password'],
        ]);

        $token = $member
            ->createToken('member-token')
            ->plainTextToken;

        return response()->json([
            'success' => true,

            'message' => 'Member registered successfully',

            'member' => $member,

            'token' => $token,
        ], 201);
    }


    public function login(MemberLoginRequest $request)
    {
        $validated = $request->validated();

        $member = Member::where(
            'email',
            $validated['email']
        )->first();

        if (
            !$member ||
            !Hash::check(
                $validated['password'],
                $member->password
            )
        ) {
            return response()->json([
                'success' => false,

                'message' => 'Invalid credentials',
            ], 401);
        }

        $token = $member
            ->createToken('member-token')
            ->plainTextToken;

        return response()->json([
            'success' => true,

            'message' => 'Login successful',

            'member' => $member,

            'token' => $token,
        ]);
    }


    public function logout(Request $request)
    {
        $request
            ->user()
            ->currentAccessToken()
            ->delete();

        return response()->json([
            'success' => true,

            'message' => 'Logged out successfully',
        ]);
    }
}
