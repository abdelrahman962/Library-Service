# Laravel Project Structural Report

Generated: 2026-08-01
Project Root: `c:\laragon\www\LibrarySystem`

This report is intended to be machine- and human-comparable with another project's report.

## 1) DB Schema and Relationships

### 1.1 Tables and Columns (from migrations)

#### `books`
Source: `database/migrations/2026_07_18_162324_create_books_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| id | bigint unsigned | no | primary key | Laravel `id()` |
| title | varchar(255) | no | - | - |
| author | varchar(255) | no | - | - |
| category | varchar(255) | no | - | - |
| publish_year | int | no | - | - |
| member_id | bigint unsigned | yes | foreign key -> `members.id` | `nullOnDelete()` |
| created_at | timestamp | yes | - | Laravel timestamps |
| updated_at | timestamp | yes | - | Laravel timestamps |

#### `members`
Source: `database/migrations/2026_07_18_162309_create_members_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| id | bigint unsigned | no | primary key | Laravel `id()` |
| name | varchar(255) | no | - | - |
| email | varchar(255) | no | unique | - |
| created_at | timestamp | yes | - | Laravel timestamps |
| updated_at | timestamp | yes | - | Laravel timestamps |

#### `users`
Source: `database/migrations/0001_01_01_000000_create_users_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| id | bigint unsigned | no | primary key | Laravel `id()` |
| name | varchar(255) | no | - | - |
| email | varchar(255) | no | unique | - |
| email_verified_at | timestamp | yes | - | - |
| password | varchar(255) | no | - | - |
| remember_token | varchar(100) | yes | - | Laravel `rememberToken()` |
| created_at | timestamp | yes | - | Laravel timestamps |
| updated_at | timestamp | yes | - | Laravel timestamps |

#### `password_reset_tokens`
Source: `database/migrations/0001_01_01_000000_create_users_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| email | varchar(255) | no | primary key | - |
| token | varchar(255) | no | - | - |
| created_at | timestamp | yes | - | - |

#### `sessions`
Source: `database/migrations/0001_01_01_000000_create_users_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| id | varchar(255) | no | primary key | - |
| user_id | bigint unsigned | yes | index | no FK declared in migration |
| ip_address | varchar(45) | yes | - | - |
| user_agent | text | yes | - | - |
| payload | longtext | no | - | - |
| last_activity | int | no | index | - |

#### `cache`
Source: `database/migrations/0001_01_01_000001_create_cache_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| key | varchar(255) | no | primary key | - |
| value | mediumtext | no | - | - |
| expiration | bigint | no | index | - |

#### `cache_locks`
Source: `database/migrations/0001_01_01_000001_create_cache_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| key | varchar(255) | no | primary key | - |
| owner | varchar(255) | no | - | - |
| expiration | bigint | no | index | - |

#### `jobs`
Source: `database/migrations/0001_01_01_000002_create_jobs_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| id | bigint unsigned | no | primary key | Laravel `id()` |
| queue | varchar(255) | no | index | - |
| payload | longtext | no | - | - |
| attempts | smallint unsigned | no | - | - |
| reserved_at | int unsigned | yes | - | - |
| available_at | int unsigned | no | - | - |
| created_at | int unsigned | no | - | - |

