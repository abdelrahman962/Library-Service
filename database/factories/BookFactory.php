<?php

namespace Database\Factories;

use Illuminate\Database\Eloquent\Factories\Factory;


class BookFactory extends Factory
{

    public function definition(): array
    {
        return [

            'title' => fake()->sentence(3),

            'author' => fake()->name(),

            'category' => fake()->randomElement([
                'Programming',
                'Science',
                'History',
                'Novel'
            ]),

            'publish_year' => fake()->numberBetween(2000,2026),

            'member_id' => null

        ];
    }

}
