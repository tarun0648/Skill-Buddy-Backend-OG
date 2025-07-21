# Skill Buddy Backend API Documentation

## Base URL
```
http://localhost:5000/api
```

---

# How to Test in Postman: Step-by-Step

1. **Set up your environment:**
   - Set `base_url` variable to `http://localhost:5000/api` in Postman.
   - For authenticated endpoints, set the `X-User-ID` header to your user ID.
   - For SSO flows, follow the OAuth instructions below.

2. **Import endpoints:**
   - Copy any endpoint below and paste it into Postman as a new request.
   - Set the method (GET, POST, etc.) and the URL (e.g., `{{base_url}}/user/all-data`).

3. **Set headers:**
   - For most endpoints, set `Content-Type: application/json`.
   - For file uploads, use `form-data`.
   - For authenticated endpoints, set `X-User-ID`.

4. **Send the request and check the response.**

---

# Authentication Endpoints

## Register User
- **POST** `/auth/register`
- **Body (JSON):**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "John Doe"
}
```
- **Instructions:**
  1. Create a new POST request to `{{base_url}}/auth/register`.
  2. Set body to raw JSON as above.
  3. Send the request.
  4. Check for `user_id` in the response.

## Login User
- **POST** `/auth/login`
- **Body (JSON):**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```
- **Instructions:**
  1. Create a new POST request to `{{base_url}}/auth/login`.
  2. Set body to raw JSON as above.
  3. Send the request.
  4. Check for `user_id` in the response.

## Phone OTP Authentication
- **POST** `/auth/phone/send-otp`
- **POST** `/auth/phone/verify-otp`
- **POST** `/auth/phone/resend-otp`
- **Instructions:**
  1. Send phone number to `/auth/phone/send-otp` to receive OTP.
  2. Use `/auth/phone/verify-otp` with phone and OTP to login/signup.
  3. Use `/auth/phone/resend-otp` to resend OTP if needed.

## Change Password
- **POST** `/auth/change-password`
- **Body (JSON):**
```json
{
  "user_id": "<user_id>",
  "current_password": "oldpass",
  "new_password": "newpass"
}
```

## Forgot/Reset Password
- **POST** `/auth/forgot-password`
- **POST** `/auth/reset-password`
- **Instructions:**
  1. Use `/auth/forgot-password` with email to receive reset link.
  2. Use `/auth/reset-password` with token and new password.

---

# SSO (Single Sign-On) Endpoints

## LinkedIn SSO
- **POST** `/auth/sso/linkedin/authorize`
- **POST** `/auth/sso/linkedin/callback`
- **Instructions:**
  1. Use `/auth/sso/linkedin/authorize` to get the LinkedIn OAuth URL.
  2. Complete the OAuth flow in browser.
  3. Use `/auth/sso/linkedin/callback` with the code and state from LinkedIn.

## GitHub SSO
- **POST** `/auth/sso/github/authorize`
- **POST** `/auth/sso/github/callback`
- **Instructions:**
  1. Use `/auth/sso/github/authorize` to get the GitHub OAuth URL.
  2. Complete the OAuth flow in browser.
  3. Use `/auth/sso/github/callback` with the code and state from GitHub.

## SSO Status & Disconnect
- **GET** `/auth/sso/status`
- **POST** `/auth/sso/disconnect/<provider>`

---

# User Endpoints

## Get/Update Profile
- **GET** `/user/profile`
- **PUT** `/user/profile`
- **PUT** `/user/profile/links`
- **GET** `/user/profile/completion`
- **Instructions:**
  1. Set `X-User-ID` header.
  2. Use GET to fetch, PUT to update profile fields.

## User Settings
- **GET** `/user/settings`
- **PUT** `/user/settings`

## User XP
- **GET** `/user/xp`

## SSO Data
- **GET** `/user/sso/linkedin/data`
- **GET** `/user/sso/github/data`
- **GET** `/user/sso/data/export`

## All User Data
- **GET** `/user/all-data`
- **GET** `/user/all-data/summary`
- **Instructions:**
  1. Set `X-User-ID` header.
  2. Use `/user/all-data` for full data, `/user/all-data/summary` for dashboard summary.

---

# Resume Endpoints

## Upload Resume
- **POST** `/resume/upload`
- **Headers:** `X-User-ID`, `Content-Type: multipart/form-data`
- **Body:** Form-data with `resume` (PDF file), `job_description` (optional)
- **Instructions:**
  1. Create a new POST request to `{{base_url}}/resume/upload`.
  2. Set `X-User-ID` header.
  3. In body, select `form-data`, add `resume` as file, and `job_description` as text (optional).
  4. Send the request.

