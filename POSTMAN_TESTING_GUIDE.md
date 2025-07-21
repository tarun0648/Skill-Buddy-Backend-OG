# Postman Testing Guide - Skill Buddy Backend

## Setup Instructions

### 1. Environment Setup
1. Open Postman
2. Create a new environment called "Skill Buddy Backend"
3. Add the following variables:
   - `base_url`: `http://localhost:5000/api`
   - `user_id`: (will be set after registration)
   - `auth_token`: (will be set after login)
   - `task_id`: (will be set after starting tasks)

### 2. Collection Setup
1. Create a new collection called "Skill Buddy Backend API"
2. Organize requests into folders:
   - Authentication
   - User Management
   - Resume Processing
   - Profile Analysis
   - Portfolio Analysis
   - Task Management
   - Community
   - Status

---

## 1. Authentication Testing

### 1.1 User Registration
**Request:**
- Method: `POST`
- URL: `{{base_url}}/auth/register`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "email": "testuser@example.com",
  "password": "TestPassword123!",
  "name": "Test User"
}
```

**Expected Response:**
```json
{
  "message": "User registered successfully",
  "user_id": "user_123",
  "email": "testuser@example.com"
}
```

**Test Script:**
```javascript
pm.test("Registration successful", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property('user_id');
    pm.environment.set("user_id", response.user_id);
});
```

### 1.2 User Login
**Request:**
- Method: `POST`
- URL: `{{base_url}}/auth/login`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "email": "testuser@example.com",
  "password": "TestPassword123!"
}
```

**Expected Response:**
```json
{
  "message": "Login successful",
  "user_id": "user_123",
  "token": "jwt_token_here"
}
```

**Test Script:**
```javascript
pm.test("Login successful", function () {
    pm.response.to.have.status(200);
    const response = pm.response.json();
    pm.expect(response).to.have.property('token');
    pm.environment.set("auth_token", response.token);
});
```

### 1.3 Phone OTP - Send OTP
**Request:**
- Method: `POST`
- URL: `{{base_url}}/auth/send-otp`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "phone_number": "+1234567890",
  "method": "sms"
}
```

**Expected Response:**
```json
{
  "message": "OTP sent successfully",
  "phone_number": "+1234567890"
}
```

### 1.4 Phone OTP - Verify OTP
**Request:**
- Method: `POST`
- URL: `{{base_url}}/auth/verify-otp`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "phone_number": "+1234567890",
  "otp": "123456"
}
```

---

## 2. User Management Testing

### 2.1 Get User Profile
**Request:**
- Method: `GET`
- URL: `{{base_url}}/user/profile/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

**Expected Response:**
```json
{
  "user_id": "user_123",
  "name": "Test User",
  "email": "testuser@example.com",
  "profession": null,
  "college_name": null,
  "career_choices": []
}
```

### 2.2 Update User Profile
**Request:**
- Method: `PUT`
- URL: `{{base_url}}/user/profile/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "name": "Updated Test User",
  "profession": "Software Engineer",
  "college_name": "Test University",
  "career_choices": ["Web Development", "Mobile Development"]
}
```



## 3. Resume Processing Testing

### 3.1 Upload Resume
**Request:**
- Method: `POST`
- URL: `{{base_url}}/resume/upload`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
- Body: `form-data`
  - Key: `resume` (Type: File) - Select a PDF file
  - Key: `job_description` (Type: Text) - "Software Engineer position"

**Expected Response:**
```json
{
  "message": "Resume uploaded and processing started",
  "task_id": "task_123",
  "user_id": "user_123",
  "status": "pending",
  "progress": 0
}
```

**Test Script:**
```javascript
pm.test("Resume upload started", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property('task_id');
    pm.environment.set("resume_task_id", response.task_id);
});
```

### 3.2 Get Resume Processing Status
**Request:**
- Method: `GET`
- URL: `{{base_url}}/resume/status/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

**Expected Response:**
```json
{
  "user_id": "user_123",
  "task_id": "task_123",
  "resume_id": "resume_456",
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

### 3.3 Get Resume Results (Poll until completed)
**Request:**
- Method: `GET`
- URL: `{{base_url}}/resume/results/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

