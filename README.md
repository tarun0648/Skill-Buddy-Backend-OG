# Skill Buddy Backend

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/yourrepo)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Skill Buddy is a backend platform for career development, resume analysis, and professional networking.  
It empowers users to analyze their resumes, LinkedIn, GitHub, and portfolios, and engage with a learning community.

---

## Table of Contents
- [Project Introduction](#project-introduction)
- [Key Technologies](#key-technologies)
- [Features](#features)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Authentication](#authentication)
- [API Overview](#api-overview)
- [Endpoints](#endpoints)
- [Example API Flow](#example-api-flow)
- [Task & Parallel Processing](#task--parallel-processing)
- [Testing & Postman](#testing--postman)
- [Development & Scripts](#development--scripts)
- [Deployment](#deployment)
- [Logging](#logging)
- [Security](#security)
- [License](#license)
- [Contact](#contact)

---

## Project Introduction

Skill Buddy Backend is a modular, scalable REST API for powering the Skill Buddy platform. It provides:
- Secure user authentication (email, phone OTP, SSO)
- Automated resume, profile, and portfolio analysis
- Community features for peer learning
- Task management and parallel processing for heavy jobs
- Comprehensive user data export and analytics

---

## Key Technologies

- **Flask**: Python web framework for REST APIs
- **Firebase**: NoSQL database and authentication
- **PyJWT, bcrypt, argon2**: Secure authentication and password hashing
- **Background Tasks**: Parallel processing for heavy jobs
- **Postman**: API documentation and testing
- **Sentry, Logging**: Monitoring and error tracking

---

## Features

| Feature                | Description                                                      |
|------------------------|------------------------------------------------------------------|
| User Auth              | Email/password, phone OTP, GitHub/LinkedIn SSO                   |
| Resume Analysis        | Upload, parse, and get interview questions                       |
| Profile Analysis       | LinkedIn & GitHub scoring, suggestions, and improvement tips     |
| Portfolio Analysis     | Automated website/portfolio scoring and feedback                 |
| Community              | Posts, replies, likes, trending, and search                      |
| Task Management        | Track, cancel, and monitor background jobs                       |
| Data Export            | Export all user data in one endpoint                             |
| Rate Limiting & Security | Secure, scalable, and production-ready                         |

---

## Project Structure

```
.
├── app.py                  # Main Flask app entrypoint
├── requirements.txt        # Python dependencies
├── config/                 # Configuration files (Firebase, settings)
├── models/                 # Data models (User, Resume, Profile, Community, etc.)
├── routes/                 # API route blueprints (auth, user, resume, etc.)
├── services/               # Business logic/services (SSO, analyzers, email, etc.)
├── utils/                  # Utility modules (validation, encryption, etc.)
├── scripts/                # Migration and admin scripts
├── uploads/                # Uploaded files (resumes, etc.)
├── logs/                   # Application logs
├── POSTMAN.md              # API endpoint documentation
├── POSTMAN_TESTING_GUIDE.md# Step-by-step Postman testing guide
├── ALL_USER_DATA_ENDPOINTS.md # User data export endpoint docs
├── Procfile, runtime.txt, app.yaml # Deployment configs
└── serviceAccountKey.json  # Firebase credentials (not committed)
```

---

## Setup & Installation

1. **Clone the repository**
2. **Create and activate a virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
4. **Add your Firebase service account key**
   - Place `serviceAccountKey.json` in the project root.
5. **Configure environment variables** (see `config/settings.py` and `.env` if used)
6. **Run the app**
   ```bash
   python app.py
   ```
   The API will be available at `http://localhost:5000/api`

---

## Configuration

- **Firebase:** Set up in `config/firebase_config.py` and `serviceAccountKey.json`
- **App settings:** See `config/settings.py`
- **Environment variables:** (Optional) Use `.env` for secrets and config overrides

---

## Authentication

- **Email/Password**: Register and login with email and password.
- **Phone OTP**: Login or register with a phone number and OTP.
- **SSO**: Connect with GitHub or LinkedIn for seamless sign-in.
- **Header**: Most endpoints require `X-User-ID` in the header.

---

## API Overview

- **All endpoints are prefixed with `/api`**
- **Authentication:** Most endpoints require `X-User-ID` header
- **Rate Limiting:** 20,000 requests/day, 5,000/hour (configurable)
- **Comprehensive API documentation:** See `POSTMAN.md` and `POSTMAN_TESTING_GUIDE.md`

---

## Endpoints

See `POSTMAN.md` for a full, categorized list.  
**Highlights:**

- **Auth:** `/auth/register`, `/auth/login`, `/auth/phone/send-otp`, `/auth/sso/github/authorize`, `/auth/sso/linkedin/authorize`, etc.
- **User:** `/user/profile`, `/user/settings`, `/user/all-data`, `/user/all-data/summary`
- **Resume:** `/resume/upload`, `/resume/status/<user_id>`, `/resume/results/<user_id>`, etc.
- **Profile Analysis:** `/profile-analysis/analyze/linkedin`, `/profile-analysis/analyze/github`, `/profile-analysis/quick-analyze`
- **Portfolio Analysis:** `/portfolio-analysis/analyze`, `/portfolio-analysis/results/<user_id>`
- **Community:** `/community/posts`, `/community/posts/<post_id>/replies`, `/community/my-posts`
- **Task Management:** `/task/status/<user_id>`, `/task/cancel/<task_id>`, `/task/history/<user_id>`

**For detailed request/response examples, see `POSTMAN.md` and `ALL_USER_DATA_ENDPOINTS.md`.**

---

## Example API Flow

1. **Register**: `POST /api/auth/register`
2. **Login**: `POST /api/auth/login`
3. **Upload Resume**: `POST /api/resume/upload`
4. **Get Resume Analysis**: `GET /api/resume/results/<user_id>`
5. **View All Data**: `GET /api/user/all-data`

---

## Task & Parallel Processing

- All heavy operations (resume parsing, profile/portfolio analysis) are processed in parallel background tasks.
- Task status and history can be tracked via `/task/status/<user_id>`, `/task/history/<user_id>`, etc.

---

## Testing & Postman

- **Step-by-step Postman guide:** See `POSTMAN_TESTING_GUIDE.md`
- **Ready-to-import collection:** Use endpoints from `POSTMAN.md`
- **Environment variables:** Use `base_url` and `user_id` for easy switching
- **Run tests with:**
  ```bash
  pytest
  ```

---

## Development & Scripts

- **Migration scripts:** See `scripts/migrate_passwords.py` for password hash migration
- **Utilities:** See `utils/` for validation, encryption, file handling, etc.
- **Logging:** All logs are written to `logs/app.log`

---

## Deployment

- **Heroku**: Uses `Procfile`
- **Google App Engine**: Uses `app.yaml`
- **Docker**: (Add instructions if Dockerfile is present)

---

## Logging

- Logs are stored in `logs/app.log`
- Logging is configured in `app.py` (INFO level by default)

---

## Security

- Passwords are hashed (bcrypt, argon2, passlib)
- JWT and session management for authentication
- Rate limiting and CORS enabled
- All user data endpoints require authentication
- Sensitive data is sanitized before transmission

---

## Contributing

- Fork the repo and create your feature branch (`git checkout -b feature/fooBar`)
- Commit your changes (`git commit -am 'Add some fooBar'`)
- Push to the branch (`git push origin feature/fooBar`)
- Create a new Pull Request

---

## License

MIT License. See [LICENSE](LICENSE) for details.

---

## Contact

Open an issue or email the maintainer.

---

## More

- See `POSTMAN.md` and `POSTMAN_TESTING_GUIDE.md` for full API docs and testing steps. 