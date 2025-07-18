# FeedMerge Database Schema

This document describes the database schema for the FeedMerge application, built with SQLAlchemy and PostgreSQL.

## Overview

The database consists of the following main entities:
- **Users**: Application users who create and manage posts
- **SocialConnections**: OAuth connections to social media platforms
- **Posts**: Content to be published across platforms
- **PostTargets**: Individual publishing targets for each post
- **NotificationTokens**: FCM tokens for push notifications

## Database Models

### User Model
- `id` (Primary Key): Unique identifier
- `email` (Unique): User's email address
- `hashed_password`: Bcrypt hashed password
- `name` (Nullable): User's display name
- `created_at`: Account creation timestamp
- `updated_at`: Last update timestamp
- `is_active`: Account status flag

### SocialConnection Model
- `id` (Primary Key): Unique identifier
- `platform` (Enum): Social media platform (Twitter, Facebook, Instagram, LinkedIn, TikTok, YouTube)
- `platform_user_id`: User ID on the social platform
- `encrypted_access_token`: Encrypted OAuth access token
- `encrypted_refresh_token` (Nullable): Encrypted OAuth refresh token
- `expires_at` (Nullable): Token expiration time
- `scopes` (JSON): OAuth permissions granted
- `user_id` (Foreign Key): Reference to User
- `created_at`, `updated_at`, `is_active`: Metadata fields

### Post Model
- `id` (Primary Key): Unique identifier
- `content`: Post text content
- `media_urls` (JSON): Array of media file URLs
- `status` (Enum): Draft, Scheduled, Published, Failed
- `scheduled_at` (Nullable): When to publish the post
- `published_at` (Nullable): When the post was actually published
- `user_id` (Foreign Key): Reference to User
- `created_at`, `updated_at`: Metadata fields

### PostTarget Model
- `id` (Primary Key): Unique identifier
- `post_id` (Foreign Key): Reference to Post
- `social_connection_id` (Foreign Key): Reference to SocialConnection
- `platform_post_id` (Nullable): Post ID from the social platform
- `status` (Enum): Publishing status for this specific target
- `error_message` (Nullable): Error details if publishing failed
- `published_at` (Nullable): When this target was published
- `created_at`, `updated_at`: Metadata fields

### NotificationToken Model
- `id` (Primary Key): Unique identifier
- `user_id` (Foreign Key): Reference to User
- `token`: FCM registration token
- `device_type` (Nullable): ios, android, web
- `device_id` (Nullable): Device identifier
- `is_active`: Token validity flag
- `created_at`, `updated_at`: Metadata fields

## Security Features

### Token Encryption
OAuth access and refresh tokens are encrypted using the `cryptography` library before storage:
- Uses Fernet symmetric encryption
- Encryption key stored in environment variables
- Automatic encryption/decryption in CRUD operations

### Password Hashing
User passwords are hashed using bcrypt via the `passlib` library:
- Salt rounds automatically managed
- Secure password verification
- Protection against timing attacks

## Database Setup

### Prerequisites
1. PostgreSQL database server
2. Python dependencies installed: `pip install -r requirements.txt`
3. Environment variables configured (see `.env.example`)

### Environment Variables
```env
DATABASE_URL=postgresql://username:password@localhost:5432/feedmerge_db
SECRET_KEY=your-secret-key-here
TOKEN_ENCRYPTION_KEY=your-encryption-key-here
```

### Initial Setup
1. **Create database**:
   ```bash
   createdb feedmerge_db
   ```

2. **Initialize Alembic** (if not already done):
   ```bash
   cd server
   python scripts/init_db.py
   ```

3. **Generate initial migration**:
   ```bash
   alembic revision --autogenerate -m "Initial migration"
   ```

4. **Apply migrations**:
   ```bash
   alembic upgrade head
   ```

### Migration Management

#### Create a new migration
```bash
alembic revision --autogenerate -m "Description of changes"
```

#### Apply migrations
```bash
alembic upgrade head
```

#### Rollback migration
```bash
alembic downgrade -1
```

#### Check migration status
```bash
alembic current
alembic history
```

## API Schemas (Pydantic)

### Schema Types
- **Base**: Common fields for the model
- **Create**: Fields required for creating new records
- **Update**: Fields that can be updated (all optional)
- **Read**: Fields returned in API responses
- **InDB**: Complete database representation

### Example Usage
```python
from app.schemas import UserCreate, UserRead
from app.crud import create_user

# Create a new user
user_data = UserCreate(email="user@example.com", password="secure123", name="John Doe")
new_user = create_user(db, user_data)

# The response will use UserRead schema (excludes password)
```

## CRUD Operations

All database operations are abstracted through CRUD modules:
- `app.crud.user`: User management
- `app.crud.social_connection`: OAuth connection management
- `app.crud.post`: Post and publishing management
- `app.crud.notification_token`: Push notification token management

### Example CRUD Usage
```python
from app.crud import get_user_by_email, create_social_connection
from app.schemas import SocialConnectionCreate

# Get user by email
user = get_user_by_email(db, "user@example.com")

# Create social connection
connection_data = SocialConnectionCreate(
    platform="twitter",
    platform_user_id="123456789",
    access_token="oauth_access_token",
    refresh_token="oauth_refresh_token"
)
connection = create_social_connection(db, connection_data, user.id)
```

## Best Practices

1. **Always use CRUD functions** instead of direct SQLAlchemy queries
2. **Use database transactions** for operations affecting multiple tables
3. **Validate data** using Pydantic schemas before database operations
4. **Handle encryption/decryption** automatically through CRUD functions
5. **Use soft deletes** where appropriate (is_active flag)
6. **Keep migrations small** and focused on single concerns
7. **Test migrations** in development before applying to production

## Troubleshooting

### Common Issues

1. **Migration conflicts**: 
   ```bash
   alembic merge heads
   ```

2. **Database connection errors**: 
   - Check DATABASE_URL format
   - Ensure PostgreSQL is running
   - Verify database exists

3. **Encryption errors**:
   - Check TOKEN_ENCRYPTION_KEY is set
   - Ensure key is Base64 encoded

4. **Schema validation errors**:
   - Check Pydantic model definitions
   - Ensure required fields are provided
