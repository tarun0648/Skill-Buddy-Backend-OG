# Skill Buddy Backend API Documentation

## Base URL
```
http://localhost:5000/api
```

## Authentication
All endpoints require authentication via `X-User-ID` header (except auth endpoints).

## Enhanced Parallel Processing Features

### Task Management Endpoints

#### Get All Task Status
```
GET /task/status/{user_id}
Headers: X-User-ID: {user_id}
```
Returns status of all tasks (resume, LinkedIn, GitHub, portfolio) for a user.

#### Get Task Status by Type
```
GET /task/status/{user_id}/{task_type}
Headers: X-User-ID: {user_id}
```
Returns status of tasks for a specific type (resume, linkedin, github, portfolio).

#### Cancel Task
```
POST /task/cancel/{task_id}
Headers: X-User-ID: {user_id}
```
Cancels a running task.

#### Get Task History
```
GET /task/history/{user_id}
Headers: X-User-ID: {user_id}
```
Returns complete task history for a user.

#### Get Task Statistics
```
GET /task/stats/{user_id}
Headers: X-User-ID: {user_id}
```
Returns task statistics and analytics for a user.

#### Cleanup Old Tasks
```
POST /task/cleanup
Headers: X-User-ID: {user_id}
Body: {"days_old": 7}
```
Cleans up old completed/failed tasks (admin function).

## Resume Processing (Enhanced)

### Upload Resume with Parallel Processing
```
POST /resume/upload
Headers: X-User-ID: {user_id}
Body: FormData
  - resume: file (PDF)
  - job_description: string (optional)
```
**Response:**
```json
{
  "message": "Resume uploaded and processing started",
  "task_id": "task_123",
  "user_id": "user_456",
  "status": "pending",
  "progress": 0
}
```

### Get Processing Status
```
GET /resume/status/{user_id}
Headers: X-User-ID: {user_id}
```
**Response:**
```json
{
  "user_id": "user_456",
  "task_id": "task_123",
  "resume_id": "resume_789",
  "status": "processing",
  "progress": 45,
  "filename": "resume.pdf",
  "created_at": "2024-01-01T10:00:00Z",
  "started_at": "2024-01-01T10:00:01Z",
  "completed_at": null,
  "error_message": null,
  "is_active": true
}
```

### Get Resume Results
```
GET /resume/results/{user_id}
Headers: X-User-ID: {user_id}
```
**Response (if completed):**
```json
{
  "user_id": "user_456",
  "task_id": "task_123",
  "resume_id": "resume_789",
  "status": "completed",
  "extracted_data": {...},
  "interview_questions": [...],
  "job_match_analysis": {...},
  "filename": "resume.pdf",
  "processed_at": "2024-01-01T10:05:00Z"
}
```

**Response (if processing):**
```json
{
  "user_id": "user_456",
  "status": "processing",
  "progress": 45,
  "message": "Resume processing in progress"
}
```

### Get Interview Questions
```
GET /resume/questions/{user_id}
Headers: X-User-ID: {user_id}
```

### Get Job Match Analysis
```
GET /resume/analysis/{user_id}
Headers: X-User-ID: {user_id}
```

### Reprocess Resume
```
POST /resume/reprocess/{user_id}
Headers: X-User-ID: {user_id}
Body: {"job_description": "New job description"}
```

### Delete Resume
```
DELETE /resume/delete/{user_id}
Headers: X-User-ID: {user_id}
```

### List All Resumes
```
GET /resume/list/{user_id}
Headers: X-User-ID: {user_id}
```

## Profile Analysis (Enhanced)

### LinkedIn Analysis

#### Start LinkedIn Analysis
```
POST /profile-analysis/analyze/linkedin
Headers: X-User-ID: {user_id}
Body: {"linkedin_url": "https://linkedin.com/in/username"}
```
**Response:**
```json
{
  "message": "LinkedIn analysis started",
  "user_id": "user_456",
  "task_id": "task_123",
  "status": "pending",
  "progress": 0
}
```

#### Get LinkedIn Status
```
GET /profile-analysis/status/linkedin/{user_id}
Headers: X-User-ID: {user_id}
```

#### Get LinkedIn Results
```
GET /profile-analysis/results/linkedin/{user_id}
Headers: X-User-ID: {user_id}
```

#### Reanalyze LinkedIn
```
POST /profile-analysis/reanalyze/linkedin/{user_id}
Headers: X-User-ID: {user_id}
```

### GitHub Analysis

#### Start GitHub Analysis
```
POST /profile-analysis/analyze/github
Headers: X-User-ID: {user_id}
Body: {"github_username": "username"}
```
**Response:**
```json
{
  "message": "GitHub analysis started",
  "user_id": "user_456",
  "task_id": "task_123",
  "status": "pending",
  "progress": 0
}
```

