# 📚 Library Management System

A modern Laravel REST API for managing library operations including books, members, and borrowing transactions with AI agent integration.

---

## 📌 Overview

**Library Management System** is a production-ready Laravel application designed to manage library operations efficiently. It combines the power of REST API architecture with Laravel best practices, including service layer pattern, proper validation, and AI assistant capabilities.

### Key Capabilities

- 📖 **Complete Book Management** - Create, read, update, and soft delete books
- 👥 **Member Management** - Register, manage, and track members
- 🔄 **Borrowing System** - Track book borrowing and returns with history
- 🤖 **AI Assistant** - LibraryAssistant AI agent with 6 integrated tools
- 📊 **Dashboard Statistics** - Real-time library metrics and analytics
- 🔐 **Role-Based Access** - Admin and member-level access control
- 🔍 **Advanced Search** - Search books and members by title/category/name
- 📄 **Pagination** - Efficient data pagination with metadata
- ✅ **Comprehensive Validation** - Server-side validation for all inputs
- 📝 **Activity Logging** - Complete audit trail of all operations

---

## ✨ Features

### 📚 Book Management

| Feature | Description |
|---|---|
| **Create Books** | Admin can add new books with title, author, category, and year |
| **View Books** | Browse all books with pagination capability |
| **Update Books** | Admin can modify book information anytime |
| **Soft Delete** | Admin can soft delete books (recoverable via restore) |
| **Restore Books** | Recover previously soft-deleted books |
| **Search** | Find books by title or category |
| **Availability Tracking** | See current borrow status of each book |

### 👥 Member Management

| Feature | Description |
|---|---|
| **Registration** | Members can self-register with email verification |
| **Member Profiles** | View and update member information |
| **Admin Management** | Admin can create, edit, and manage members |
| **Role Assignment** | Designate admin members for elevated privileges |
| **Soft Delete** | Remove members while preserving history |
| **Search** | Find members by name or email |

### 🔄 Borrowing & Returns

| Feature | Description |
|---|---|
| **Borrow Books** | Members can borrow available books |
| **Return Books** | Track book returns and update availability |
| **Borrow History** | View detailed history of all transactions |
| **Availability Status** | Real-time tracking of book availability |
| **Member's Books** | See current books borrowed by member |

### 🤖 AI Integration

| Feature | Description |
|---|---|
| **Library Assistant** | AI agent powered by LarAgent framework |
| **6 Integrated Tools** | Predefined tools for common library operations |
| **Context Awareness** | AI has access to complete library statistics |
| **Smart Responses** | Natural language understanding and responses |

---

## 🚀 Quick Start

### Prerequisites

- PHP 8.2+
- Composer
- MySQL or SQLite
- Node.js & npm (for frontend assets)
- Laravel 11.x

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd LibrarySystem
   ```

2. **Install dependencies**
   ```bash
   composer install
   npm install
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   php artisan key:generate
   ```

4. **Setup database**
   ```bash
   php artisan migrate
   php artisan db:seed
   ```

5. **Start the application**
   ```bash
   php artisan serve
   npm run dev
   ```

The API will be available at `http://localhost:8000/api`

---

## 🔐 Authentication

### Authentication Method: Sanctum Token

The API uses Laravel Sanctum for API authentication.

#### Register (Create Account)

**Endpoint:** `POST /api/register`

