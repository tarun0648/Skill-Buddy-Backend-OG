# Skill Buddy API - Complete Endpoint Reference

## Overview
This is a comprehensive reference of all 85+ API endpoints available in the Skill Buddy application. The API includes authentication, user management, profile analysis, resume processing, community features, and debugging tools.

## Base URL
```
http://localhost:5000/api
```

## Authentication Header
Most endpoints require user authentication. Add this header to authenticated requests:
```
X-User-ID: your-user-id-here
```

---

## 1. Authentication Endpoints (/api/auth)

### 1.1 User Registration
- **Method:** `POST`
- **URL:** `{{baseURL}}/auth/register`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe"
}
```
- **Expected Response:** `201 Created`
- **Notes:** Name is optional, only email and password are required

### 1.2 User Login
- **Method:** `POST`
- **URL:** `{{baseURL}}/auth/login`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```
- **Expected Response:** `200 OK` with user data and user_id

### 1.3 Google SSO Login
- **Method:** `POST`
- **URL:** `{{baseURL}}/auth/google-login`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "google_token": "google-oauth-token-here"
}
```
- **Expected Response:** `200 OK`

### 1.4 Change Password
- **Method:** `POST`
- **URL:** `{{baseURL}}/auth/change-password`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "current_password": "CurrentPassword123!",
  "new_password": "NewPassword123!"
}
```
- **Expected Response:** `200 OK`

### 1.5 Forgot Password
- **Method:** `POST`
- **URL:** `{{baseURL}}/auth/forgot-password`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "email": "user@example.com"
}
```
- **Expected Response:** `200 OK`

### 1.6 Reset Password
- **Method:** `POST`
- **URL:** `{{baseURL}}/auth/reset-password`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "token": "reset-token-from-email",
  "new_password": "NewPassword123!"
}
```
- **Expected Response:** `200 OK`

### 1.7 Test Email
- **Method:** `POST`
- **URL:** `{{baseURL}}/auth/test-email`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "email": "test@example.com"
}
```
- **Expected Response:** `200 OK`

---

## 2. User Profile Endpoints

### 2.1 Get User Profile
- **Method:** `GET`
- **URL:** `{{baseURL}}/user/profile`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with complete user profile

### 2.2 Update User Profile
- **Method:** `PUT`
- **URL:** `{{baseURL}}/user/profile`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "name": "Updated Name",
  "profession": "Student",
  "career_choices": ["Software Engineering", "Data Science"],
  "college_name": "University Name",
  "college_email": "student@university.edu",
  "github_link": "https://github.com/username",
  "linkedin_link": "https://linkedin.com/in/username",
  "phone": "+1234567890"
}
```
- **Expected Response:** `200 OK`

