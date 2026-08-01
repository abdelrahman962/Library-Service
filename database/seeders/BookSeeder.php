<?php

namespace Database\Seeders;

use Illuminate\Database\Seeder;
use App\Models\Book;

class BookSeeder extends Seeder
{
    public function run(): void
    {

        Book::create([
            'title' => 'Clean Code',
            'author' => 'Robert Martin',
            'category' => 'Programming',
            'publish_year' => 2008,
            'member_id' => null,
        ]);

        Book::create([
            'title' => 'Laravel Up & Running',
            'author' => 'Matt Stauffer',
            'category' => 'Programming',
            'publish_year' => 2023,
            'member_id' => null,
        ]);

        Book::create([
            'title' => 'Design Patterns',
            'author' => 'GoF',
            'category' => 'Software Engineering',
            'publish_year' => 1994,
            'member_id' => null,
        ]);

        Book::create([
            'title' => 'The Pragmatic Programmer',
            'author' => 'Andrew Hunt',
            'category' => 'Programming',
            'publish_year' => 1999,
            'member_id' => null,
        ]);

        Book::create([
            'title' => 'Introduction to Algorithms',
            'author' => 'Thomas Cormen',
            'category' => 'Algorithms',
            'publish_year' => 2022,
            'member_id' => null,
        ]);



        Book::create([
    'title' => 'Computer Networks',
    'author' => 'Andrew S. Tanenbaum',
    'category' => 'Networking',
    'publish_year' => 2021,
    'member_id' => null,
]);

Book::create([
    'title' => 'Operating System Concepts',
    'author' => 'Abraham Silberschatz',
    'category' => 'Operating Systems',
    'publish_year' => 2018,
    'member_id' => null,
]);

Book::create([
    'title' => 'Artificial Intelligence: A Modern Approach',
    'author' => 'Stuart Russell',
    'category' => 'Artificial Intelligence',
    'publish_year' => 2021,
    'member_id' => null,
]);

Book::create([
    'title' => 'Deep Learning',
    'author' => 'Ian Goodfellow',
    'category' => 'Machine Learning',
    'publish_year' => 2016,
    'member_id' => null,
]);

Book::create([
    'title' => 'Clean Architecture',
    'author' => 'Robert C. Martin',
    'category' => 'Software Engineering',
    'publish_year' => 2017,
    'member_id' => null,
]);

Book::create([
    'title' => 'Database System Concepts',
    'author' => 'Abraham Silberschatz',
    'category' => 'Database',
    'publish_year' => 2019,
    'member_id' => null,
]);

Book::create([
    'title' => 'Refactoring',
    'author' => 'Martin Fowler',
    'category' => 'Programming',
    'publish_year' => 2018,
    'member_id' => null,
]);

Book::create([
    'title' => 'You Don’t Know JS',
    'author' => 'Kyle Simpson',
    'category' => 'JavaScript',
    'publish_year' => 2020,
    'member_id' => null,
]);

Book::create([
    'title' => 'The Mythical Man-Month',
    'author' => 'Frederick P. Brooks Jr.',
    'category' => 'Software Engineering',
    'publish_year' => 1995,
    'member_id' => null,
]);

Book::create([
    'title' => 'Code Complete',
    'author' => 'Steve McConnell',
    'category' => 'Programming',
    'publish_year' => 2004,
    'member_id' => null,
]);

    }
}
