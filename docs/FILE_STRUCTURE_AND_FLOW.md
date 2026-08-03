~# Library System File Structure And Flow

This file explains how the main files in the project work together, especially the book and member features.

## 1. Main Folder Roles

- `app/Http/Controllers` handles user requests and decides what happens next.
- `app/Models` represents database tables as PHP classes.
- `app/Services` holds reusable business logic.
- `database/migrations` defines the database tables and columns.
- `database/seeders` inserts starter data into the database.
- `database/factories` generates fake data for testing or bulk seeding.
- `resources/views` contains the Blade templates shown in the browser.
- `routes/web.php` connects URLs to controller methods.

## 2. Book File Flow

### BookController

[BookController](../app/Http/Controllers/BookController.php) is the main request handler for books.

It is responsible for:

- listing books
- creating books
- editing books
- deleting books
- returning books
- showing one book in detail

The controller does not talk to the database directly for every action. In this project it uses [LibraryService](../app/Services/LibraryService.php) for shared book operations like creating, deleting, and searching.

### Book Model

[Book](../app/Models/Book.php) represents one row in the `books` table.

It defines:

- `$fillable` fields that can be mass assigned
- the `member()` relationship to the [Member](../app/Models/Member.php) model
- `isAvailable()` to check if the book is borrowed or free
- `getInfo()` to return a simple array of book details

### Book Migration

[create_books_table](../database/migrations/2026_07_18_162324_create_books_table.php) creates the actual `books` table.

It defines:

- `title`
- `author`
- `category`
- `publish_year`
- `member_id`

The `member_id` column is nullable because a book can exist without being borrowed.

It is also a foreign key to the `members` table, so Laravel can keep the relationship valid.

### Book Seeder

[BookSeeder](../database/seeders/BookSeeder.php) fills the `books` table with sample records.

It uses `Book::create(...)` to insert books after the migration has created the table.

### Book Factory

[BookFactory](../database/factories/BookFactory.php) generates fake book data.

Right now it exists in the project, but the current seeders do not use it directly. The project uses manual `Book::create(...)` calls in the seeder instead.

### Book Views

The main book views are:

- `resources/views/books/index.blade.php` for the list page
- `resources/views/books/create.blade.php` for the create form
- `resources/views/books/edit.blade.php` for the edit form
- `resources/views/books/show.blade.php` for the detail page

These views display data that the controller sends to them.

## 3. Step-By-Step Book Communication

### A. Showing the list of books

1. The browser visits `/books`.
2. `routes/web.php` sends that request to `BookController@index`.
3. `BookController` asks `LibraryService` for the base query through `displayBooks()`.
4. If search text exists, the controller uses `searchBookByTitle()` and `searchBookByCategory()` to find matching IDs.
5. The controller applies sorting and pagination.
6. The `books.index` view receives the final `$books` data and renders it.

### B. Creating a book

1. The browser opens `/books/create`.
2. `BookController@create` returns the form view.
3. The user submits the form to `/books`.
4. `BookController@store` validates the request.
5. If validation passes, the controller calls `LibraryService::addBook()`.
6. `LibraryService` uses `Book::create(...)`.
7. Eloquent writes the new row into the `books` table.
8. The controller redirects back to `/books` with a success message.

### C. Editing a book

1. The browser opens `/books/{book}/edit`.
2. Laravel route-model binding loads the correct `Book` model automatically.
3. `BookController@edit` sends that book to the edit form.
4. The user submits the update form.
5. `BookController@update` validates the input.
6. The controller updates the existing `Book` model.
7. Eloquent saves the changed data into the database.

### D. Deleting a book

1. The user clicks delete in the books list.
2. The request goes to `BookController@destroy`.
3. The controller calls `LibraryService::removeBook()`.
4. The service deletes the book model.
5. The row is removed from the `books` table.

### E. Returning a book

1. The return form sends a request to `/books/{book}/return`.
2. `BookController@returnBook` receives the book model.
3. The controller sets `member_id` to `null`.
4. The book becomes available again.

## 4. Member File Flow

### MemberController

[MemberController](../app/Http/Controllers/MemberController.php) handles all member requests.

It is responsible for:

- listing members
- creating members
- editing members
- deleting members
- showing one member
- borrowing books for a member
- returning books from a member

It uses [LibraryService](../app/Services/LibraryService.php) for member creation through `addMember()`.

### Member Model

[Member](../app/Models/Member.php) represents one row in the `members` table.

It defines the `books()` relationship so a member can see all borrowed books.

### Member Migration

[create_members_table](../database/migrations/2026_07_18_162309_create_members_table.php) creates the `members` table.

It defines:

- `name`
- `email`

The email is unique, so no two members should share the same email address.

### Member Seeder

[MemberSeeder](../database/seeders/MemberSeeder.php) inserts sample members into the database.

### Member Views

The main member views are:

- `resources/views/members/index.blade.php`
- `resources/views/members/create.blade.php`
- `resources/views/members/edit.blade.php`
- `resources/views/members/show.blade.php`
- `resources/views/members/borrow.blade.php`

## 5. Step-By-Step Member Communication

### A. Showing the list of members

1. The browser visits `/members`.
2. `routes/web.php` sends the request to `MemberController@index`.
3. The controller loads members with their borrowed books using `with('books')`.
4. The `members.index` view shows the list.

### B. Creating a member

1. The browser opens `/members/create`.
2. The form submits to `/members`.
3. `MemberController@store` validates the name and email.
4. The controller calls `LibraryService::addMember()`.
5. The service uses `Member::create(...)`.
6. Eloquent inserts the new member into the `members` table.

### C. Borrowing a book

1. The browser opens the borrow page for a member.
2. `MemberController@borrowBooks` loads available books.
3. The user chooses a book.
4. `MemberController@borrow` checks if the book is available.
5. If the book is available, the controller updates `member_id` with the member ID.
6. The book is now linked to that member.

### D. Returning a book from a member

1. The member return form sends a request to `MemberController@returnBook`.
2. The controller checks whether the book really belongs to that member.
3. If it matches, the controller sets `member_id` to `null`.
4. The book becomes available again.

## 6. How The Files Communicate

Here is the communication chain in simple form:

`Route -> Controller -> Model or Service -> Database -> View`

More specifically:

- `routes/web.php` decides which controller method runs.
- The controller validates the request and prepares the data.
- The controller may call `LibraryService` for reusable logic.
- `LibraryService` uses Eloquent models like `Book` and `Member`.
- The model writes to or reads from the database tables created by migrations.
- The controller sends the final data to a Blade view.
- The view renders the HTML page in the browser.

## 7. Why This Structure Matters

- Controllers stay focused on request handling.
- Models stay focused on data and relationships.
- Migrations define the database schema in a repeatable way.
- Seeders make it easy to load starter data.
- Services keep shared logic in one place.
- Views stay separate from business logic.

That separation makes the project easier to read, debug, and extend.