#### `job_batches`
Source: `database/migrations/0001_01_01_000002_create_jobs_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| id | varchar(255) | no | primary key | - |
| name | varchar(255) | no | - | - |
| total_jobs | int | no | - | - |
| pending_jobs | int | no | - | - |
| failed_jobs | int | no | - | - |
| failed_job_ids | longtext | no | - | - |
| options | mediumtext | yes | - | - |
| cancelled_at | int | yes | - | - |
| created_at | int | no | - | - |
| finished_at | int | yes | - | - |

#### `failed_jobs`
Source: `database/migrations/0001_01_01_000002_create_jobs_table.php`

| Column | Type | Nullable | Index/Constraint | Notes |
|---|---|---|---|---|
| id | bigint unsigned | no | primary key | Laravel `id()` |
| uuid | varchar(255) | no | unique | - |
| connection | varchar(255) | no | - | - |
| queue | varchar(255) | no | - | - |
| payload | longtext | no | - | - |
| exception | longtext | no | - | - |
| failed_at | timestamp | no | index part (`connection`,`queue`,`failed_at`) | default current timestamp |

### 1.2 Eloquent Models and Relationships

#### `App\Models\Book`
- Table inference: `books`
- Fillable: `title`, `author`, `category`, `publish_year`, `member_id`
- Relationships:
  - `member(): belongsTo(Member::class)`
- Domain helpers:
  - `isAvailable(): bool` returns `member_id == null`
  - `getInfo(): array` returns normalized book metadata

#### `App\Models\Member`
- Table inference: `members`
- Fillable: `name`, `email`
- Relationships:
  - `books(): hasMany(Book::class)`
- Domain helpers:
  - `getBorrowedBooks()` returns `$this->books`

#### `App\Models\User`
- Table inference: `users`
- Uses PHP attributes for fillable/hidden:
  - `#[Fillable(['name', 'email', 'password'])]`
  - `#[Hidden(['password', 'remember_token'])]`
- Casts:
  - `email_verified_at => datetime`
  - `password => hashed`
- No explicit relationships declared in model.

### 1.3 Relationship Map (Entity-Level)

- `Member (1) -> (N) Book` via `books.member_id`
- `Book (N) -> (1) Member` via `member()`
- `User` is currently isolated from library domain entities.

## 2) Routes

Route files present:
- `routes/web.php`
- `routes/console.php`

Route file absent:
- `routes/api.php` (not present in workspace)

Below is the complete route matrix derived from `routes/web.php` plus resource expansion and runtime route inspection (`php artisan route:list -v`).

| Method | URI | Name | Controller@Method / Action | Middleware |
|---|---|---|---|---|
| ANY | `/` | - | `Illuminate\Routing\RedirectController` (`/` -> `/dashboard`) | `web` |
| GET\|HEAD | `/books` | `books.index` | `BookController@index` | `web` |
| POST | `/books` | `books.store` | `BookController@store` | `web` |
| GET\|HEAD | `/books/create` | `books.create` | `BookController@create` | `web` |
| GET\|HEAD | `/books/{book}` | `books.show` | `BookController@show` | `web` |
| PUT\|PATCH | `/books/{book}` | `books.update` | `BookController@update` | `web` |
| DELETE | `/books/{book}` | `books.destroy` | `BookController@destroy` | `web` |
| GET\|HEAD | `/books/{book}/edit` | `books.edit` | `BookController@edit` | `web` |
| POST | `/books/{book}/return` | `books.return` | `BookController@returnBook` | `web` |
| GET\|HEAD | `/members` | `members.index` | `MemberController@index` | `web` |
| POST | `/members` | `members.store` | `MemberController@store` | `web` |
| GET\|HEAD | `/members/create` | `members.create` | `MemberController@create` | `web` |
| GET\|HEAD | `/members/{member}` | `members.show` | `MemberController@show` | `web` |
| PUT\|PATCH | `/members/{member}` | `members.update` | `MemberController@update` | `web` |
| DELETE | `/members/{member}` | `members.destroy` | `MemberController@destroy` | `web` |
| GET\|HEAD | `/members/{member}/edit` | `members.edit` | `MemberController@edit` | `web` |
| GET\|HEAD | `/members/{member}/books` | `members.borrow.books` | `MemberController@borrowBooks` | `web` |
| POST | `/members/{member}/books/{book}/borrow` | `members.borrow` | `MemberController@borrow` | `web` |
| POST | `/members/{member}/books/{book}/return` | `members.return` | `MemberController@returnBook` | `web` |
| GET\|HEAD | `/dashboard` | `dashboard` | `DashboardController@index` | `web` |