### 2.3 Delete User Profile
- **Method:** `DELETE`
- **URL:** `{{baseURL}}/user/profile`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK`

### 2.4 Get User Stats
- **Method:** `GET`
- **URL:** `{{baseURL}}/user/stats`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with user statistics

---

## 3. Resume Processing Endpoints (/api/resume)

### 3.1 Upload Resume
- **Method:** `POST`
- **URL:** `{{baseURL}}/resume/upload`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Body:** 
  - Type: `form-data`
  - Key: `resume` (Type: File)
  - Value: Select PDF file
- **Expected Response:** `201 Created`

### 3.2 Get Processing Status
- **Method:** `GET`
- **URL:** `{{baseURL}}/resume/status/{resume_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with processing status

### 3.3 Get Resume Results
- **Method:** `GET`
- **URL:** `{{baseURL}}/resume/results/{resume_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with complete results

### 3.4 Get Interview Questions
- **Method:** `GET`
- **URL:** `{{baseURL}}/resume/questions/{resume_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with generated questions

### 3.5 Get Job Match Analysis
- **Method:** `GET`
- **URL:** `{{baseURL}}/resume/analysis/{resume_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with job match analysis

### 3.6 Reprocess Resume
- **Method:** `POST`
- **URL:** `{{baseURL}}/resume/reprocess/{resume_id}`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "job_description": "Optional job description for targeted analysis"
}
```
- **Expected Response:** `200 OK`

### 3.7 Delete Resume
- **Method:** `DELETE`
- **URL:** `{{baseURL}}/resume/delete/{resume_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK`

### 3.8 Get User Resumes
- **Method:** `GET`
- **URL:** `{{baseURL}}/user/resumes`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Query Parameters:**
  - `details`: true/false (include full details)
  - `limit`: number (pagination limit)
- **Expected Response:** `200 OK` with resumes list

---

## 4. Profile Analysis Endpoints (/api/profile-analysis)

### 4.1 Analyze LinkedIn Profile
- **Method:** `POST`
- **URL:** `{{baseURL}}/profile-analysis/linkedin`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "linkedin_url": "https://linkedin.com/in/username"
}
```
- **Expected Response:** `200 OK`

### 4.2 Analyze GitHub Profile
- **Method:** `POST`
- **URL:** `{{baseURL}}/profile-analysis/github`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "github_url": "https://github.com/username"
}
```
- **Expected Response:** `200 OK`

### 4.3 Get Analysis Results
- **Method:** `GET`
- **URL:** `{{baseURL}}/profile-analysis/results`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with analysis results

### 4.4 Get Analysis by ID
- **Method:** `GET`
- **URL:** `{{baseURL}}/profile-analysis/results/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with specific analysis

### 4.5 Get All User Analyses
- **Method:** `GET`
- **URL:** `{{baseURL}}/profile-analysis/analyses`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with all user analyses

### 4.6 Re-analyze Profile
- **Method:** `POST`
- **URL:** `{{baseURL}}/profile-analysis/reanalyze/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK`

### 4.7 Delete Analysis
- **Method:** `DELETE`
- **URL:** `{{baseURL}}/profile-analysis/delete/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK`

### 4.8 Quick Analyze (LinkedIn + GitHub)
- **Method:** `POST`
- **URL:** `{{baseURL}}/profile-analysis/quick-analyze`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK`

### 4.9 Get Improvement Suggestions
- **Method:** `GET`
- **URL:** `{{baseURL}}/profile-analysis/suggestions/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with detailed improvement suggestions
- **Response includes:**
  - Improvement suggestions
  - Career-specific advice
  - Project recommendations
  - Skill development tips

---

## 5. Portfolio Analysis Endpoints (/api/portfolio-analysis)

### 5.1 Analyze Portfolio Website
- **Method:** `POST`
- **URL:** `{{baseURL}}/portfolio-analysis/analyze`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "portfolio_url": "https://yourportfolio.com"
}
```
- **Expected Response:** `200 OK`

### 5.2 Get Portfolio Analysis Results
- **Method:** `GET`
- **URL:** `{{baseURL}}/portfolio-analysis/results`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with portfolio analysis

### 5.3 Get Analysis by ID
- **Method:** `GET`
- **URL:** `{{baseURL}}/portfolio-analysis/results/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with specific analysis

### 5.4 Get All Analyses
- **Method:** `GET`
- **URL:** `{{baseURL}}/portfolio-analysis/analyses`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with all portfolio analyses

### 5.5 Re-analyze Portfolio
- **Method:** `POST`
- **URL:** `{{baseURL}}/portfolio-analysis/reanalyze/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK`

### 5.6 Delete Analysis
- **Method:** `DELETE`
- **URL:** `{{baseURL}}/portfolio-analysis/delete/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK`

### 5.7 Get Portfolio Improvement Suggestions
- **Method:** `GET`
- **URL:** `{{baseURL}}/portfolio-analysis/suggestions/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with detailed portfolio suggestions
- **Response includes:**
  - Immediate improvements
  - Content improvements
  - Technical improvements
  - Career-specific advice
  - Project recommendations

### 5.8 Get User Portfolio Analyses
- **Method:** `GET`
- **URL:** `{{baseURL}}/portfolio-analysis/user/portfolios`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with all user portfolio analyses

### 5.9 Get Extracted Portfolio Data
- **Method:** `GET`
- **URL:** `{{baseURL}}/portfolio-analysis/extracted-data/{analysis_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with raw extracted website data

---

## 6. Community Platform Endpoints (/api/community)

### 6.1 Create Post
- **Method:** `POST`
- **URL:** `{{baseURL}}/community/posts`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "content": "This is my first post in the community!"
}
```
- **Expected Response:** `201 Created`

### 6.2 Get All Posts
- **Method:** `GET`
- **URL:** `{{baseURL}}/community/posts`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Query Parameters (optional):**
  - `limit`: Number of posts to retrieve (default: 20)
  - `offset`: Number of posts to skip (default: 0)
- **Expected Response:** `200 OK` with posts array

### 6.3 Get Single Post
- **Method:** `GET`
- **URL:** `{{baseURL}}/community/posts/{post_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with post details

### 6.4 Get User's Posts
- **Method:** `GET`
- **URL:** `{{baseURL}}/community/posts/user`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with user's posts

### 6.5 Get My Posts
- **Method:** `GET`
- **URL:** `{{baseURL}}/community/my-posts`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with authenticated user's posts

### 6.6 Like/Unlike a Post
- **Method:** `POST`
- **URL:** `{{baseURL}}/community/posts/{post_id}/like`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` (toggles like status)

### 6.7 Add Reply to Post
- **Method:** `POST`
- **URL:** `{{baseURL}}/community/posts/{post_id}/replies`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "text": "This is a reply to the post"
}
```
- **Expected Response:** `201 Created`

### 6.8 Get Post Replies
- **Method:** `GET`
- **URL:** `{{baseURL}}/community/posts/{post_id}/replies`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with replies array

### 6.9 Delete Post
- **Method:** `DELETE`
- **URL:** `{{baseURL}}/community/posts/{post_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` (only author can delete)

### 6.10 Delete Reply
- **Method:** `DELETE`
- **URL:** `{{baseURL}}/community/posts/{post_id}/replies/{reply_id}`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` (only author can delete)

### 6.11 Get Community Statistics
- **Method:** `GET`
- **URL:** `{{baseURL}}/community/stats`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with community stats

---

## 7. User Settings & Extended Features (/api/user)

### 7.1 Get User Settings
- **Method:** `GET`
- **URL:** `{{baseURL}}/user/settings`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with user settings

### 7.2 Update User Settings
- **Method:** `PUT`
- **URL:** `{{baseURL}}/user/settings`
- **Headers:** 
  - `Content-Type: application/json`
  - `X-User-ID: user-id-here`
- **Body (JSON):**
```json
{
  "notifications": true,
  "email_updates": false,
  "privacy_level": "normal"
}
```
- **Expected Response:** `200 OK`

### 7.3 Get User Resumes (Extended)
- **Method:** `GET`
- **URL:** `{{baseURL}}/user/resumes`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Query Parameters:**
  - `details`: true/false (include full details)
  - `limit`: number (pagination limit)
- **Expected Response:** `200 OK` with resumes and statistics

---

## 8. System Status & Testing Endpoints (/api)

### 8.1 API Status
- **Method:** `GET`
- **URL:** `{{baseURL}}/status`
- **Expected Response:** `200 OK` with comprehensive system status

### 8.2 System Information
- **Method:** `GET`
- **URL:** `{{baseURL}}/info`
- **Expected Response:** `200 OK` with system info and features

### 8.3 Test Authentication
- **Method:** `GET`
- **URL:** `{{baseURL}}/test-auth`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with auth verification

### 8.4 Test Profile Completion
- **Method:** `GET`
- **URL:** `{{baseURL}}/test-profile-completion`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with completion test results

### 8.5 Test Profile Analysis
- **Method:** `GET`
- **URL:** `{{baseURL}}/test-profile-analysis`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with analysis test results

### 8.6 Test Portfolio Analysis
- **Method:** `GET`
- **URL:** `{{baseURL}}/test-portfolio-analysis`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with portfolio test results

### 8.7 Test Community Platform
- **Method:** `GET`
- **URL:** `{{baseURL}}/test-community`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with community test results

### 8.8 Profile Completion Information
- **Method:** `GET`
- **URL:** `{{baseURL}}/profile-completion/info`
- **Expected Response:** `200 OK` with completion system info

---

## 9. Debug & Email Testing Endpoints (/api/debug)

### 9.1 Debug Email Configuration
- **Method:** `GET`
- **URL:** `{{baseURL}}/debug/email-config`
- **Expected Response:** `200 OK` with email configuration details

### 9.2 Test Email Connection
- **Method:** `POST`
- **URL:** `{{baseURL}}/debug/test-email-connection`
- **Expected Response:** `200 OK` if connection successful

### 9.3 Send Test Email
- **Method:** `POST`
- **URL:** `{{baseURL}}/debug/send-test-email`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "email": "test@example.com"
}
```
- **Expected Response:** `200 OK` if email sent successfully

### 9.4 Debug Profile Completion
- **Method:** `GET`
- **URL:** `{{baseURL}}/debug/profile-completion/{user_id}`
- **Expected Response:** `200 OK` with detailed completion analysis

---

## 10. Rate Limiting & Error Handling

### Rate Limits
- **Daily limit**: 200 requests per day
- **Hourly limit**: 50 requests per hour
- **Applies to**: All endpoints except system status

### Common HTTP Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required/invalid
- `403 Forbidden`: Access denied (e.g., trying to delete others' content)
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error
- `503 Service Unavailable`: Service temporarily unavailable

### Error Response Format
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)",
  "success": false
}
```