**Request:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "password123",
  "password_confirmation": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Member registered successfully",
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com",
    "is_admin": false,
    "created_at": "2026-09-02T10:00:00Z"
  },
  "token": "1|abcdef123456"
}
```

#### Login (Get Token)

**Endpoint:** `POST /api/login`

**Request:**
```json
{
  "email": "john@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "id": 1,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "token": "1|abcdef123456"
}
```

#### Using the Token

Add the token to request headers:
```
Authorization: Bearer YOUR_TOKEN_HERE
```

#### Logout

**Endpoint:** `POST /api/logout`

**Headers:** `Authorization: Bearer YOUR_TOKEN`

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 📚 API Documentation

### Response Format

All API responses follow a consistent format:

#### Success Response
```json
{
  "success": true,
  "message": "Optional message",
  "data": { }
}
```

#### Error Response
```json
{
  "success": false,
  "message": "Error message",
  "errors": { }
}
```

### Books Endpoints

#### Get All Books

**Endpoint:** `GET /api/books`

**Query Parameters:**
- `search` (string) - Search by title or category
- `sort` (string) - Sort order: `title_asc` | `title_desc` | `newest` | `oldest`
- `page` (integer) - Page number (default: 1)

**Example:**
```
GET /api/books?search=Laravel&sort=title_asc&page=1
```

**Response:**
```json
{
  "success": true,
  "data": {
    "books": [],
    "pagination": {
      "current_page": 1,
      "per_page": 10,
      "total": 47,
      "last_page": 5
    }
  }
}
```

---

#### Get Single Book

**Endpoint:** `GET /api/books/{id}`

**Headers:** None required for public access

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "title": "Laravel Guide",
    "author": "Taylor Otwell",
    "category": "Programming",
    "publish_year": 2024,
    "member_id": null,
    "created_at": "2026-09-02T10:00:00Z",
    "updated_at": "2026-09-02T10:00:00Z"
  }
}
```

---

#### Create Book (Admin Only)

**Endpoint:** `POST /api/books`

**Headers:** `Authorization: Bearer TOKEN`

**Request:**
```json
{
  "title": "Laravel Guide",
  "author": "Taylor Otwell",
  "category": "Programming",
  "publish_year": 2024
}
```

**Response:** Created book object with 201 status

---

#### Update Book (Admin Only)

**Endpoint:** `PUT /api/books/{id}`

**Headers:** `Authorization: Bearer TOKEN`

**Request:** (All fields optional)
```json
{
  "title": "Advanced Laravel",
  "author": "Taylor Otwell",
  "category": "Programming",
  "publish_year": 2025
}
```

---

#### Delete Book (Admin Only)

**Endpoint:** `DELETE /api/books/{id}`

**Headers:** `Authorization: Bearer TOKEN`

**Response:**
```json
{
  "success": true,
  "message": "Book deleted successfully"
}
```

---

#### Restore Book (Admin Only)

**Endpoint:** `PATCH /api/books/{id}/restore`

**Headers:** `Authorization: Bearer TOKEN`

**Response:** Restored book object

---

### Members Endpoints

#### Get All Members (Admin Only)

**Endpoint:** `GET /api/members`

**Query Parameters:**
- `search` (string) - Search by name or email
- `sort` (string) - `name_asc` | `name_desc` | `newest` | `oldest`
- `page` (integer) - Page number (default: 1)

---

#### Get Single Member (Admin Only)

**Endpoint:** `GET /api/members/{id}`

---

#### Create Member (Admin Only)

**Endpoint:** `POST /api/members`

**Request:**
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "secure_password",
  "password_confirmation": "secure_password"
}
```

---

#### Update Member (Admin Only)

**Endpoint:** `PUT /api/members/{id}`

**Request:** (All fields optional)
```json
{
  "name": "Jane Smith",
  "email": "jane.smith@example.com",
  "is_admin": true
}
```

---

#### Delete Member (Admin Only)

**Endpoint:** `DELETE /api/members/{id}`

---

#### Restore Member (Admin Only)

**Endpoint:** `PATCH /api/members/{id}/restore`

---

### Borrowing Endpoints

#### Get My Borrowed Books

**Endpoint:** `GET /api/member/books`

**Headers:** `Authorization: Bearer TOKEN`

**Response:**
```json
{
  "success": true,
  "data": {
    "books": [],
    "pagination": {
      "current_page": 1,
      "per_page": 5,
      "total": 10,
      "last_page": 2
    }
  }
}
```

---

#### Borrow a Book

**Endpoint:** `POST /api/books/{bookId}/borrow`

**Headers:** `Authorization: Bearer TOKEN`

**Response:**
```json
{
  "success": true,
  "message": "Book borrowed successfully",
  "data": { book object }
}
```

---

#### Return a Book

**Endpoint:** `POST /api/books/{bookId}/return`

**Headers:** `Authorization: Bearer TOKEN`

---

#### Get My Borrow History

**Endpoint:** `GET /api/member/history`

**Headers:** `Authorization: Bearer TOKEN`

**Response:**
```json
{
  "success": true,
  "data": {
    "history": []
  }
}
```

---

#### Get Book Borrow History (Admin Only)

**Endpoint:** `GET /api/books/{bookId}/history`

---

## 🏗️ Project Architecture

### Folder Structure

```
app/
├── AiAgents/          # AI Agent implementation
├── Http/
│   ├── Controllers/   # API controllers
│   ├── Middleware/    # Custom middleware
│   └── Requests/      # Form request validation
├── Models/            # Eloquent models
├── Services/          # Business logic layer
└── Traits/            # Reusable traits (ApiResponse)

