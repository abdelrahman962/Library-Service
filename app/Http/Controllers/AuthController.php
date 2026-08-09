<?php

namespace App\Http\Controllers;

use App\Models\User;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Hash;


class AuthController extends Controller
{


    public function register(Request $request)
    {


        $request->validate([

            'name'=>'required|string|max:255',

            'email'=>'required|email|unique:users',

            'password'=>'required|min:8'

        ]);



        $user = User::create([

            'name'=>$request->name,

            'email'=>$request->email,

            'password'=>Hash::make($request->password)

        ]);




        $token = $user
            ->createToken('api-token')
            ->plainTextToken;



        return response()->json([

            'success'=>true,

            'message'=>'User registered successfully',

            'user'=>$user,

            'token'=>$token

        ],201);


    }






    public function login(Request $request)
    {


        $request->validate([

            'email'=>'required|email',

            'password'=>'required'

        ]);



        $user = User::where(
            'email',
            $request->email
        )->first();



        if(
            !$user ||
            !Hash::check(
                $request->password,
                $user->password
            )
        ){

            return response()->json([

                'success'=>false,

                'message'=>'Invalid credentials'

            ],401);

        }





        $token=$user
            ->createToken('api-token')
            ->plainTextToken;




        return response()->json([

            'success'=>true,

            'message'=>'Login successful',

            'user'=>$user,

            'token'=>$token

        ]);

    }







    public function logout(Request $request)
    {


        $request->user()
            ->currentAccessToken()
            ->delete();



        return response()->json([

            'success'=>true,

            'message'=>'Logged out successfully'

        ]);

    }


}