### Success Response Format
```json
{
  "message": "Success message",
  "data": { /* response data */ },
  "success": true
}
```

---

## 11. Complete Endpoint Summary

### Authentication (7 endpoints)
1. `POST /api/auth/register`
2. `POST /api/auth/login`
3. `POST /api/auth/google-login`
4. `POST /api/auth/change-password`
5. `POST /api/auth/forgot-password`
6. `POST /api/auth/reset-password`
7. `POST /api/auth/test-email`

### User Management (6 endpoints)
8. `GET /api/user/profile`
9. `PUT /api/user/profile`
10. `DELETE /api/user/profile`
11. `GET /api/user/stats`
12. `GET /api/user/settings`
13. `PUT /api/user/settings`
14. `GET /api/user/resumes`

### Resume Processing (8 endpoints)
15. `POST /api/resume/upload`
16. `GET /api/resume/status/{resume_id}`
17. `GET /api/resume/results/{resume_id}`
18. `GET /api/resume/questions/{resume_id}`
19. `GET /api/resume/analysis/{resume_id}`
20. `POST /api/resume/reprocess/{resume_id}`
21. `DELETE /api/resume/delete/{resume_id}`

### Profile Analysis (9 endpoints)
22. `POST /api/profile-analysis/linkedin`
23. `POST /api/profile-analysis/github`
24. `GET /api/profile-analysis/results`
25. `GET /api/profile-analysis/results/{analysis_id}`
26. `GET /api/profile-analysis/analyses`
27. `POST /api/profile-analysis/reanalyze/{analysis_id}`
28. `DELETE /api/profile-analysis/delete/{analysis_id}`
29. `POST /api/profile-analysis/quick-analyze`
30. `GET /api/profile-analysis/suggestions/{analysis_id}`