Additional framework-provided routes seen in runtime route list (not defined in `routes/web.php`):
- `GET|HEAD storage/{path}` (`storage.local`)
- `PUT storage/{path}` (`storage.local.upload`)
- `GET|HEAD up` (health route)

## 3) Controllers

### 3.1 `BookController`
Source: `app/Http/Controllers/BookController.php`

Dependencies:
- Models: `Book`
- Services: `LibraryService` (constructor-injected)

Methods:

| Method | Uses | Behavior Summary | Returns |
|---|---|---|---|
| `index(Request $request)` | `LibraryService`, `Book` query builder | Gets base query from service; optional search by title/category; applies sort option; paginates 10 | `view('books.index')` |
| `show(Book $book)` | `Book` | Displays one book | `view('books.show')` |
| `create()` | - | Shows create form | `view('books.create')` |
| `store(Request $request)` | `LibraryService` | Validates inputs; creates book via service | `redirect('/books')` + flash |
| `edit(Book $book)` | `Book` | Shows edit form | `view('books.edit')` |
| `update(Request $request, Book $book)` | `Book` | Validates and updates model directly | `redirect('/books')` + flash |
| `destroy(Book $book)` | `LibraryService` | Deletes book via service | `redirect('/books')` |
| `returnBook(Book $book)` | `Book` | Sets `member_id` to null | `redirect('/books')` + flash |

Return types observed: `view`, `redirect` (no JSON responses).

### 3.2 `MemberController`
Source: `app/Http/Controllers/MemberController.php`

Dependencies:
- Models: `Member`, `Book`
- Services: `LibraryService` (constructor-injected)

Methods:

| Method | Uses | Behavior Summary | Returns |
|---|---|---|---|
| `index(Request $request)` | `Member` | Searches by member name/email or lists all; eager-loads books; paginates 5 | `view('members.index')` |
| `create()` | - | Shows create form | `view('members.create')` |
| `store(Request $request)` | `LibraryService` | Validates and creates member via service | `redirect('/members')` + flash |
| `edit(Member $member)` | `Member` | Shows edit form | `view('members.edit')` |
| `show(Member $member)` | `Member` | Loads borrowed books for member | `view('members.show')` |
| `update(Request $request, Member $member)` | `Member` | Validates and updates member directly | `redirect('/members')` |
| `destroy(Member $member)` | `Member` | Deletes member | `redirect('/members')` |
| `borrowBooks(Request $request, Member $member)` | `Book`, `Member` | Lists/searches books to borrow for selected member; paginates 5 | `view('members.borrow')` |
| `borrow(Member $member, Book $book)` | `Book`, `Member` | Guard: only borrow if available; sets `member_id` | `redirect()->back()` + flash |
| `returnBook(Member $member, Book $book)` | `Book`, `Member` | Guard: verify ownership; sets `member_id` to null | `redirect()->back()` + flash |

Return types observed: `view`, `redirect` (no JSON responses).

### 3.3 `DashboardController`
Source: `app/Http/Controllers/DashboardController.php`

Dependencies:
- Models: `Book`, `Member`
- Services: none

Methods:

| Method | Uses | Behavior Summary | Returns |
|---|---|---|---|
| `index()` | `Book`, `Member` | Computes counts for total books, borrowed books, available books, total members | `view('dashboard')` |

Return types observed: `view` only.

## 4) Views

### 4.1 Blade Inventory

- `resources/views/dashboard.blade.php`
- `resources/views/welcome.blade.php`
- `resources/views/books/index.blade.php`
- `resources/views/books/show.blade.php`
- `resources/views/books/create.blade.php`
- `resources/views/books/edit.blade.php`
- `resources/views/books/borrow.blade.php`
- `resources/views/members/index.blade.php`
- `resources/views/members/show.blade.php`
- `resources/views/members/create.blade.php`
- `resources/views/members/edit.blade.php`
- `resources/views/members/borrow.blade.php`
- `resources/views/pagination/custom.blade.php`

### 4.2 Parent Layout and Controller Mapping

No inspected Blade file in this project uses `@extends(...)`; each page is standalone HTML or a reusable partial.