**Test Script:**
```javascript
pm.test("Resume results available", function () {
    const response = pm.response.json();
    if (response.status === "completed") {
        pm.expect(response).to.have.property('extracted_data');
        pm.expect(response).to.have.property('interview_questions');
        pm.expect(response).to.have.property('job_match_analysis');
    } else {
        pm.expect(response.status).to.be.oneOf(['pending', 'processing']);
    }
});
```

### 3.4 Get Interview Questions
**Request:**
- Method: `GET`
- URL: `{{base_url}}/resume/questions/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 3.5 Get Job Match Analysis
**Request:**
- Method: `GET`
- URL: `{{base_url}}/resume/analysis/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 3.6 List All Resumes
**Request:**
- Method: `GET`
- URL: `{{base_url}}/resume/list/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 3.7 Reprocess Resume
**Request:**
- Method: `POST`
- URL: `{{base_url}}/resume/reprocess/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "job_description": "Senior Software Engineer position with focus on Python and React"
}
```

### 3.8 Delete Resume
**Request:**
- Method: `DELETE`
- URL: `{{base_url}}/resume/delete/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

---

## 4. Profile Analysis Testing

### 4.1 LinkedIn Analysis - Start Analysis
**Request:**
- Method: `POST`
- URL: `{{base_url}}/profile-analysis/analyze/linkedin`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "linkedin_url": "https://linkedin.com/in/testuser"
}
```

**Expected Response:**
```json
{
  "message": "LinkedIn analysis started",
  "user_id": "user_123",
  "task_id": "task_456",
  "status": "pending",
  "progress": 0
}
```

**Test Script:**
```javascript
pm.test("LinkedIn analysis started", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property('task_id');
    pm.environment.set("linkedin_task_id", response.task_id);
});
```

### 4.2 LinkedIn Analysis - Get Status
**Request:**
- Method: `GET`
- URL: `{{base_url}}/profile-analysis/status/linkedin/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 4.3 LinkedIn Analysis - Get Results
**Request:**
- Method: `GET`
- URL: `{{base_url}}/profile-analysis/results/linkedin/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 4.4 LinkedIn Analysis - Reanalyze
**Request:**
- Method: `POST`
- URL: `{{base_url}}/profile-analysis/reanalyze/linkedin/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 4.5 GitHub Analysis - Start Analysis
**Request:**
- Method: `POST`
- URL: `{{base_url}}/profile-analysis/analyze/github`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "github_username": "testuser"
}
```

**Expected Response:**
```json
{
  "message": "GitHub analysis started",
  "user_id": "user_123",
  "task_id": "task_789",
  "status": "pending",
  "progress": 0
}
```

**Test Script:**
```javascript
pm.test("GitHub analysis started", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property('task_id');
    pm.environment.set("github_task_id", response.task_id);
});
```

### 4.6 GitHub Analysis - Get Status
**Request:**
- Method: `GET`
- URL: `{{base_url}}/profile-analysis/status/github/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 4.7 GitHub Analysis - Get Results
**Request:**
- Method: `GET`
- URL: `{{base_url}}/profile-analysis/results/github/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 4.8 GitHub Analysis - Reanalyze
**Request:**
- Method: `POST`
- URL: `{{base_url}}/profile-analysis/reanalyze/github/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 4.9 Get All Analysis Results
**Request:**
- Method: `GET`
- URL: `{{base_url}}/profile-analysis/results/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 4.10 Get Improvement Suggestions
**Request:**
- Method: `GET`
- URL: `{{base_url}}/profile-analysis/suggestions/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

---

## 5. Portfolio Analysis Testing