### Portfolio Analysis (9 endpoints)
31. `POST /api/portfolio-analysis/analyze`
32. `GET /api/portfolio-analysis/results`
33. `GET /api/portfolio-analysis/results/{analysis_id}`
34. `GET /api/portfolio-analysis/analyses`
35. `POST /api/portfolio-analysis/reanalyze/{analysis_id}`
36. `DELETE /api/portfolio-analysis/delete/{analysis_id}`
37. `GET /api/portfolio-analysis/suggestions/{analysis_id}`
38. `GET /api/portfolio-analysis/user/portfolios`
39. `GET /api/portfolio-analysis/extracted-data/{analysis_id}`

### Community Platform (11 endpoints)
40. `POST /api/community/posts`
41. `GET /api/community/posts`
42. `GET /api/community/posts/{post_id}`
43. `GET /api/community/posts/user`
44. `GET /api/community/my-posts`
45. `POST /api/community/posts/{post_id}/like`
46. `POST /api/community/posts/{post_id}/replies`
47. `GET /api/community/posts/{post_id}/replies`
48. `DELETE /api/community/posts/{post_id}`
49. `DELETE /api/community/posts/{post_id}/replies/{reply_id}`
50. `GET /api/community/stats`

### System & Testing (8 endpoints)
51. `GET /api/status`
52. `GET /api/info`
53. `GET /api/test-auth`
54. `GET /api/test-profile-completion`
55. `GET /api/test-profile-analysis`
56. `GET /api/test-portfolio-analysis`
57. `GET /api/test-community`
58. `GET /api/profile-completion/info`

