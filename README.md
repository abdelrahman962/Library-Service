````md
# 📚 Library Management System

---

# 📌 Overview

**Library Management System** is a Laravel CRUD application designed to manage a small library efficiently.

The system provides complete management of:

- 📖 Books
- 👥 Members
- 🔄 Borrowing and returning operations
- 🔍 Searching and sorting
- 📄 Pagination
- ✅ Server-side validation
- 📊 Dashboard statistics

The application follows the **MVC architecture** and uses a **Service Layer pattern** to keep business logic clean and reusable.

---

# ✨ Features

## 📚 Book Management

| Feature | Description |
|---|---|
| Create Books | Add new books to the library |
| Update Books | Edit existing book information |
| Delete Books | Remove books from the system |
| Search | Find books by title or category |
| Sorting | Sort books by different fields |
| Pagination | Navigate through large book collections |
| Borrow Status | Track whether books are available |

---

## 👥 Member Management

| Feature | Description |
|---|---|
| Create Members | Register new library members |
| Update Members | Edit member information |
| Delete Members | Remove members |
| Search Members | Quickly find members |
| Borrow Books | Assign available books to members |
| Return Books | Process returned books |

---

# 🔎 Search & Pagination

The system supports:

- Searching without losing pagination state
- Sorting while maintaining query parameters
- Previous / next navigation
- Page number navigation

Example:

```text
/books?search=laravel&sort=title&page=2
````

---

# 🏗️ Application Architecture

The project follows Laravel best practices:

```
                Browser
                   |
                   |
              Routes (web.php)
                   |
                   |
             Controllers
                   |
          -------------------
          |                 |
       Services          Models
          |                 |
          -------------------
                   |
              Database
```

## MVC Responsibilities

| Layer      | Responsibility                       |
| ---------- | ------------------------------------ |
| Model      | Database structure and relationships |
| Controller | Handles requests and responses       |
| View       | Blade templates for UI               |
| Service    | Reusable business logic              |

---

# 📂 Project Structure

```
LibrarySystem
│
├── app
│   ├── Http
│   │   └── Controllers
│   │       ├── BookController.php
│   │       └── MemberController.php
│   │
│   ├── Models
│   │   ├── Book.php
│   │   └── Member.php
│   │
│   └── Services
│       └── LibraryService.php
│
├── database
│   ├── migrations
│   ├── seeders
│   └── factories
│
├── resources
│   └── views
│       ├── books
│       ├── members
│       └── dashboard
│
└── routes
    └── web.php
```

---

# 🗄️ Database Design

## Books Table

| Column     | Type        |
| ---------- | ----------- |
| id         | bigint      |
| title      | string      |
| author     | string      |
| category   | string      |
| member_id  | foreign key |
| created_at | timestamp   |
| updated_at | timestamp   |

---

## Members Table

| Column     | Type      |
| ---------- | --------- |
| id         | bigint    |
| name       | string    |
| email      | string    |
| created_at | timestamp |
| updated_at | timestamp |

---

# 🔗 Relationships

## Member → Books

A member can borrow multiple books.

```php
public function books()
{
    return $this->hasMany(Book::class);
}
```

---

## Book → Member

A book belongs to one member.

```php
public function member()
{
    return $this->belongsTo(Member::class);
}
```

---

# 🛠️ Technologies Used

| Technology         | Purpose               |
| ------------------ | --------------------- |
| Laravel 13         | Backend Framework     |
| PHP 8.3+           | Programming Language  |
| MySQL              | Database              |
| Blade              | Frontend Templates    |
| Eloquent ORM       | Database Interaction  |
| Bootstrap/Tailwind | Styling               |
| Composer           | Dependency Management |
| NPM                | Frontend Assets       |

---

# 🚀 Installation

## 1. Clone Repository

```bash
git clone <your-repository-url>

cd LibrarySystem
```

---

## 2. Install PHP Dependencies

```bash
composer install
```

---

## 3. Install Frontend Dependencies

```bash
npm install
```

---

## 4. Configure Environment

Create `.env` file:

```bash
cp .env.example .env
```

Generate application key:

```bash
php artisan key:generate
```

---

## 5. Configure Database

Update `.env`:

```env
DB_DATABASE=library_system
DB_USERNAME=root
DB_PASSWORD=
```

---

## 6. Run Database Setup

Run migrations and seed sample data:

```bash
php artisan migrate --seed
```

---

# ▶️ Running The Application

Start Laravel server:

```bash
php artisan serve
```

Start frontend development server:

```bash
npm run dev
```

Open:

```text
http://127.0.0.1:8000
```

---

# 🌐 Available Routes

| URL               | Description       |
| ----------------- | ----------------- |
| `/dashboard`      | Dashboard summary |
| `/books`          | Books listing     |
| `/books/create`   | Add new book      |
| `/members`        | Members listing   |
| `/members/create` | Add new member    |

---

# 🧪 Sample Data

Seeders provide:

* Example books
* Example members
* Borrowing relationships

Run:

```bash
php artisan db:seed
```

---

# 🔐 Validation

The application includes server-side validation.

Example:

```php
$request->validate([
    'title' => 'required|string|max:255',
    'author' => 'required|string',
]);
```

Validation errors are displayed directly inside Blade forms.

---

# 📈 Future Improvements

Possible enhancements:

* 🔐 Authentication and authorization
* 📧 Email notifications
* 📚 Borrow history tracking
* 📱 REST API support
* 📊 Advanced analytics dashboard
* 🔎 Full-text search
* 🧪 Automated testing

---

# 👨‍💻 Author

**Your Name**

Laravel Developer | Backend Developer

---

# 📄 License

This project is licensed under the MIT License.

```
```
