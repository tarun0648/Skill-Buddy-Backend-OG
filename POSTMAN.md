# Postman Testing Guide - Skill Buddy API

This comprehensive guide covers all API endpoints for the Skill Buddy application with step-by-step Postman testing instructions.

## Table of Contents

1. [Initial Setup](#initial-setup)
2. [Environment Variables](#environment-variables)
3. [Authentication Flow](#authentication-flow)
4. [Status & Health Endpoints](#status--health-endpoints)
5. [User Management](#user-management)
6. [Resume Processing](#resume-processing)
7. [Profile Analysis](#profile-analysis)
8. [Portfolio Analysis](#portfolio-analysis)
9. [Community Features](#community-features)
10. [Interview System](#interview-system)
11. [JD-based Interviews](#jd-based-interviews)
12. [Task Management](#task-management)
13. [Debug Endpoints](#debug-endpoints)
14. [Testing Scenarios](#testing-scenarios)

---

## Initial Setup

### Base URL Configuration
- **Local Development**: `http://localhost:5000`
- **Production**: `https://your-domain.com`

### Postman Collection Setup
1. Create a new Postman Collection named "Skill Buddy API"
2. Set up the base URL as a collection variable
3. Import the environment variables listed below

---

## Environment Variables

Create a Postman Environment with these variables:

```json
{
  "base_url": "http://localhost:5000",
  "user_id": "",
  "auth_token": "",
  "linkedin_url": "",
  "github_username": "",
  "portfolio_url": "",
  "phone_number": "",
  "otp_code": "",
  "task_id": "",
  "session_id": "",
  "thread_id": "",
  "post_id": "",
  "reply_id": ""
}
```

---

## Authentication Flow

### 1. User Registration (Email/Password)

**Endpoint**: `POST {{base_url}}/api/auth/register`

**Headers**:
```
Content-Type: application/json
```

**Body** (JSON):
```json
{
  "email": "test@example.com",
  "password": "SecurePassword123!",
  "name": "Test User"
}
```

**Expected Response**:
```json
{
  "message": "User registered successfully",
  "user_id": "user_123456",
  "user": {
    "id": "user_123456",
    "email": "test@example.com",
    "profile": {}
  },
  "email_sent": true
}
```

**Post-Response Script**:
```javascript
if (pm.response.code === 201) {
    const responseJson = pm.response.json();
    pm.environment.set("user_id", responseJson.user_id);
}
```

### 2. User Login (Email/Password)

**Endpoint**: `POST {{base_url}}/api/auth/login`

**Headers**:
```
Content-Type: application/json
```

**Body** (JSON):
```json
{
  "email": "test@example.com",
  "password": "SecurePassword123!"
}
```

**Expected Response**:
```json
{
  "message": "Login successful",
  "user_id": "user_123456",
  "user": {
    "id": "user_123456",
    "email": "test@example.com",
    "profile": {}
  }
}
```

### 3. Phone OTP Registration/Login Flow

#### Step 3a: Send OTP for Signup
**Endpoint**: `POST {{base_url}}/api/auth/phone/send-otp`

**Body** (JSON):
```json
{
  "phone": "+1234567890",
  "purpose": "signup",
  "method": "sms"
}
```

#### Step 3b: Verify OTP for Signup
**Endpoint**: `POST {{base_url}}/api/auth/phone/verify-otp`

**Body** (JSON):
```json
{
  "phone": "+1234567890",
  "otp": "123456",
  "purpose": "signup",
  "name": "Phone User"
}
```

#### Step 3c: Send OTP for Login
**Endpoint**: `POST {{base_url}}/api/auth/phone/send-otp`

**Body** (JSON):
```json
{
  "phone": "+1234567890",
  "purpose": "login",
  "method": "sms"
}
```

#### Step 3d: Verify OTP for Login
**Endpoint**: `POST {{base_url}}/api/auth/phone/verify-otp`

**Body** (JSON):
```json
{
  "phone": "+1234567890",
  "otp": "123456",
  "purpose": "login"
}
```

### 4. SSO Authentication

#### LinkedIn SSO
**Endpoint**: `POST {{base_url}}/api/auth/sso/linkedin/authorize`

**Body** (JSON):
```json
{
  "email": "user@example.com",
  "fetch_data": true
}
```

#### GitHub SSO
**Endpoint**: `POST {{base_url}}/api/auth/sso/github/authorize`

**Body** (JSON):
```json
{
  "email": "user@example.com",
  "fetch_data": true
}
```

---

## Status & Health Endpoints

### 1. Health Check
**Endpoint**: `GET {{base_url}}/`

**Expected Response**: API status and feature overview

### 2. API Status
**Endpoint**: `GET {{base_url}}/api/status`

**Expected Response**: Comprehensive system status

### 3. Health Check
**Endpoint**: `GET {{base_url}}/api/status/health`

### 4. Ping
**Endpoint**: `GET {{base_url}}/api/status/ping`

### 5. Readiness Check
**Endpoint**: `GET {{base_url}}/api/status/ready`

---

## User Management

**All user endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### 1. Get User Profile
**Endpoint**: `GET {{base_url}}/api/user/profile`

### 2. Update User Profile
**Endpoint**: `PUT {{base_url}}/api/user/profile`

**Body** (JSON):
```json
{
  "name": "Updated Name",
  "profession": "Student",
  "career_choices": ["Software Engineering", "Data Science"],
  "college_name": "Test University",
  "college_email": "student@university.edu",
  "github_link": "https://github.com/username",
  "linkedin_link": "https://linkedin.com/in/username"
}
```

### 3. Get User Settings
**Endpoint**: `GET {{base_url}}/api/user/settings`

### 4. Update User Settings
**Endpoint**: `PUT {{base_url}}/api/user/settings`

**Body** (JSON):
```json
{
  "notifications": true,
  "email_updates": false,
  "privacy_level": "normal"
}
```

### 5. Get Profile Completion Status
**Endpoint**: `GET {{base_url}}/api/user/profile/completion`

### 6. Update Profile Links
**Endpoint**: `PUT {{base_url}}/api/user/profile/links`

**Body** (JSON):
```json
{
  "github_link": "https://github.com/newusername",
  "linkedin_link": "https://linkedin.com/in/newusername"
}
```

### 7. Get User XP
**Endpoint**: `GET {{base_url}}/api/user/xp`

### 8. Get User Resumes
**Endpoint**: `GET {{base_url}}/api/user/resumes?details=true&limit=10`

### 9. Get All User Data
**Endpoint**: `GET {{base_url}}/api/user/all-data?include_resumes=true&include_profile_analyses=true`

### 10. Get User Data Summary
**Endpoint**: `GET {{base_url}}/api/user/all-data/summary`

---

## Resume Processing

**All resume endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### 1. Upload Resume
**Endpoint**: `POST {{base_url}}/api/resume/upload`

**Headers**:
```
X-User-ID: {{user_id}}
Content-Type: multipart/form-data
```

**Body** (form-data):
- Key: `resume` (File) - Upload a PDF file
- Key: `job_description` (Text) - Optional job description

**Post-Response Script**:
```javascript
if (pm.response.code === 201) {
    const responseJson = pm.response.json();
    pm.environment.set("task_id", responseJson.task_id);
}
```

### 2. Get Processing Status
**Endpoint**: `GET {{base_url}}/api/resume/status/{{user_id}}`

### 3. Get Resume Results
**Endpoint**: `GET {{base_url}}/api/resume/results/{{user_id}}`

### 4. Get Interview Questions
**Endpoint**: `GET {{base_url}}/api/resume/questions/{{user_id}}`

### 5. Get Job Match Analysis
**Endpoint**: `GET {{base_url}}/api/resume/analysis/{{user_id}}`

### 6. Reprocess Resume
**Endpoint**: `POST {{base_url}}/api/resume/reprocess/{{user_id}}`

**Body** (JSON):
```json
{
  "job_description": "New job description for reprocessing"
}
```

### 7. Delete Resume
**Endpoint**: `DELETE {{base_url}}/api/resume/delete/{{user_id}}`

### 8. Get User Resume List
**Endpoint**: `GET {{base_url}}/api/resume/list/{{user_id}}`

---

## Profile Analysis

**All profile analysis endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### LinkedIn Profile Analysis

### 1. Analyze LinkedIn Profile
**Endpoint**: `POST {{base_url}}/api/profile-analysis/analyze/linkedin`

**Body** (JSON):
```json
{
  "linkedin_url": "https://linkedin.com/in/username"
}
```

**Post-Response Script**:
```javascript
if (pm.response.code === 200) {
    const responseJson = pm.response.json();
    pm.environment.set("task_id", responseJson.task_id);
}
```

### 2. Get LinkedIn Analysis Status
**Endpoint**: `GET {{base_url}}/api/profile-analysis/status/linkedin/{{user_id}}`

### 3. Get LinkedIn Results
**Endpoint**: `GET {{base_url}}/api/profile-analysis/results/linkedin/{{user_id}}`

### 4. Reanalyze LinkedIn
**Endpoint**: `POST {{base_url}}/api/profile-analysis/reanalyze/linkedin/{{user_id}}`

### GitHub Profile Analysis

### 5. Analyze GitHub Profile
**Endpoint**: `POST {{base_url}}/api/profile-analysis/analyze/github`

**Body** (JSON):
```json
{
  "github_username": "username"
}
```

### 6. Get GitHub Analysis Status
**Endpoint**: `GET {{base_url}}/api/profile-analysis/status/github/{{user_id}}`

### 7. Get GitHub Results
**Endpoint**: `GET {{base_url}}/api/profile-analysis/results/github/{{user_id}}`

### 8. Reanalyze GitHub
**Endpoint**: `POST {{base_url}}/api/profile-analysis/reanalyze/github/{{user_id}}`

### Combined Analysis

### 9. Get All Analysis Results
**Endpoint**: `GET {{base_url}}/api/profile-analysis/results/{{user_id}}`

### 10. Get Improvement Suggestions
**Endpoint**: `GET {{base_url}}/api/profile-analysis/suggestions/{{user_id}}`

### 11. Quick Analyze Both Profiles
**Endpoint**: `POST {{base_url}}/api/profile-analysis/quick-analyze`

### 12. Delete Analysis
**Endpoint**: `DELETE {{base_url}}/api/profile-analysis/delete/{{user_id}}`

**Body** (JSON):
```json
{
  "analysis_type": "linkedin"
}
```

---

## Portfolio Analysis

**All portfolio analysis endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### 1. Analyze Portfolio
**Endpoint**: `POST {{base_url}}/api/portfolio-analysis/analyze`

**Body** (JSON):
```json
{
  "portfolio_url": "https://yourportfolio.com"
}
```

**Post-Response Script**:
```javascript
if (pm.response.code === 200) {
    const responseJson = pm.response.json();
    pm.environment.set("task_id", responseJson.task_id);
}
```

### 2. Get Portfolio Analysis Status
**Endpoint**: `GET {{base_url}}/api/portfolio-analysis/status/{{user_id}}`

### 3. Get Portfolio Results
**Endpoint**: `GET {{base_url}}/api/portfolio-analysis/results/{{user_id}}`

### 4. Get Portfolio Suggestions
**Endpoint**: `GET {{base_url}}/api/portfolio-analysis/suggestions/{{user_id}}`

### 5. Reanalyze Portfolio
**Endpoint**: `POST {{base_url}}/api/portfolio-analysis/reanalyze/{{user_id}}`

### 6. Delete Portfolio Analysis
**Endpoint**: `DELETE {{base_url}}/api/portfolio-analysis/delete/{{user_id}}`

### 7. Get Extracted Portfolio Data
**Endpoint**: `GET {{base_url}}/api/portfolio-analysis/extracted-data/{{user_id}}`

---

## Community Features

**All community endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### 1. Create Post
**Endpoint**: `POST {{base_url}}/api/community/posts`

**Body** (JSON):
```json
{
  "content": "This is my first community post! Excited to be here."
}
```

**Post-Response Script**:
```javascript
if (pm.response.code === 201) {
    const responseJson = pm.response.json();
    pm.environment.set("post_id", responseJson.data.id);
}
```

### 2. Get All Posts
**Endpoint**: `GET {{base_url}}/api/community/posts?limit=20&page=1`

### 3. Get Specific Post
**Endpoint**: `GET {{base_url}}/api/community/posts/{{post_id}}`

### 4. Like/Unlike Post
**Endpoint**: `POST {{base_url}}/api/community/posts/{{post_id}}/like`

### 5. Add Reply to Post
**Endpoint**: `POST {{base_url}}/api/community/posts/{{post_id}}/replies`

**Body** (JSON):
```json
{
  "text": "Great post! Thanks for sharing."
}
```

**Post-Response Script**:
```javascript
if (pm.response.code === 201) {
    const responseJson = pm.response.json();
    pm.environment.set("reply_id", responseJson.data.reply.id);
}
```

### 6. Get Post Replies
**Endpoint**: `GET {{base_url}}/api/community/posts/{{post_id}}/replies`

### 7. Delete Post
**Endpoint**: `DELETE {{base_url}}/api/community/posts/{{post_id}}`

### 8. Delete Reply
**Endpoint**: `DELETE {{base_url}}/api/community/posts/{{post_id}}/replies/{{reply_id}}`

### 9. Get My Posts
**Endpoint**: `GET {{base_url}}/api/community/my-posts`

### 10. Get Community Stats
**Endpoint**: `GET {{base_url}}/api/community/stats`

### 11. Search Posts
**Endpoint**: `GET {{base_url}}/api/community/search?q=javascript&limit=10`

### 12. Get Trending Posts
**Endpoint**: `GET {{base_url}}/api/community/trending?limit=10&days=7`

---

## Interview System

**All interview endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### 1. Start Interview Session
**Endpoint**: `POST {{base_url}}/api/interview/start-session`

**Post-Response Script**:
```javascript
if (pm.response.code === 200) {
    const responseJson = pm.response.json();
    pm.environment.set("thread_id", responseJson.thread_id);
}
```

### 2. Get First Question
**Endpoint**: `POST {{base_url}}/api/interview/first-question`

**Body** (JSON):
```json
{
  "role": "Software Engineer",
  "level": "junior",
  "topic": "JavaScript"
}
```

### 3. Get Next Question
**Endpoint**: `POST {{base_url}}/api/interview/next-question`

**Body** (JSON):
```json
{
  "thread_id": "{{thread_id}}",
  "role": "Software Engineer",
  "level": "junior",
  "topic": "JavaScript",
  "last_question": "Tell me about your experience with JavaScript",
  "last_answer": "I have 2 years of experience working with JavaScript...",
  "answer_feedback": "Good response",
  "answer_history": "Previous answers context",
  "session_id": "{{session_id}}",
  "interview_round": 2
}
```

### 4. Upload Video Response
**Endpoint**: `POST {{base_url}}/api/interview/upload-video`

**Headers**:
```
X-User-ID: {{user_id}}
Content-Type: multipart/form-data
```

**Body** (form-data):
- Key: `video` (File) - Upload video file
- Key: `question_id` (Text) - "1"
- Key: `session_id` (Text) - "{{session_id}}"

### 5. Save Interview Summary
**Endpoint**: `POST {{base_url}}/api/interview/save-summary`

**Body** (JSON):
```json
{
  "session_id": "{{session_id}}",
  "role": "Software Engineer",
  "level": "junior",
  "topic": "JavaScript",
  "total_questions": 5,
  "completion_status": "completed",
  "summary": "Interview completed successfully"
}
```

### 6. Get Interview History
**Endpoint**: `GET {{base_url}}/api/interview/history?session_id={{session_id}}`

### 7. Get Available Topics
**Endpoint**: `GET {{base_url}}/api/interview/questions/topics?role=Software Engineer&level=junior`

### 8. Get Questions Count
**Endpoint**: `GET {{base_url}}/api/interview/questions/count?role=Software Engineer&level=junior&topic=JavaScript`

### 9. Get All User Interview Data
**Endpoint**: `GET {{base_url}}/api/interview/user/all-data?limit=100`

---

## JD-based Interviews

**All JD interview endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### 1. Analyze Job Description
**Endpoint**: `POST {{base_url}}/api/jd-interview/analyze`

**Body** (JSON):
```json
{
  "job_description": "We are looking for a Senior Software Engineer with 5+ years of experience in React, Node.js, and AWS. The candidate should have experience with microservices architecture and be comfortable working in an agile environment."
}
```

### 2. Get First JD Question
**Endpoint**: `POST {{base_url}}/api/jd-interview/first-question`

**Body** (JSON):
```json
{
  "extracted_data": {
    "role": "Senior Software Engineer",
    "experience_level": "5+ years",
    "required_skills": ["React", "Node.js", "AWS"],
    "preferred_skills": ["microservices", "agile"]
  }
}
```

### 3. Get Next JD Question
**Endpoint**: `POST {{base_url}}/api/jd-interview/next-question`

**Body** (JSON):
```json
{
  "extracted_data": {
    "role": "Senior Software Engineer",
    "experience_level": "5+ years",
    "required_skills": ["React", "Node.js", "AWS"]
  },
  "last_question": "Tell me about your experience with React",
  "last_answer": "I have 6 years of experience with React...",
  "answer_history": "Previous context",
  "interview_round": 2,
  "used_questions": ["react_experience"],
  "session_id": "{{session_id}}"
}
```

### 4. Get JD Interview History
**Endpoint**: `GET {{base_url}}/api/jd-interview/history?session_id={{session_id}}`

### 5. Get Matching Questions
**Endpoint**: `POST {{base_url}}/api/jd-interview/matching-questions`

**Body** (JSON):
```json
{
  "extracted_data": {
    "role": "Software Engineer",
    "required_skills": ["JavaScript", "Python"]
  },
  "num_questions": 5
}
```

### 6. Generate Custom Question
**Endpoint**: `POST {{base_url}}/api/jd-interview/generate-custom`

**Body** (JSON):
```json
{
  "extracted_data": {
    "role": "Software Engineer",
    "required_skills": ["React", "Node.js"]
  },
  "last_answer": "Previous answer context",
  "answer_history": "Interview history",
  "question_type": "technical"
}
```

### 7. Assess Skills
**Endpoint**: `POST {{base_url}}/api/jd-interview/skills-assessment`

**Body** (JSON):
```json
{
  "extracted_data": {
    "role": "Software Engineer",
    "required_skills": ["React", "Node.js"]
  },
  "interview_history": [
    {
      "question": "React experience",
      "answer": "5 years experience"
    }
  ]
}
```

### 8. Calculate Compatibility Score
**Endpoint**: `POST {{base_url}}/api/jd-interview/compatibility-score`

**Body** (JSON):
```json
{
  "extracted_data": {
    "role": "Software Engineer",
    "required_skills": ["React", "Node.js"]
  },
  "candidate_responses": [
    {
      "skill": "React",
      "response": "Expert level",
      "score": 9
    }
  ]
}
```

---

## Task Management

**All task endpoints require authentication header**:
```
X-User-ID: {{user_id}}
```

### 1. Get All Task Status
**Endpoint**: `GET {{base_url}}/api/task/status/{{user_id}}`

### 2. Get Task Status by Type
**Endpoint**: `GET {{base_url}}/api/task/status/{{user_id}}/resume`

**Available types**: `resume`, `linkedin`, `github`, `portfolio`

### 3. Cancel Task
**Endpoint**: `POST {{base_url}}/api/task/cancel/{{task_id}}`

### 4. Get Task History
**Endpoint**: `GET {{base_url}}/api/task/history/{{user_id}}`

### 5. Get Task Stats
**Endpoint**: `GET {{base_url}}/api/task/stats/{{user_id}}`

### 6. Cleanup Old Tasks
**Endpoint**: `POST {{base_url}}/api/task/cleanup`

**Body** (JSON):
```json
{
  "days_old": 7
}
```

---

## Debug Endpoints

### 1. Test Authentication
**Endpoint**: `GET {{base_url}}/api/test-auth`

**Headers**:
```
X-User-ID: {{user_id}}
```

### 2. Test Interview System
**Endpoint**: `GET {{base_url}}/api/test-interview-system`

**Headers**:
```
X-User-ID: {{user_id}}
```

### 3. Test OTP Service
**Endpoint**: `GET {{base_url}}/api/test-otp-service`

**Headers**:
```
X-User-ID: {{user_id}}
```

### 4. Test Community Platform
**Endpoint**: `GET {{base_url}}/api/test-community`

**Headers**:
```
X-User-ID: {{user_id}}
```

### 5. Test Profile Analysis
**Endpoint**: `GET {{base_url}}/api/test-profile-analysis`

**Headers**:
```
X-User-ID: {{user_id}}
```

### 6. Debug Profile Completion
**Endpoint**: `GET {{base_url}}/api/debug/profile-completion/{{user_id}}`

### 7. Debug Interview System
**Endpoint**: `GET {{base_url}}/api/debug/interview-system`

### 8. Debug Email Configuration
**Endpoint**: `GET {{base_url}}/api/debug/email-config`

### 9. Test Email Connection
**Endpoint**: `POST {{base_url}}/api/debug/test-email-connection`

### 10. Send Test Email
**Endpoint**: `POST {{base_url}}/api/debug/send-test-email`

**Body** (JSON):
```json
{
  "email": "test@example.com"
}
```

---

## Testing Scenarios

### Complete User Journey

#### Scenario 1: New User Registration and Profile Setup

1. **Register User** - `POST /api/auth/register`
2. **Get Profile** - `GET /api/user/profile`
3. **Update Profile** - `PUT /api/user/profile`
4. **Check Completion** - `GET /api/user/profile/completion`
5. **Upload Resume** - `POST /api/resume/upload`
6. **Check Processing** - `GET /api/resume/status/{user_id}`
7. **Get Results** - `GET /api/resume/results/{user_id}`

#### Scenario 2: Profile Analysis Workflow

1. **Login User** - `POST /api/auth/login`
2. **Analyze LinkedIn** - `POST /api/profile-analysis/analyze/linkedin`
3. **Check Status** - `GET /api/profile-analysis/status/linkedin/{user_id}`
4. **Get Results** - `GET /api/profile-analysis/results/linkedin/{user_id}`
5. **Analyze GitHub** - `POST /api/profile-analysis/analyze/github`
6. **Get Combined Results** - `GET /api/profile-analysis/results/{user_id}`

#### Scenario 3: Interview Experience

1. **Start Session** - `POST /api/interview/start-session`
2. **Get First Question** - `POST /api/interview/first-question`
3. **Get Next Questions** - `POST /api/interview/next-question` (repeat)
4. **Upload Video** - `POST /api/interview/upload-video`
5. **Save Summary** - `POST /api/interview/save-summary`
6. **Get History** - `GET /api/interview/history`

#### Scenario 4: Community Engagement

1. **Create Post** - `POST /api/community/posts`
2. **Get All Posts** - `GET /api/community/posts`
3. **Like Post** - `POST /api/community/posts/{post_id}/like`
4. **Add Reply** - `POST /api/community/posts/{post_id}/replies`
5. **Get My Posts** - `GET /api/community/my-posts`

### Error Testing

#### Test Invalid Authentication
- Send requests without `X-User-ID` header
- Use invalid user IDs
- Expected: 401 Unauthorized

#### Test Invalid Data
- Send malformed JSON
- Send missing required fields
- Send invalid email formats
- Expected: 400 Bad Request

#### Test Non-existent Resources
- Access posts/users that don't exist
- Expected: 404 Not Found

### Performance Testing

#### Rate Limiting Test
- Send rapid requests to test rate limiting
- Expected: 429 Too Many Requests after threshold

#### Large File Upload Test
- Upload large resume files (>10MB)
- Expected: 400 Bad Request with file size error

---

## Environment-Specific Testing

### Development Environment
```
base_url: http://localhost:5000
```

### Production Environment
```
base_url: https://your-production-domain.com
```

### Environment Variables to Set

For comprehensive testing, ensure these environment variables are configured on your server:

**Required for Core Features:**
- `FIREBASE_CREDENTIALS` - Firebase service account
- `SECRET_KEY` - Flask secret key

**Required for Resume Processing:**
- `CLAUDE_API_KEY` - Anthropic Claude API

**Required for Profile Analysis:**
- `CLAUDE_API_KEY` - Anthropic Claude API
- `GITHUB_TOKEN` - GitHub personal access token

**Required for Interview System:**
- `OPENAI_API_KEY` - OpenAI API key
- `OPENAI_ASSISTANT_ID` - OpenAI Assistant ID

**Required for Email Features:**
- `SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`
- `FROM_EMAIL`, `FROM_NAME`

**Required for OTP Features:**
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- Or `SMS_API_KEY`, `SMS_SENDER_ID`, `MSG91_FLOW_ID`
- For WhatsApp: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_ID`

---

## Common Response Codes

- **200 OK** - Success
- **201 Created** - Resource created successfully
- **400 Bad Request** - Invalid request data
- **401 Unauthorized** - Missing or invalid authentication
- **403 Forbidden** - Access denied
- **404 Not Found** - Resource not found
- **409 Conflict** - Resource already exists
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

---

## Tips for Effective Testing

1. **Use Environment Variables**: Store frequently used values like `user_id`, `task_id`, etc.

2. **Create Test Collections**: Organize endpoints into logical collections (Auth, User Management, etc.)

3. **Use Pre-request Scripts**: Set up authentication headers automatically

4. **Use Post-response Scripts**: Extract and store IDs for chaining requests

5. **Test Error Cases**: Don't just test happy paths

6. **Monitor Performance**: Check response times and file upload speeds

7. **Test Rate Limiting**: Ensure your API handles high traffic appropriately

8. **Validate Data**: Check that returned data matches expected schema

This guide provides a comprehensive testing framework for the entire Skill Buddy API. Start with basic authentication and gradually work through each feature area to ensure everything is working correctly.