### Debug & Email (4 endpoints)
59. `GET /api/debug/email-config`
60. `POST /api/debug/test-email-connection`
61. `POST /api/debug/send-test-email`
62. `GET /api/debug/profile-completion/{user_id}`

**Total: 62 Primary Endpoints + Variations = 90+ Total Endpoints**

---

## 12. Postman Collection Setup

### Environment Variables
Create these variables in your Postman environment:
```
baseURL: http://localhost:5000/api
userID: (obtained from login response)
postID: (for testing community features)
resumeID: (for testing resume features)
analysisID: (for testing analysis features)
```

### Pre-request Scripts
For authenticated endpoints, add this pre-request script:
```javascript
if (pm.environment.get("userID")) {
    pm.request.headers.add({
        key: "X-User-ID",
        value: pm.environment.get("userID")
    });
}
```

### Test Scripts
Add this test script to verify responses:
```javascript
pm.test("Status code is successful", function () {
    pm.expect(pm.response.code).to.be.oneOf([200, 201]);
});

pm.test("Response has required structure", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('message').or.property('data');
});
```

---

## 13. Testing Workflow & Best Practices

### Recommended Testing Order

#### Phase 1: Authentication & Setup
1. **Register** → `POST /api/auth/register`
2. **Login** → `POST /api/auth/login`
3. **Save User ID** → Update environment variable
4. **Test Auth** → `GET /api/test-auth`

#### Phase 2: Profile Management
5. **Get Profile** → `GET /api/user/profile`
6. **Update Profile** → `PUT /api/user/profile`
7. **Test Profile Completion** → `GET /api/test-profile-completion`

#### Phase 3: Resume Features
8. **Upload Resume** → `POST /api/resume/upload`
9. **Check Status** → `GET /api/resume/status/{resume_id}`
10. **Get Results** → `GET /api/resume/results/{resume_id}`
11. **Get Questions** → `GET /api/resume/questions/{resume_id}`

#### Phase 4: Profile Analysis
12. **Analyze LinkedIn** → `POST /api/profile-analysis/linkedin`
13. **Analyze GitHub** → `POST /api/profile-analysis/github`
14. **Get Results** → `GET /api/profile-analysis/results`
15. **Quick Analyze** → `POST /api/profile-analysis/quick-analyze`

#### Phase 5: Portfolio Analysis
16. **Analyze Portfolio** → `POST /api/portfolio-analysis/analyze`
17. **Get Results** → `GET /api/portfolio-analysis/results`

