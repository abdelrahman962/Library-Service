# Postman API Guide for LibrarySystem

Base URL:
- http://127.0.0.1:8000

All API routes are prefixed with /api.

> If you are using the Laravel built-in server, make sure it is running first:
> php artisan serve --host=127.0.0.1 --port=8000

## 1. Get all books
- Method: GET
- URL: http://localhost/api/books

### Example
No body required.

## 2. Get one book by id
- Method: GET
- URL: http://localhost/api/books/1

### Example
Replace 1 with a real book id.

## 3. Create a new book
- Method: POST
- URL: http://localhost/api/books
- Headers:
  - Content-Type: application/json

### Body (JSON)
```json
{
  "title": "Design Principles",
  "author": "Robert Martin",
  "category": "Programming",
  "publish_year": 2020
}
```

## 4. Get all members
- Method: GET
- URL: http://localhost/api/members

### Example
No body required.

## 5. Get one member by id
- Method: GET
- URL: http://localhost/api/members/1

### Example
Replace 1 with a real member id.

## 6. Create a new member
- Method: POST
- URL: http://localhost/api/members
- Headers:
  - Content-Type: application/json

### Body (JSON)
```json
{
  "name": "Ahmed Ali",
  "email": "ahmed@example.com"
}
```

## 7. Borrow a book to a member
- Method: POST
- URL: http://localhost/api/members/1/books/2/borrow

### Example
Replace 1 with a member id and 2 with a book id.

## 8. Return a borrowed book
- Method: POST
- URL: http://localhost/api/members/1/books/2/return

### Example
Replace 1 with a member id and 2 with a book id.

## 9. Expected response format
Most endpoints return JSON like this:

```json
{
  "message": "Book created successfully",
  "data": {
    "id": 1,
    "title": "Design Principles"
  }
}
```

## 10. Tips for Postman
- Use the "Body" tab and select "raw" with JSON.
- For GET requests, no body is needed.
- For POST requests, set the header:
  - Content-Type: application/json
- If you get an error, make sure your Laravel server is running:
  - php artisan serve