#### Get GitHub Status
```
GET /profile-analysis/status/github/{user_id}
Headers: X-User-ID: {user_id}
```

#### Get GitHub Results
```
GET /profile-analysis/results/github/{user_id}
Headers: X-User-ID: {user_id}
```

#### Reanalyze GitHub
```
POST /profile-analysis/reanalyze/github/{user_id}
Headers: X-User-ID: {user_id}
```

### Combined Results

#### Get All Analysis Results
```
GET /profile-analysis/results/{user_id}
Headers: X-User-ID: {user_id}
```

#### Get Improvement Suggestions
```
GET /profile-analysis/suggestions/{user_id}
Headers: X-User-ID: {user_id}
```

## Portfolio Analysis (Enhanced)

### Start Portfolio Analysis
```
POST /portfolio-analysis/analyze
Headers: X-User-ID: {user_id}
Body: {"portfolio_url": "https://example.com"}
```
**Response:**
```json
{
  "message": "Portfolio analysis started",
  "user_id": "user_456",
  "task_id": "task_123",
  "status": "pending",
  "progress": 0
}
```

### Get Portfolio Status
```
GET /portfolio-analysis/status/{user_id}
Headers: X-User-ID: {user_id}
```

### Get Portfolio Results
```
GET /portfolio-analysis/results/{user_id}
Headers: X-User-ID: {user_id}
```

### Get Portfolio Suggestions
```
GET /portfolio-analysis/suggestions/{user_id}
Headers: X-User-ID: {user_id}
```

### Reanalyze Portfolio
```
POST /portfolio-analysis/reanalyze/{user_id}
Headers: X-User-ID: {user_id}
```

### Delete Portfolio Analysis
```
DELETE /portfolio-analysis/delete/{user_id}
Headers: X-User-ID: {user_id}
```

### Get Extracted Data
```
GET /portfolio-analysis/extracted-data/{user_id}
Headers: X-User-ID: {user_id}
```

## Authentication

### Register User
```
POST /auth/register
Body: {
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}
```

### Login User
```
POST /auth/login
Body: {
  "email": "user@example.com",
  "password": "password123"
}
```

### Phone OTP Authentication

#### Send OTP
```
POST /auth/send-otp
Body: {
  "phone_number": "+1234567890",
  "method": "sms" // or "whatsapp"
}
```

#### Verify OTP
```
POST /auth/verify-otp
Body: {
  "phone_number": "+1234567890",
  "otp": "123456"
}
```

## User Management

### Get User Profile
```
GET /user/profile/{user_id}
Headers: X-User-ID: {user_id}
```

### Update User Profile
```
PUT /user/profile/{user_id}
Headers: X-User-ID: {user_id}
Body: {
  "name": "John Doe",
  "profession": "Software Engineer",
  "college_name": "University of Example",
  "career_choices": ["Web Development", "Mobile Development"]
}
```

### Get Profile Completion Status
```
GET /user/completion/{user_id}
Headers: X-User-ID: {user_id}
```

## Community Platform

### Create Post
```
POST /community/posts
Headers: X-User-ID: {user_id}
Body: {
  "title": "Post Title",
  "content": "Post content...",
  "category": "general"
}
```

### Get Posts
```
GET /community/posts
Headers: X-User-ID: {user_id}
Query Parameters:
  - category (optional)
  - page (optional, default: 1)
  - limit (optional, default: 10)
```

### Get Post Details
```
GET /community/posts/{post_id}
Headers: X-User-ID: {user_id}
```

### Create Comment
```
POST /community/posts/{post_id}/comments
Headers: X-User-ID: {user_id}
Body: {"content": "Comment content"}
```

### Like/Unlike Post
```
POST /community/posts/{post_id}/like
Headers: X-User-ID: {user_id}
```

## Status Endpoints

### API Status
```
GET /status
```

### Health Check
```
GET /
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

Common HTTP Status Codes:
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `429`: Rate Limited
- `500`: Internal Server Error

## Parallel Processing Features

### Key Benefits:
1. **Non-blocking Operations**: Users can navigate away while processing continues
2. **Status Persistence**: Processing status is saved and retrievable
3. **Progress Tracking**: Real-time progress updates available
4. **Task Management**: Centralized task control and monitoring
5. **Error Handling**: Robust error handling with detailed error messages
6. **Task Cancellation**: Ability to cancel running tasks
7. **History Tracking**: Complete task history and statistics

### Task States:
- `pending`: Task created, waiting to start
- `running`: Task is currently processing
- `completed`: Task finished successfully
- `failed`: Task failed with error
- `cancelled`: Task was cancelled by user

### Progress Tracking:
- Progress percentage (0-100)
- Start and completion timestamps
- Active task status
- Error messages for failed tasks