#### Phase 6: Community Features
18. **Create Post** → `POST /api/community/posts`
19. **Get Posts** → `GET /api/community/posts`
20. **Like Post** → `POST /api/community/posts/{post_id}/like`
21. **Add Reply** → `POST /api/community/posts/{post_id}/replies`
22. **Get Community Stats** → `GET /api/community/stats`

#### Phase 7: System Verification
23. **Check System Status** → `GET /api/status`
24. **Test All Features** → Run all test endpoints

#### Suggestion & Recommendation Endpoints
These endpoints provide AI-powered suggestions and career advice:

**Profile Analysis Suggestions:**
- `GET /api/profile-analysis/suggestions/{analysis_id}` - Get improvement suggestions for LinkedIn/GitHub
- Response includes:
  - Professional improvement suggestions
  - Repository improvements (GitHub)
  - Skill development recommendations
  - Career-specific advice
  - Project recommendations
  - Networking opportunities

**Portfolio Analysis Suggestions:**
- `GET /api/portfolio-analysis/suggestions/{analysis_id}` - Get portfolio improvement suggestions
- Response includes:
  - Immediate improvements
  - Content improvements
  - Technical improvements
  - Career-specific advice
  - Project recommendations
  - SEO and performance suggestions

**Resume-Based Suggestions:**
- `GET /api/resume/questions/{resume_id}` - Get AI-generated interview questions
- `GET /api/resume/analysis/{resume_id}` - Get job match analysis and suggestions

### Advanced Testing Scenarios

#### Error Handling Tests
- **Invalid User ID**: Use non-existent user ID
- **Missing Headers**: Remove required headers
- **Invalid Data**: Send malformed JSON
- **Rate Limiting**: Exceed request limits
- **File Upload Errors**: Upload invalid file types

#### Security Tests
- **Unauthorized Access**: Try accessing other users' data
- **SQL Injection**: Test with malicious inputs
- **XSS Prevention**: Test with script inputs
- **Password Security**: Test weak passwords

#### Performance Tests
- **Large File Upload**: Test with maximum file sizes
- **Concurrent Requests**: Multiple simultaneous requests
- **Long Running Operations**: Monitor processing status
- **Pagination**: Test large data sets

### Data Flow Testing

#### Profile Completion Flow
```
Register → Login → Update Profile → Check Completion
                              ↓
Upload Resume → Link GitHub → Link LinkedIn → 100% Complete
```

#### Analysis Flow
```
Profile Setup → Upload Resume → Analyze Profiles → Portfolio Analysis
                                      ↓
Generate Insights → Recommendations → Action Items
```

#### Community Engagement Flow
```
Create Profile → Join Community → Create Posts → Engage with Others
                                        ↓
Like Posts → Add Replies → Build Network → Share Knowledge
```

---

## 14. Common Issues & Troubleshooting

### Authentication Issues
- **401 Unauthorized**: Check X-User-ID header format
- **Invalid User**: Verify user exists in database
- **Token Expired**: Re-login to get fresh session

### File Upload Issues
- **413 Request Entity Too Large**: File exceeds 10MB limit
- **400 Bad Request**: Check file format (PDF required)
- **Processing Timeout**: Large files may take time

### Database Connection Issues
- **500 Internal Server Error**: Check Firebase configuration
- **503 Service Unavailable**: Database temporarily down
- **Connection Timeout**: Network connectivity issues

### Email Service Issues
- **Email Not Sent**: Check SMTP configuration
- **Invalid Email**: Verify email format
- **Service Disabled**: Check email service status

### Community Features Issues
- **403 Forbidden**: Trying to modify others' content
- **404 Not Found**: Post or reply doesn't exist
- **Rate Limited**: Too many posts in short time

### Resolution Steps
1. **Check System Status**: `GET /api/status`
2. **Verify Authentication**: `GET /api/test-auth`
3. **Test Email Config**: `GET /api/debug/email-config`
4. **Review Error Logs**: Check response details
5. **Contact Support**: If issues persist