| Blade File | Parent Layout | Returned By Controller Method |
|---|---|---|
| `dashboard.blade.php` | none | `DashboardController@index` |
| `books/index.blade.php` | none | `BookController@index` |
| `books/show.blade.php` | none | `BookController@show` |
| `books/create.blade.php` | none | `BookController@create` |
| `books/edit.blade.php` | none | `BookController@edit` |
| `members/index.blade.php` | none | `MemberController@index` |
| `members/show.blade.php` | none | `MemberController@show` |
| `members/create.blade.php` | none | `MemberController@create` |
| `members/edit.blade.php` | none | `MemberController@edit` |
| `members/borrow.blade.php` | none | `MemberController@borrowBooks` |
| `pagination/custom.blade.php` | partial, no parent | referenced by `books/index.blade.php` and `members/index.blade.php` via `links('pagination.custom')` |
| `welcome.blade.php` | none | not returned by any controller method in current `routes/web.php` |
| `books/borrow.blade.php` | none | not returned by any controller method in current controller set |

## 5) MVC Flow Summary and Deviation Flags

### 5.1 End-to-End Flow Patterns

Primary application flow:
1. Route dispatch (from `routes/web.php`) resolves to controller actions.
2. Controller actions execute validation + domain behavior.
3. Domain behavior uses Eloquent models directly and partially via `LibraryService`.
4. Controller returns Blade view (HTML response) or redirect with flash message.
5. Blade views render model data and basic conditional display logic.

Example flow A (list books):
- `GET /books` -> `BookController@index` -> `LibraryService::displayBooks()` + search/sort query composition -> `books.index` view.

Example flow B (borrow book through member):
- `POST /members/{member}/books/{book}/borrow` -> `MemberController@borrow` -> `Book::isAvailable()` + `Book::update(member_id)` -> redirect back.

Example flow C (dashboard summary):
- `GET /dashboard` -> `DashboardController@index` -> aggregate counts on `Book`/`Member` -> `dashboard` view.

### 5.2 Clean MVC Assessment

#### Positive patterns
- Models contain relationship methods (`Book::member`, `Member::books`) and small domain helpers.
- Controllers consistently return either views or redirects.
- Service layer exists (`LibraryService`) and is dependency-injected.

#### Deviations / risks from clean MVC
1. **Inconsistent service-layer usage**
   - Some write actions use `LibraryService` (`store`, `destroy`), while others write directly in controllers (`update`, `returnBook`, member update/delete/borrow-return).
   - Impact: mixed orchestration style increases maintenance cost and makes rules harder to centralize.

2. **Controller-heavy query orchestration**
   - Search and sorting logic is in controllers (`BookController@index`, `MemberController@index`, `MemberController@borrowBooks`) rather than query scopes/repositories.
   - Impact: controllers can grow and become harder to test in isolation.

3. **Potential orphan/unused UI artifacts**
   - `resources/views/books/borrow.blade.php` is not returned by any controller and posts to `/books/{book}/borrow`, which has no matching route.
   - `resources/views/welcome.blade.php` appears unused by current routes.

4. **Potential N+1 query in borrow-books page**
   - `MemberController@borrowBooks` fetches books without eager-loading `member`, while `members/borrow.blade.php` reads `$book->member`.
   - Impact: can trigger additional queries per row.

5. **Framework vs app route noise for comparison**
   - Runtime route list includes framework-provided routes (`storage/*`, `up`) that are not in `web.php`.
   - Impact: cross-project comparisons should separate app-defined routes from framework-provided routes.

### 5.3 Comparison Tips (for the next project)

When generating the next report, keep the same section/order and compare:
- Table-level schema diffs (added/removed columns, type changes, nullability, FK behavior).
- Route matrix diffs (method/URI/name/action/middleware).
- Controller responsibility diffs (service usage consistency, return-type patterns).
- View mapping diffs (orphaned views, layout strategy).
- MVC quality flags (logic placement, coupling, query efficiency risks).