### 5.1 Start Portfolio Analysis
**Request:**
- Method: `POST`
- URL: `{{base_url}}/portfolio-analysis/analyze`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "portfolio_url": "https://example.com/portfolio"
}
```

**Expected Response:**
```json
{
  "message": "Portfolio analysis started",
  "user_id": "user_123",
  "task_id": "task_101",
  "status": "pending",
  "progress": 0
}
```

**Test Script:**
```javascript
pm.test("Portfolio analysis started", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property('task_id');
    pm.environment.set("portfolio_task_id", response.task_id);
});
```

### 5.2 Get Portfolio Status
**Request:**
- Method: `GET`
- URL: `{{base_url}}/portfolio-analysis/status/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 5.3 Get Portfolio Results
**Request:**
- Method: `GET`
- URL: `{{base_url}}/portfolio-analysis/results/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 5.4 Get Portfolio Suggestions
**Request:**
- Method: `GET`
- URL: `{{base_url}}/portfolio-analysis/suggestions/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 5.5 Get Extracted Data
**Request:**
- Method: `GET`
- URL: `{{base_url}}/portfolio-analysis/extracted-data/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 5.6 Reanalyze Portfolio
**Request:**
- Method: `POST`
- URL: `{{base_url}}/portfolio-analysis/reanalyze/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 5.7 Delete Portfolio Analysis
**Request:**
- Method: `DELETE`
- URL: `{{base_url}}/portfolio-analysis/delete/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

---

## 6. Task Management Testing

### 6.1 Get All Task Status
**Request:**
- Method: `GET`
- URL: `{{base_url}}/task/status/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

**Expected Response:**
```json
{
  "user_id": "user_123",
  "tasks": {
    "resume": {
      "task_id": "task_123",
      "status": "completed",
      "progress": 100,
      "created_at": "2024-01-01T10:00:00Z",
      "completed_at": "2024-01-01T10:05:00Z"
    },
    "linkedin": {
      "task_id": "task_456",
      "status": "processing",
      "progress": 60,
      "created_at": "2024-01-01T10:10:00Z"
    },
    "github": {
      "task_id": "task_789",
      "status": "pending",
      "progress": 0,
      "created_at": "2024-01-01T10:15:00Z"
    },
    "portfolio": {
      "task_id": "task_101",
      "status": "failed",
      "progress": 30,
      "error_message": "Invalid URL",
      "created_at": "2024-01-01T10:20:00Z"
    }
  }
}
```

### 6.2 Get Task Status by Type
**Request:**
- Method: `GET`
- URL: `{{base_url}}/task/status/{{user_id}}/resume`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 6.3 Cancel Task
**Request:**
- Method: `POST`
- URL: `{{base_url}}/task/cancel/{{resume_task_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

**Expected Response:**
```json
{
  "message": "Task cancelled successfully",
  "task_id": "task_123",
  "status": "cancelled"
}
```

### 6.4 Get Task History
**Request:**
- Method: `GET`
- URL: `{{base_url}}/task/history/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 6.5 Get Task Statistics
**Request:**
- Method: `GET`
- URL: `{{base_url}}/task/stats/{{user_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

**Expected Response:**
```json
{
  "user_id": "user_123",
  "statistics": {
    "total_tasks": 10,
    "completed_tasks": 7,
    "failed_tasks": 2,
    "cancelled_tasks": 1,
    "average_processing_time": "00:03:45",
    "success_rate": 70.0
  },
  "by_type": {
    "resume": {"total": 3, "completed": 2, "failed": 1},
    "linkedin": {"total": 3, "completed": 3, "failed": 0},
    "github": {"total": 2, "completed": 1, "failed": 1},
    "portfolio": {"total": 2, "completed": 1, "failed": 0}
  }
}
```

### 6.6 Cleanup Old Tasks
**Request:**
- Method: `POST`
- URL: `{{base_url}}/task/cleanup`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "days_old": 7
}
```

---

## 7. Community Testing