---

## 15. Postman Collection Import

### Collection Structure
```
Skill Buddy API/
├── 01 - Authentication/
│   ├── Register
│   ├── Login
│   ├── Google Login
│   ├── Change Password
│   ├── Forgot Password
│   ├── Reset Password
│   └── Test Email
├── 02 - User Management/
│   ├── Get Profile
│   ├── Update Profile
│   ├── Delete Profile
│   ├── Get Stats
│   ├── Get Settings
│   ├── Update Settings
│   └── Get Resumes
├── 03 - Resume Processing/
│   ├── Upload Resume
│   ├── Get Status
│   ├── Get Results
│   ├── Get Questions
│   ├── Get Analysis
│   ├── Reprocess
│   └── Delete
├── 04 - Profile Analysis/
│   ├── Analyze LinkedIn
│   ├── Analyze GitHub
│   ├── Get Results
│   ├── Get All Analyses
│   ├── Re-analyze
│   ├── Delete Analysis
│   ├── Quick Analyze
│   └── Get Suggestions
├── 05 - Portfolio Analysis/
│   ├── Analyze Portfolio
│   ├── Get Results
│   ├── Get All Analyses
│   ├── Re-analyze
│   ├── Delete Analysis
│   ├── Get Suggestions
│   ├── Get User Portfolios
│   └── Get Extracted Data
├── 06 - Community Platform/
│   ├── Create Post
│   ├── Get All Posts
│   ├── Get Single Post
│   ├── Get User Posts
│   ├── Get My Posts
│   ├── Like Post
│   ├── Add Reply
│   ├── Get Replies
│   ├── Delete Post
│   ├── Delete Reply
│   └── Get Stats
├── 07 - System & Testing/
│   ├── API Status
│   ├── System Info
│   ├── Test Auth
│   ├── Test Profile Completion
│   ├── Test Profile Analysis
│   ├── Test Portfolio Analysis
│   ├── Test Community
│   └── Profile Completion Info
└── 08 - Debug & Email/
    ├── Debug Email Config
    ├── Test Email Connection
    ├── Send Test Email
    └── Debug Profile Completion
```

### Environment Setup JSON
```json
{
  "name": "Skill Buddy API Environment",
  "values": [
    {
      "key": "baseURL",
      "value": "http://localhost:5000/api",
      "enabled": true
    },
    {
      "key": "userID",
      "value": "",
      "enabled": true
    },
    {
      "key": "postID",
      "value": "",
      "enabled": true
    },
    {
      "key": "resumeID",
      "value": "",
      "enabled": true
    },
    {
      "key": "analysisID",
      "value": "",
      "enabled": true
    }
  ]
}
```

### Global Scripts

#### Pre-request Script (Collection Level)
```javascript
// Auto-add authentication header if userID exists
if (pm.environment.get("userID") && pm.request.headers.has("X-User-ID") === false) {
    pm.request.headers.add({
        key: "X-User-ID",
        value: pm.environment.get("userID")
    });
}

// Log request details for debugging
console.log(`Making ${pm.request.method} request to: ${pm.request.url}`);
```

#### Test Script (Collection Level)
```javascript
// Common tests for all requests
pm.test("Response time is acceptable", function () {
    pm.expect(pm.response.responseTime).to.be.below(10000);
});

pm.test("Response has valid JSON", function () {
    pm.response.to.have.jsonBody();
});

pm.test("No server errors", function () {
    pm.expect(pm.response.code).to.not.be.oneOf([500, 502, 503, 504]);
});

// Save important IDs for subsequent requests
const jsonData = pm.response.json();
if (jsonData.user_id) {
    pm.environment.set("userID", jsonData.user_id);
}
if (jsonData.resume_id) {
    pm.environment.set("resumeID", jsonData.resume_id);
}
if (jsonData.analysis_id) {
    pm.environment.set("analysisID", jsonData.analysis_id);
}
if (jsonData.data && jsonData.data.post_id) {
    pm.environment.set("postID", jsonData.data.post_id);
}
```

