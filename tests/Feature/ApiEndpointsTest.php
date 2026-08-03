<?php

namespace Tests\Feature;

use App\Models\Book;
use App\Models\Member;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ApiEndpointsTest extends TestCase
{
    use RefreshDatabase;

    public function test_books_api_index_and_store_work(): void
    {
        $response = $this->getJson('/api/books');

        $response->assertOk()
            ->assertJsonStructure(['data']);

        $createResponse = $this->postJson('/api/books', [
            'title' => 'Design Principles',
            'author' => 'Robert Martin',
            'category' => 'Programming',
            'publish_year' => 2020,
        ]);

        $createResponse->assertCreated()
            ->assertJsonPath('data.title', 'Design Principles');

        $this->assertDatabaseHas('books', ['title' => 'Design Principles']);
    }

    public function test_members_and_borrowing_api_work(): void
    {
        $member = Member::factory()->create();
        $book = Book::factory()->create();

        $response = $this->postJson("/api/members/{$member->id}/books/{$book->id}/borrow");

        $response->assertOk()
            ->assertJsonPath('ok', true);

        $this->assertDatabaseHas('books', [
            'id' => $book->id,
            'member_id' => $member->id,
        ]);
    }
}