### 7.1 Create Post
**Request:**
- Method: `POST`
- URL: `{{base_url}}/community/posts`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "title": "Test Post Title",
  "content": "This is a test post content for the community platform.",
  "category": "general"
}
```

**Expected Response:**
```json
{
  "message": "Post created successfully",
  "post_id": "post_123",
  "title": "Test Post Title",
  "author": "user_123",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Test Script:**
```javascript
pm.test("Post created successfully", function () {
    pm.response.to.have.status(201);
    const response = pm.response.json();
    pm.expect(response).to.have.property('post_id');
    pm.environment.set("post_id", response.post_id);
});
```

### 7.2 Get Posts
**Request:**
- Method: `GET`
- URL: `{{base_url}}/community/posts`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
- Query Params:
  - `category`: `general`
  - `page`: `1`
  - `limit`: `10`

### 7.3 Get Post Details
**Request:**
- Method: `GET`
- URL: `{{base_url}}/community/posts/{{post_id}}`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

### 7.4 Create Comment
**Request:**
- Method: `POST`
- URL: `{{base_url}}/community/posts/{{post_id}}/comments`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
  - `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "content": "This is a test comment on the post."
}
```

### 7.5 Like/Unlike Post
**Request:**
- Method: `POST`
- URL: `{{base_url}}/community/posts/{{post_id}}/like`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`

---

## 8. Status Testing

### 8.1 API Status
**Request:**
- Method: `GET`
- URL: `{{base_url}}/status`
- Headers: None

**Expected Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

### 8.2 Health Check
**Request:**
- Method: `GET`
- URL: `http://localhost:5000/`
- Headers: None

**Expected Response:**
```json
{
  "message": "Skill Buddy Backend is running",
  "status": "healthy"
}
```

---

## 9. Error Testing

### 9.1 Test Invalid Authentication
**Request:**
- Method: `GET`
- URL: `{{base_url}}/user/profile/invalid_user_id`
- Headers: 
  - `X-User-ID: invalid_user_id`
  - `Authorization: Bearer invalid_token`

**Expected Response:**
```json
{
  "error": "Unauthorized",
  "details": "Invalid user ID or token"
}
```

### 9.2 Test Missing Required Fields
**Request:**
- Method: `POST`
- URL: `{{base_url}}/auth/register`
- Headers: `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "email": "test@example.com"
}
```

**Expected Response:**
```json
{
  "error": "Missing required fields",
  "details": "Password and name are required"
}
```

### 9.3 Test Invalid File Upload
**Request:**
- Method: `POST`
- URL: `{{base_url}}/resume/upload`
- Headers: 
  - `X-User-ID: {{user_id}}`
  - `Authorization: Bearer {{auth_token}}`
- Body: `form-data`
  - Key: `resume` (Type: File) - Select a non-PDF file

**Expected Response:**
```json
{
  "error": "Invalid file type",
  "details": "Only PDF files are allowed"
}
```

---

## 10. Parallel Processing Testing Scenarios

### 10.1 Concurrent Task Execution
1. Start resume upload
2. Start LinkedIn analysis
3. Start GitHub analysis
4. Start portfolio analysis
5. Check all task statuses simultaneously
6. Verify tasks run in parallel

### 10.2 Task Cancellation Testing
1. Start a long-running task
2. Cancel the task mid-execution
3. Verify task status changes to "cancelled"
4. Verify no further processing occurs

### 10.3 Progress Tracking Testing
1. Start a task
2. Poll status endpoint every 2 seconds
3. Verify progress percentage increases
4. Verify final status is "completed"

### 10.4 Error Recovery Testing
1. Start a task with invalid data
2. Verify task fails with error message
3. Retry with correct data
4. Verify task completes successfully

---

## 11. Performance Testing

### 11.1 Load Testing
1. Create multiple users
2. Start multiple tasks simultaneously
3. Monitor response times
4. Verify system stability

### 11.2 Stress Testing
1. Start maximum number of concurrent tasks
2. Monitor memory usage
3. Verify graceful degradation
4. Check error handling

---

## 12. Testing Checklist

### Authentication
- [ ] User registration
- [ ] User login
- [ ] Phone OTP send
- [ ] Phone OTP verify
- [ ] Invalid credentials handling

### User Management
- [ ] Get user profile
- [ ] Update user profile
- [ ] Get profile completion status
- [ ] Invalid user ID handling

### Resume Processing
- [ ] Resume upload
- [ ] Status checking
- [ ] Results retrieval
- [ ] Interview questions
- [ ] Job match analysis
- [ ] Resume listing
- [ ] Resume reprocessing
- [ ] Resume deletion
- [ ] Invalid file handling

### Profile Analysis
- [ ] LinkedIn analysis start
- [ ] LinkedIn status checking
- [ ] LinkedIn results retrieval
- [ ] LinkedIn reanalysis
- [ ] GitHub analysis start
- [ ] GitHub status checking
- [ ] GitHub results retrieval
- [ ] GitHub reanalysis
- [ ] Combined results
- [ ] Improvement suggestions

### Portfolio Analysis
- [ ] Portfolio analysis start
- [ ] Portfolio status checking
- [ ] Portfolio results retrieval
- [ ] Portfolio suggestions
- [ ] Extracted data
- [ ] Portfolio reanalysis
- [ ] Portfolio deletion

### Task Management
- [ ] Get all task status
- [ ] Get task status by type
- [ ] Cancel task
- [ ] Get task history
- [ ] Get task statistics
- [ ] Cleanup old tasks

### Community
- [ ] Create post
- [ ] Get posts
- [ ] Get post details
- [ ] Create comment
- [ ] Like/unlike post

### Status
- [ ] API status
- [ ] Health check

### Error Handling
- [ ] Invalid authentication
- [ ] Missing required fields
- [ ] Invalid file types
- [ ] Network errors
- [ ] Server errors

### Parallel Processing
- [ ] Concurrent task execution
- [ ] Task cancellation
- [ ] Progress tracking
- [ ] Error recovery
- [ ] Performance under load

---

## 13. Environment Variables Summary

After running all tests, your environment should contain:
- `base_url`: `http://localhost:5000/api`
- `user_id`: Generated user ID from registration
- `auth_token`: JWT token from login
- `resume_task_id`: Task ID from resume upload
- `linkedin_task_id`: Task ID from LinkedIn analysis
- `github_task_id`: Task ID from GitHub analysis
- `portfolio_task_id`: Task ID from portfolio analysis
- `post_id`: Post ID from community post creation

---

## 14. Troubleshooting

### Common Issues:
1. **Connection refused**: Ensure the Flask server is running
2. **401 Unauthorized**: Check user_id and auth_token are set correctly
3. **404 Not Found**: Verify the base_url is correct
4. **500 Internal Server Error**: Check server logs for detailed error messages
5. **Task not starting**: Verify the task manager service is properly initialized

### Debug Tips:
1. Use Postman's console to view request/response details
2. Check the Flask server logs for backend errors
3. Verify database connectivity
4. Test endpoints individually before running full test suite
5. Use environment variables to maintain state between requests 

---

## Additional User Endpoints

### Get/Update User Profile
**Request:**
- Method: `GET` or `PUT`
- URL: `{{base_url}}/user/profile`
- Headers: `X-User-ID: {{user_id}}`
- For PUT, Body (raw JSON):
```json
{
  "name": "Updated Name",
  "profession": "Engineer"
}
```
**Instructions:**
- Use GET to fetch, PUT to update profile fields.

### Update Profile Links
**Request:**
- Method: `PUT`
- URL: `{{base_url}}/user/profile/links`
- Headers: `X-User-ID: {{user_id}}`, `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "github_link": "https://github.com/username",
  "linkedin_link": "https://linkedin.com/in/username"
}
```

### Get Profile Completion
**Request:**
- Method: `GET`
- URL: `{{base_url}}/user/profile/completion`
- Headers: `X-User-ID: {{user_id}}`

### Get/Update User Settings
**Request:**
- Method: `GET` or `PUT`
- URL: `{{base_url}}/user/settings`
- Headers: `X-User-ID: {{user_id}}`
- For PUT, Body (raw JSON):
```json
{
  "notifications": true,
  "email_updates": false
}
```

### Get User XP
**Request:**
- Method: `GET`
- URL: `{{base_url}}/user/xp`
- Headers: `X-User-ID: {{user_id}}`

### Get SSO Data
**Request:**
- Method: `GET`
- URL: `{{base_url}}/user/sso/linkedin/data` or `/user/sso/github/data` or `/user/sso/data/export`
- Headers: `X-User-ID: {{user_id}}`

### Get All User Data
**Request:**
- Method: `GET`
- URL: `{{base_url}}/user/all-data` or `/user/all-data/summary`
- Headers: `X-User-ID: {{user_id}}`
- **Instructions:** Use `/user/all-data` for full data, `/user/all-data/summary` for dashboard summary.

---

## Additional Profile Analysis Endpoints

### Quick Analyze Both Profiles
**Request:**
- Method: `POST`
- URL: `{{base_url}}/profile-analysis/quick-analyze`
- Headers: `X-User-ID: {{user_id}}`

### Delete Analyses
**Request:**
- Method: `DELETE`
- URL: `{{base_url}}/profile-analysis/delete/{{user_id}}`
- Headers: `X-User-ID: {{user_id}}`
- Body (optional, raw JSON):
```json
{
  "analysis_type": "linkedin"
}
```

---

## Additional Portfolio Analysis Endpoints

### Get Extracted Portfolio Data
**Request:**
- Method: `GET`
- URL: `{{base_url}}/portfolio-analysis/extracted-data/{{user_id}}`
- Headers: `X-User-ID: {{user_id}}`

### Delete Portfolio Analysis
**Request:**
- Method: `DELETE`
- URL: `{{base_url}}/portfolio-analysis/delete/{{user_id}}`
- Headers: `X-User-ID: {{user_id}}`

---

## Additional Community Endpoints

### Add Reply to Post
**Request:**
- Method: `POST`
- URL: `{{base_url}}/community/posts/{{post_id}}/replies`
- Headers: `X-User-ID: {{user_id}}`, `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "text": "This is a reply."
}
```

### Get Replies for Post
**Request:**
- Method: `GET`
- URL: `{{base_url}}/community/posts/{{post_id}}/replies`
- Headers: `X-User-ID: {{user_id}}`

### Delete Reply
**Request:**
- Method: `DELETE`
- URL: `{{base_url}}/community/posts/{{post_id}}/replies/{{reply_id}}`
- Headers: `X-User-ID: {{user_id}}`

### Get My Posts
**Request:**
- Method: `GET`
- URL: `{{base_url}}/community/my-posts`
- Headers: `X-User-ID: {{user_id}}`

### Get Community Stats
**Request:**
- Method: `GET`
- URL: `{{base_url}}/community/stats`
- Headers: `X-User-ID: {{user_id}}`

### Search Posts
**Request:**
- Method: `GET`
- URL: `{{base_url}}/community/search?q=search_term`
- Headers: `X-User-ID: {{user_id}}`

### Get Trending Posts
**Request:**
- Method: `GET`
- URL: `{{base_url}}/community/trending`
- Headers: `X-User-ID: {{user_id}}`

---

## Additional Task Management Endpoints

### Get Task Status by Type
**Request:**
- Method: `GET`
- URL: `{{base_url}}/task/status/{{user_id}}/{{task_type}}`
- Headers: `X-User-ID: {{user_id}}`

### Cancel Task
**Request:**
- Method: `POST`
- URL: `{{base_url}}/task/cancel/{{task_id}}`
- Headers: `X-User-ID: {{user_id}}`

### Cleanup Old Tasks
**Request:**
- Method: `POST`
- URL: `{{base_url}}/task/cleanup`
- Headers: `X-User-ID: {{user_id}}`, `Content-Type: application/json`
- Body (raw JSON):
```json
{
  "days_old": 7
}
```

### Get Task Statistics
**Request:**
- Method: `GET`
- URL: `{{base_url}}/task/stats/{{user_id}}`
- Headers: `X-User-ID: {{user_id}}`

---

## Additional SSO Endpoints

### Get SSO Status
**Request:**
- Method: `GET`
- URL: `{{base_url}}/auth/sso/status`

### Disconnect SSO Provider
**Request:**
- Method: `POST`
- URL: `{{base_url}}/auth/sso/disconnect/{{provider}}`
- Headers: `X-User-ID: {{user_id}}`
- Body (raw JSON, optional):
```json
{
  "provider": "github"
}
```

---

# Tips
- For all endpoints, set `X-User-ID` header if required.
- For file uploads, use `form-data` and select the file type.
- For SSO, follow the OAuth flow: get the auth URL, complete in browser, use code/state in callback.
- Use Postman collections to organize requests by feature. 