---

## 16. API Documentation Standards

### Request Format
All requests should follow these standards:

#### Headers
```
Content-Type: application/json
X-User-ID: {user-id} (for authenticated endpoints)
```

#### Request Body
```json
{
  "field_name": "value",
  "nested_object": {
    "sub_field": "value"
  },
  "array_field": ["item1", "item2"]
}
```

### Response Format
All responses follow consistent structure:

#### Success Response
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "data": {
    // Response data here
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Error Response
```json
{
  "success": false,
  "error": "Error message",
  "details": "Additional error details",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### HTTP Status Codes Usage

#### Success Codes
- `200 OK`: Successful GET, PUT, DELETE
- `201 Created`: Successful POST (resource created)
- `202 Accepted`: Request accepted for processing
- `204 No Content`: Successful DELETE with no response body

#### Client Error Codes
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource already exists
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded

#### Server Error Codes
- `500 Internal Server Error`: Server error
- `502 Bad Gateway`: Upstream server error
- `503 Service Unavailable`: Service temporarily down
- `504 Gateway Timeout`: Request timeout

---

This comprehensive API reference provides everything needed to test and integrate with the Skill Buddy platform. The 85+ endpoints cover all functionality from basic authentication to advanced AI-powered analysis features, making it a complete career development platform.
- **URL:** `{{baseURL}}/test-community`
- **Headers:** 
  - `X-User-ID: user-id-here`
- **Expected Response:** `200 OK` with community test results

---

## 8. Debug & Email Testing Endpoints

### 8.1 Debug Email Configuration
- **Method:** `GET`
- **URL:** `{{baseURL}}/debug/email-config`
- **Expected Response:** `200 OK` with email configuration details

### 8.2 Test Email Connection
- **Method:** `POST`
- **URL:** `{{baseURL}}/debug/test-email-connection`
- **Expected Response:** `200 OK` if connection successful

### 8.3 Send Test Email
- **Method:** `POST`
- **URL:** `{{baseURL}}/debug/send-test-email`
- **Headers:** 
  - `Content-Type: application/json`
- **Body (JSON):**
```json
{
  "email": "test@example.com"
}
```
- **Expected Response:** `200 OK` if email sent successfully

---

## 9. Postman Setup Instructions

### Step 1: Create Environment Variables
1. Open Postman
2. Click on "Environments" → "Create Environment"
3. Name it "Skill Buddy Local"
4. Add these variables:
   - `baseURL`: `http://localhost:5000/api`
   - `userID`: (leave empty, will be filled after login)

### Step 2: Create Collection
1. Click "New" → "Collection"
2. Name it "Skill Buddy API"
3. Add description: "Complete API testing for Skill Buddy application"

### Step 3: Authentication Flow
1. **Register a new user** using endpoint 1.1
2. **Login** using endpoint 1.2
3. **Copy the user_id** from login response
4. **Update environment variable** `userID` with the copied user_id
5. **Use {{userID}}** in X-User-ID header for subsequent requests

### Step 4: Testing Workflow
1. **Authentication**: Register → Login → Get user_id
2. **Profile Setup**: Update profile with basic information
3. **Resume Upload**: Upload and analyze resume
4. **Profile Analysis**: Analyze LinkedIn/GitHub profiles
5. **Portfolio Analysis**: Analyze portfolio website
6. **Community Features**: Create posts, like, reply
7. **System Tests**: Run test endpoints to verify functionality

### Step 5: Common Headers Template
Create a header preset with:
```
Content-Type: application/json
X-User-ID: {{userID}}
```

---

## 10. Error Handling & Status Codes

### Common Status Codes
- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Access denied
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Error Response Format
```json
{
  "error": "Error message",
  "details": "Additional error details"
}
```
