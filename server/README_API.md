# FeedMerge API Startup Guide

This guide will help you set up and run the FeedMerge FastAPI application with Celery for background task processing.

## Prerequisites

1. **Python 3.8+**
2. **PostgreSQL** database server
3. **Redis** server (for Celery message broker)
4. **AWS S3** bucket (for media uploads)

## Installation

1. **Install Python dependencies**:
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   python scripts/generate_keys.py  # Generate secure keys
   ```
   
   Edit `.env` with your configuration:
   ```env
   # Database
   DATABASE_URL=postgresql://username:password@localhost:5432/feedmerge_db
   
   # Security
   SECRET_KEY=your-generated-secret-key
   TOKEN_ENCRYPTION_KEY=your-generated-encryption-key
   
   # AWS S3
   AWS_ACCESS_KEY_ID=your-aws-access-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret-key
   AWS_S3_BUCKET=your-s3-bucket-name
   AWS_REGION=us-east-1
   
   # Redis
   REDIS_URL=redis://localhost:6379/0
   
   # OAuth (optional - for social media connections)
   TWITTER_CLIENT_ID=your-twitter-client-id
   TWITTER_CLIENT_SECRET=your-twitter-client-secret
   FACEBOOK_CLIENT_ID=your-facebook-client-id
   FACEBOOK_CLIENT_SECRET=your-facebook-client-secret
   # ... other platforms
   ```

3. **Set up the database**:
   ```bash
   # Create database
   createdb feedmerge_db
   
   # Run migrations
   python scripts/init_db.py
   alembic revision --autogenerate -m "Initial migration"
   alembic upgrade head
   ```

## Running the Application

### Option 1: Development Mode (Simple)

1. **Start the FastAPI server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   ```
   python server_runner.py
   ```

2. **Start Redis server** (in another terminal):
   ```bash
   redis-server
   ```

3. **Start Celery worker** (in another terminal):
   ```bash
   cd server
   celery -A app.core.celery_app:celery_app worker --loglevel=info
   ```

4. **Start Celery Beat scheduler** (in another terminal):
   ```bash
   cd server
   celery -A app.core.celery_app:celery_app beat --loglevel=info
   ```

### Option 2: Production Mode (with process management)

Use a process manager like **supervisord** or **systemd** to manage the services:

1. **FastAPI service**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

2. **Celery worker service**:
   ```bash
   celery -A app.core.celery_app:celery_app worker --loglevel=info --concurrency=4
   ```

3. **Celery Beat service**:
   ```bash
   celery -A app.core.celery_app:celery_app beat --loglevel=info
   ```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/token` - Login and get access token
- `GET /api/v1/auth/me` - Get current user profile
- `POST /api/v1/auth/oauth/connect` - Connect social media account

### Posts
- `POST /api/v1/posts/upload-url` - Get pre-signed URL for media upload
- `POST /api/v1/posts` - Create scheduled post
- `GET /api/v1/posts` - Get user's posts
- `GET /api/v1/posts/{post_id}` - Get specific post
- `PUT /api/v1/posts/{post_id}` - Update post
- `DELETE /api/v1/posts/{post_id}` - Delete post

## API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/api/v1/openapi.json

## Background Tasks

The application uses Celery for background task processing:

### Tasks
1. **publish_scheduled_posts**: Runs every minute to check for and publish scheduled posts
2. **publish_single_post**: Publishes a single post to all target platforms
3. **refresh_expired_tokens**: Refreshes expired OAuth tokens

### Monitoring
You can monitor Celery tasks using **Flower**:
```bash
pip install flower
celery -A app.core.celery_app:celery_app flower
```
Then visit: http://localhost:5555

## Social Media Platform Setup

### Twitter/X
1. Create a Twitter Developer account
2. Create a new App and get:
   - Client ID
   - Client Secret
3. Configure OAuth 2.0 settings

### Facebook
1. Create a Facebook Developer account
2. Create a new App and get:
   - App ID
   - App Secret
3. Add Facebook Login product

### Instagram
1. Set up Facebook for Business
2. Connect Instagram Business account
3. Use Facebook's Graph API

### LinkedIn
1. Create a LinkedIn Developer account
2. Create a new App and get:
   - Client ID
   - Client Secret
3. Request appropriate permissions

## AWS S3 Setup

1. Create an S3 bucket
2. Configure CORS policy:
   ```json
   [
     {
       "AllowedHeaders": ["*"],
       "AllowedMethods": ["GET", "PUT", "POST"],
       "AllowedOrigins": ["*"],
       "ExposeHeaders": []
     }
   ]
   ```
3. Create IAM user with S3 permissions

## Security Considerations

1. **Never commit secrets** to version control
2. **Use HTTPS** in production
3. **Configure CORS** properly for your domain
4. **Rotate encryption keys** regularly
5. **Monitor failed login attempts**
6. **Use rate limiting** (consider adding middleware)

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Check DATABASE_URL format
   - Ensure PostgreSQL is running
   - Verify database exists

2. **Celery worker not processing tasks**:
   - Check Redis connection
   - Verify Celery worker is running
   - Check logs for errors

3. **OAuth connection failures**:
   - Verify client credentials
   - Check redirect URIs
   - Ensure proper scopes

4. **S3 upload failures**:
   - Check AWS credentials
   - Verify bucket permissions
   - Check CORS configuration

### Logs
Check application logs for detailed error information:
```bash
# FastAPI logs
tail -f /var/log/feedmerge/api.log

# Celery worker logs
tail -f /var/log/feedmerge/celery.log

# Celery beat logs
tail -f /var/log/feedmerge/celery-beat.log
```

## Performance Optimization

1. **Database indexing**: Add indexes on frequently queried columns
2. **Connection pooling**: Configure SQLAlchemy connection pool
3. **Caching**: Add Redis caching for frequently accessed data
4. **Rate limiting**: Implement API rate limiting
5. **CDN**: Use CloudFront for media delivery

## Scaling

1. **Horizontal scaling**: Run multiple FastAPI instances behind a load balancer
2. **Celery scaling**: Add more worker processes/machines
3. **Database scaling**: Use read replicas for heavy read workloads
4. **Redis clustering**: Scale Redis for high availability