## Resume Status/Results
- **GET** `/resume/status/<user_id>`
- **GET** `/resume/results/<user_id>`
- **GET** `/resume/questions/<user_id>`
- **GET** `/resume/analysis/<user_id>`
- **POST** `/resume/reprocess/<user_id>`
- **DELETE** `/resume/delete/<user_id>`
- **GET** `/resume/list/<user_id>`
- **Instructions:**
  1. Set `X-User-ID` header.
  2. Use the appropriate endpoint to check status, get results, or delete resumes.

---

# Profile Analysis Endpoints

## LinkedIn & GitHub Analysis
- **POST** `/profile-analysis/analyze/linkedin`
- **POST** `/profile-analysis/analyze/github`
- **GET** `/profile-analysis/status/linkedin/<user_id>`
- **GET** `/profile-analysis/status/github/<user_id>`
- **GET** `/profile-analysis/results/linkedin/<user_id>`
- **GET** `/profile-analysis/results/github/<user_id>`
- **GET** `/profile-analysis/results/<user_id>`
- **GET** `/profile-analysis/suggestions/<user_id>`
- **POST** `/profile-analysis/reanalyze/linkedin/<user_id>`
- **POST** `/profile-analysis/reanalyze/github/<user_id>`
- **DELETE** `/profile-analysis/delete/<user_id>`
- **POST** `/profile-analysis/quick-analyze`
- **Instructions:**
  1. Set `X-User-ID` header.
  2. Use POST to start analysis, GET to check status/results, DELETE to remove analyses.

---

# Portfolio Analysis Endpoints

## Analyze Portfolio
- **POST** `/portfolio-analysis/analyze`
- **GET** `/portfolio-analysis/status/<user_id>`
- **GET** `/portfolio-analysis/results/<user_id>`
- **GET** `/portfolio-analysis/suggestions/<user_id>`
- **POST** `/portfolio-analysis/reanalyze/<user_id>`
- **DELETE** `/portfolio-analysis/delete/<user_id>`
- **GET** `/portfolio-analysis/extracted-data/<user_id>`
- **Instructions:**
  1. Set `X-User-ID` header.
  2. Use POST to start analysis, GET to check status/results, DELETE to remove analyses.

---

# Community Endpoints

## Posts
- **POST** `/community/posts`
- **GET** `/community/posts`
- **GET** `/community/posts/<post_id>`
- **POST** `/community/posts/<post_id>/like`
- **POST** `/community/posts/<post_id>/replies`
- **GET** `/community/posts/<post_id>/replies`
- **DELETE** `/community/posts/<post_id>`
- **DELETE** `/community/posts/<post_id>/replies/<reply_id>`
- **GET** `/community/my-posts`
- **GET** `/community/stats`
- **GET** `/community/search?q=term`
- **GET** `/community/trending`
- **Instructions:**
  1. Set `X-User-ID` header.
  2. Use POST to create/like/reply, GET to fetch, DELETE to remove.

---

# Task Management Endpoints

## Task Status & History
- **GET** `/task/status/<user_id>`
- **GET** `/task/status/<user_id>/<task_type>`
- **POST** `/task/cancel/<task_id>`
- **GET** `/task/history/<user_id>`
- **POST** `/task/cleanup`
- **GET** `/task/stats/<user_id>`
- **Instructions:**
  1. Set `X-User-ID` header.
  2. Use GET to check status/history/stats, POST to cancel/cleanup tasks.

---

# Tips for Postman
- Use environment variables for `base_url` and `X-User-ID`.
- For file uploads, use `form-data` and select the file type.
- For SSO, follow the OAuth flow: get the auth URL, complete in browser, use code/state in callback.
- Save example responses for quick reference.
- Use Postman collections to organize requests by feature.

---

# Example: Testing Resume Upload in Postman
1. Create a new POST request to `{{base_url}}/resume/upload`.
2. Set `X-User-ID` header to your user ID.
3. In the body, select `form-data`.
4. Add a key `resume` of type `File` and select a PDF file.
5. (Optional) Add a key `job_description` as text.
6. Send the request and check for a `task_id` in the response.

---

# Example: Testing GitHub SSO in Postman
1. POST to `/auth/sso/github/authorize` to get the GitHub OAuth URL.
2. Open the URL in your browser and complete the GitHub login/authorization.
3. GitHub will redirect to your frontend with a `code` and `state`.
4. POST to `/auth/sso/github/callback` with `{ "code": "...", "state": "..." }` in the body.
5. Check the response for user and profile data.

---

# Need More Help?
- For any endpoint, check the response for error messages and required fields.
- If you get a 401 error, make sure your `X-User-ID` is correct and the user exists.
- For SSO, ensure your OAuth app credentials are set up in the backend.

---

This documentation covers all endpoints in your backend. Use it as a reference for testing every feature in Postman!
