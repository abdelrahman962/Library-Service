<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Member;

class MemberSeeder extends Seeder
{
    public function run(): void
    {

        Member::create([
            'name' => 'Ahmed Ali',
            'email' => 'ahmed@example.com',
        ]);

        Member::create([
            'name' => 'Omar Hassan',
            'email' => 'omar@example.com',
        ]);

        Member::create([
            'name' => 'Sara Khaled',
            'email' => 'sara@example.com',
        ]);

        Member::create([
            'name' => 'Lina Ahmad',
            'email' => 'lina@example.com',
        ]);

        Member::create([
    'name' => 'Yousef Mahmoud',
    'email' => 'yousef@example.com',
]);

Member::create([
    'name' => 'Mariam Saleh',
    'email' => 'mariam@example.com',
]);

Member::create([
    'name' => 'Khaled Nasser',
    'email' => 'khaled@example.com',
]);

Member::create([
    'name' => 'Rana Ibrahim',
    'email' => 'rana@example.com',
]);

Member::create([
    'name' => 'Ali Samir',
    'email' => 'ali@example.com',
]);

Member::create([
    'name' => 'Noor Adel',
    'email' => 'noor@example.com',
]);

Member::create([
    'name' => 'Hassan Tarek',
    'email' => 'hassan@example.com',
]);

Member::create([
    'name' => 'Aya Fadi',
    'email' => 'aya@example.com',
]);

Member::create([
    'name' => 'Mahmoud Rami',
    'email' => 'mahmoud@example.com',
]);

Member::create([
    'name' => 'Dina Wael',
    'email' => 'dina@example.com',
]);

    }



}