database/
├── migrations/        # Database schema
└── seeders/          # Database seeders

routes/
├── api.php           # API routes
└── web.php           # Web routes

tests/
├── Feature/          # Feature tests
└── Unit/             # Unit tests
```

### Architecture Pattern: MVC + Service Layer

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
   ┌───▼────┐
   │ Routes │
   └───┬────┘
       │
   ┌───▼───────────┐
   │ Controllers   │  (HTTP handling)
   └───┬───────────┘
       │
   ┌───▼─────────┐
   │ Services    │   (Business logic)
   └───┬─────────┘
       │
   ┌───▼────┐
   │ Models  │      (Data & relationships)
   └───┬────┘
       │
   ┌───▼────────┐
   │ Database   │
   └────────────┘
```

---

## 🧪 Testing

Run tests with:
```bash
php artisan test
```

Run specific test:
```bash
php artisan test tests/Feature/ApiEndpointsTest.php
```

---

## 🔧 Configuration

### Environment Variables

Key environment variables in `.env`:

```env
APP_NAME="Library System"
APP_ENV=production
APP_DEBUG=false
APP_URL=http://localhost

DB_CONNECTION=mysql
DB_HOST=127.0.0.1
DB_PORT=3306
DB_DATABASE=library_system
DB_USERNAME=root
DB_PASSWORD=

MAIL_MAILER=smtp
MAIL_HOST=smtp.mailtrap.io
MAIL_PORT=465
```

---

## 📊 Database Schema

### Books Table
- `id` - Primary key
- `title` - Book title
- `author` - Author name
- `category` - Book category
- `publish_year` - Publication year
- `member_id` - FK to borrowing member
- `deleted_at` - Soft delete timestamp

### Members Table
- `id` - Primary key
- `name` - Member name
- `email` - Email address (unique)
- `password` - Hashed password
- `is_admin` - Admin flag
- `deleted_at` - Soft delete timestamp

### Borrow Histories Table
- `id` - Primary key
- `member_id` - FK to member
- `book_id` - FK to book
- `borrowed_at` - Borrow timestamp
- `returned_at` - Return timestamp

---

## 🚀 Deployment

For production deployment:

1. Set `APP_DEBUG=false` in `.env`
2. Run `php artisan config:cache`
3. Run `php artisan route:cache`
4. Set up proper database backups
5. Configure email service
6. Use HTTPS for API endpoints

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📝 License

This project is open source and available under the MIT License.

---

## 📞 Support

For issues or questions, please open an issue on the repository or contact the development team.

---

## 🎯 Future Enhancements

- [ ] Book due dates and fine system
- [ ] Book reservations
- [ ] Email notifications
- [ ] Advanced reporting
- [ ] Book recommendations
- [ ] API versioning (v1, v2)
- [ ] Rate limiting
- [ ] Advanced authorization policies
- [ ] Docker deployment
- [ ] CI/CD pipeline

---

**Last Updated:** September 2, 2026


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
