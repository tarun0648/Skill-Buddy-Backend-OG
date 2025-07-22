# Skill Buddy Backend - Enhanced with Interview System

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com/yourrepo)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/flask-2.3%2B-green)](https://flask.palletsprojects.com/)
[![OpenAI](https://img.shields.io/badge/openai-1.35%2B-orange)](https://openai.com)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Skill Buddy Backend is a comprehensive platform for career development, resume analysis, professional networking, and **AI-powered interview practice**. The system now includes an advanced interview module with both role-based and job description-based interview capabilities.

---

## 🆕 New Features - Interview System

### ✨ Two Interview Modes
1. **Role-Based Interviews**: Traditional interviews based on job roles (Software Engineer, Engineering Manager, etc.)
2. **JD-Based Interviews**: Custom interviews generated from actual job descriptions

### 🤖 AI-Powered Features
- OpenAI GPT integration for dynamic question generation
- Intelligent follow-up questions based on candidate responses
- Video interview optimization (no code writing requests)
- Real-time answer analysis and feedback

### 📊 Advanced Analytics
- Interview performance tracking
- Skills assessment based on JD requirements
- Compatibility scoring between candidate and job requirements
- Comprehensive interview history and statistics

---

## Table of Contents
- [Features Overview](#features-overview)
- [Architecture](#architecture)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Interview System Usage](#interview-system-usage)
- [Authentication](#authentication)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)

---

## Features Overview

### 🎯 Core Features
| Feature | Description | Status |
|---------|-------------|--------|
| **User Authentication** | Email/password, phone OTP, GitHub/LinkedIn SSO | ✅ Active |
| **Resume Analysis** | Upload, parse, and get interview questions | ✅ Active |
| **Profile Analysis** | LinkedIn & GitHub scoring and improvement tips | ✅ Active |
| **Portfolio Analysis** | Automated website/portfolio scoring | ✅ Active |
| **Community Features** | Posts, replies, likes, trending content | ✅ Active |
| **Task Management** | Background job tracking and monitoring | ✅ Active |

### 🚀 Interview System Features
| Feature | Description | Status |
|---------|-------------|--------|
| **Role-Based Interviews** | Pre-defined questions by role and experience level | ✅ Active |
| **JD-Based Interviews** | AI-generated questions from job descriptions | ✅ Active |
| **Video Interview Support** | Optimized for video responses (no code writing) | ✅ Active |
| **AI Question Generation** | Dynamic follow-up questions using OpenAI | ✅ Active |
| **Answer Analysis** | Real-time assessment of response quality | ✅ Active |
| **Interview History** | Complete session tracking and analytics | ✅ Active |
| **Skills Assessment** | JD-based skills matching and scoring | ✅ Active |
| **Compatibility Scoring** | Candidate-JD fit percentage calculation | ✅ Active |

---

## Architecture

### 🏗️ System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API   │    │   External      │
│   (React/Vue)   │◄──►│   (Flask)       │◄──►│   Services      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │                        │
                               ▼                        ├─ OpenAI API
                       ┌─────────────────┐              ├─ Firebase
                       │   Services      │              ├─ Twilio SMS
                       │   Layer         │              └─ OAuth Providers
                       └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   Data Layer    │
                       │   (Firebase)    │
                       └─────────────────┘
```

### 📁 Project Structure
```
skill-buddy-backend/
├── app.py                          # Main Flask application
├── requirements.txt                # Dependencies
├── config/                         # Configuration files
│   ├── __init__.py
│   ├── settings.py                 # App configuration
│   └── firebase_config.py          # Firebase setup
├── routes/                         # API route blueprints
│   ├── __init__.py
│   ├── auth_routes.py              # Authentication endpoints
│   ├── user_routes.py              # User management
│   ├── resume_routes.py            # Resume analysis
│   ├── profile_analysis_routes.py  # Profile analysis
│   ├── portfolio_analysis_routes.py # Portfolio analysis
│   ├── community_routes.py         # Community features
│   ├── task_routes.py              # Task management
│   ├── status_routes.py            # Health checks
│   ├── interview_routes.py         # 🆕 Role-based interviews
│   └── jd_interview_routes.py      # 🆕 JD-based interviews
├── services/                       # Business logic layer
│   ├── __init__.py
│   ├── interview_service.py        # 🆕 Interview logic
│   ├── jd_interview_service.py     # 🆕 JD interview logic
│   ├── assistant_client.py         # 🆕 OpenAI integration
│   ├── firebase_service.py         # 🆕 Enhanced Firebase service
│   └── [other existing services]
├── utils/                          # Utility modules
│   ├── __init__.py
│   ├── auth_utils.py               # 🆕 Authentication helpers
│   ├── validation_utils.py         # 🆕 Data validation
│   ├── file_utils.py               # 🆕 File handling
│   └── [other existing utils]
├── data/                           # 🆕 Data files
│   ├── interview_questions.json    # Role-based questions
│   └── jd-predefined.json          # JD interview questions
├── uploads/                        # File uploads
├── logs/                           # Application logs
└── tests/                          # Test files
```

---

## Setup & Installation

### Prerequisites
- Python 3.10+
- Firebase project with Firestore enabled
- OpenAI API account (for interview system)
- Git

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/your-repo/skill-buddy-backend.git
cd skill-buddy-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Firebase Configuration
```bash
# 1. Create a Firebase project at https://console.firebase.google.com
# 2. Enable Firestore Database
# 3. Create a service account and download the JSON key
# 4. Rename the key file to 'serviceAccountKey.json'
# 5. Place it in the project root directory
```

### 3. OpenAI Configuration
```bash
# 1. Get your OpenAI API key from https://platform.openai.com
# 2. Create an OpenAI Assistant (or use existing one)
# 3. Note down the Assistant ID
```

### 4. Environment Variables
```bash
# Create .env file (optional, can use config/settings.py)
cat > .env << EOF
FLASK_ENV=development
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_ASSISTANT_ID=your_assistant_id_here
SECRET_KEY=your_secret_key_here
EOF
```

### 5. Run the Application
```bash
# Start the development server
python app.py

# The API will be available at http://localhost:5000
```

---

## Configuration

### ⚙️ Key Configuration Files

#### `config/settings.py`
```python
# Core settings
FLASK_ENV = 'development'  # or 'production'
DEBUG = True

# Interview System Settings
OPENAI_API_KEY = 'your-api-key'
OPENAI_ASSISTANT_ID = 'asst-xxx'
INTERVIEW_MAX_QUESTIONS = 8
INTERVIEW_MIN_QUESTIONS = 5

# Firebase Settings (automatic from serviceAccountKey.json)

# Feature Flags
FEATURES = {
    'interview_system': True,
    'jd_interviews': True,
    'video_upload': True,
    # ... other features
}
```

#### Environment-Specific Configs
- **Development**: `DevelopmentConfig` - Debug enabled, relaxed limits
- **Production**: `ProductionConfig` - Security hardened, rate limited
- **Testing**: `TestingConfig` - Fast execution, minimal questions

---

## API Endpoints

### 🔐 Authentication Endpoints
```
POST   /api/auth/register           # User registration
POST   /api/auth/login              # User login
POST   /api/auth/phone/send-otp     # Send phone OTP
POST   /api/auth/phone/verify-otp   # Verify phone OTP
POST   /api/auth/sso/github/*       # GitHub OAuth
POST   /api/auth/sso/linkedin/*     # LinkedIn OAuth
```

### 👤 User Management
```
GET    /api/user/profile            # Get user profile
PUT    /api/user/profile            # Update profile
GET    /api/user/all-data           # Export all user data
GET    /api/user/settings           # Get user settings
```

### 🆕 Interview System Endpoints

#### Role-Based Interviews
```
POST   /api/interview/start-session     # Start new interview session
POST   /api/interview/first-question    # Get first question
POST   /api/interview/next-question     # Get next question
GET    /api/interview/history           # Get interview history
POST   /api/interview/upload-video      # Upload video response
POST   /api/interview/save-summary      # Save interview summary
GET    /api/interview/questions/topics  # Get available topics
GET    /api/interview/questions/count   # Get questions count
```

#### JD-Based Interviews
```
POST   /api/jd-interview/analyze           # Analyze job description
POST   /api/jd-interview/first-question    # Get first JD question
POST   /api/jd-interview/next-question     # Get next JD question
GET    /api/jd-interview/history           # Get JD interview history
POST   /api/jd-interview/matching-questions # Get matching questions
POST   /api/jd-interview/generate-custom   # Generate custom question
POST   /api/jd-interview/skills-assessment # Assess candidate skills
POST   /api/jd-interview/compatibility-score # Calculate compatibility
```

### 📊 Existing Features (Resume, Profile, etc.)
```
POST   /api/resume/upload           # Upload resume
GET    /api/resume/results/{id}     # Get analysis results
POST   /api/profile-analysis/*      # Profile analysis endpoints
POST   /api/portfolio-analysis/*    # Portfolio analysis endpoints
GET/POST /api/community/*           # Community features
GET    /api/task/status/{id}        # Task management
```

---

## Interview System Usage

### 🎯 Role-Based Interview Flow

#### 1. Start Interview Session
```bash
curl -X POST http://localhost:5000/api/interview/start-session \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json"
```

#### 2. Get First Question
```bash
curl -X POST http://localhost:5000/api/interview/first-question \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "Software Engineer",
    "level": "mid",
    "topic": "System Design"
  }'
```

#### 3. Continue Interview
```bash
curl -X POST http://localhost:5000/api/interview/next-question \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "thread_abc123",
    "role": "Software Engineer",
    "level": "mid",
    "topic": "System Design",
    "last_question": "Tell me about yourself",
    "last_answer": "I am a software engineer with 3 years experience...",
    "interview_round": 2,
    "session_id": "session_xyz789"
  }'
```

### 🎯 JD-Based Interview Flow

#### 1. Analyze Job Description
```bash
curl -X POST http://localhost:5000/api/jd-interview/analyze \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "We are looking for a Senior Python Developer with experience in Django, AWS, and microservices..."
  }'
```

#### 2. Start JD Interview
```bash
curl -X POST http://localhost:5000/api/jd-interview/first-question \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{
    "extracted_data": {
      "role": "Senior Python Developer",
      "level": "senior",
      "skills": ["Python", "Django", "AWS"],
      "technologies": ["Docker", "Redis", "PostgreSQL"]
    }
  }'
```

### 📱 Frontend Integration Example
```javascript
// React component example
const InterviewComponent = () => {
  const [currentQuestion, setCurrentQuestion] = useState('');
  const [userAnswer, setUserAnswer] = useState('');
  
  const startInterview = async () => {
    const response = await fetch('/api/interview/first-question', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-ID': userId
      },
      body: JSON.stringify({
        role: 'Software Engineer',
        level: 'mid',
        topic: 'System Design'
      })
    });
    
    const data = await response.json();
    setCurrentQuestion(data.question);
  };
  
  // ... rest of component
};
```

---

## Authentication

### 🔑 Authentication Methods

#### 1. Header-Based (Existing System Compatibility)
```bash
# Using X-User-ID header
curl -H "X-User-ID: user123" http://localhost:5000/api/interview/history
```

#### 2. JWT Tokens
```bash
# Using Bearer token
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..." \
     http://localhost:5000/api/interview/history
```

#### 3. Firebase ID Tokens
```bash
# Using Firebase token
curl -H "Authorization: Firebase firebase_id_token_here" \
     http://localhost:5000/api/interview/history
```

### 🛡️ Security Features
- Password strength validation
- Rate limiting (configurable)
- CORS protection
- Input sanitization
- SQL injection prevention
- XSS protection

---

## Development

### 🧪 Running Tests
```bash
# Install test dependencies
pip install pytest pytest-flask pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=./ --cov-report=html

# Run specific test category
pytest tests/test_interview_system.py
```

### 🔧 Development Tools
```bash
# Code formatting
black .

# Import sorting
isort .

# Linting
flake8 .

# Type checking (if using mypy)
mypy .
```

### 📊 Monitoring and Debugging
```bash
# View logs
tail -f logs/app.log

# Test Firebase connection
python -c "from config.firebase_config import test_firebase_connection; print(test_firebase_connection())"

# Test OpenAI connection
python -c "from services.assistant_client import AssistantClient; client = AssistantClient(); print('OpenAI connected')"
```

---

## Testing

### 🧪 Test Structure
```
tests/
├── conftest.py                 # Test configuration
├── test_auth.py               # Authentication tests
├── test_interview_system.py   # Interview system tests
├── test_jd_interviews.py      # JD interview tests
├── test_api_endpoints.py      # API endpoint tests
└── test_services.py           # Service layer tests
```

### 🚀 Test Examples
```python
# Example interview test
def test_start_interview_session(client, auth_headers):
    response = client.post('/api/interview/start-session', 
                          headers=auth_headers)
    assert response.status_code == 200
    assert 'thread_id' in response.json

def test_jd_analysis(client, auth_headers):
    jd_text = "Looking for a Python developer..."
    response = client.post('/api/jd-interview/analyze',
                          json={'job_description': jd_text},
                          headers=auth_headers)
    assert response.status_code == 200
    assert 'extracted_data' in response.json
```

---

## Deployment

### 🚀 Production Deployment

#### Using Gunicorn
```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
```

#### Using Docker
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

#### Environment Variables for Production
```bash
export FLASK_ENV=production
export OPENAI_API_KEY=your_production_key
export SECRET_KEY=your_strong_secret_key
export RATE_LIMIT_ENABLED=true
export LOG_LEVEL=INFO
```

### 🌐 Deployment Platforms

#### Heroku
```bash
# Create Procfile
echo "web: gunicorn app:app" > Procfile

# Deploy
git push heroku main
```

#### Google Cloud Platform
```yaml
# app.yaml
runtime: python310
service: skill-buddy-backend

env_variables:
  FLASK_ENV: production
  OPENAI_API_KEY: your_key_here

automatic_scaling:
  min_instances: 1
  max_instances: 10
```

#### AWS Lambda (Serverless)
```bash
# Install serverless framework
npm install -g serverless

# Deploy with serverless
serverless deploy
```

---

## Performance Optimization

### 📈 Optimization Strategies

#### Database Optimization
- Firebase composite indexes for complex queries
- Pagination for large result sets
- Caching frequently accessed data

#### API Optimization
- Response compression
- Request/response caching
- Background task processing
- Rate limiting

#### Interview System Optimization
- Question pre-loading
- AI response caching
- Async processing for heavy operations

---

## Monitoring and Analytics

### 📊 Key Metrics to Monitor
- API response times
- Interview completion rates
- Question generation latency
- User engagement metrics
- Error rates and types

### 🔍 Logging
```python
# Application logs are automatically saved to logs/app.log
# Key events logged:
# - Authentication events
# - Interview session start/end
# - AI question generation
# - Error events
# - Performance metrics
```

---

## Contributing

### 🤝 Contributing Guidelines

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/interview-enhancement
   ```
3. **Make your changes**
4. **Add tests for new features**
5. **Run the test suite**
   ```bash
   pytest
   ```
6. **Submit a pull request**

### 📝 Code Standards
- Follow PEP 8 for Python code
- Use type hints where possible
- Add docstrings for all functions
- Write tests for new features
- Update documentation

### 🐛 Reporting Issues
- Use the GitHub issue tracker
- Include steps to reproduce
- Provide error logs and stack traces
- Specify your environment details

---

## Troubleshooting

### ❗ Common Issues

#### OpenAI API Issues
```bash
# Test OpenAI connection
python -c "
from services.assistant_client import AssistantClient
client = AssistantClient()
thread_id = client.create_thread()
print(f'Success: {thread_id}')
"
```

#### Firebase Connection Issues
```bash
# Verify Firebase setup
python -c "
from config.firebase_config import test_firebase_connection
result = test_firebase_connection()
print(f'Firebase connected: {result}')
"
```

#### Missing Dependencies
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

## License

MIT License. See [LICENSE](LICENSE) file for details.

---

## Support

- 📧 Email: support@skillbuddy.com
- 💬 Discord: [Join our community](https://discord.gg/skillbuddy)
- 📖 Documentation: [Full API docs](https://docs.skillbuddy.com)
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/skill-buddy-backend/issues)

---

## Changelog

### v2.0.0 - Interview System Integration
- ✅ Added role-based interview system
- ✅ Added JD-based interview system
- ✅ Integrated OpenAI GPT for question generation
- ✅ Added video interview support
- ✅ Enhanced Firebase integration
- ✅ Added comprehensive authentication system
- ✅ Improved error handling and validation
- ✅ Added interview analytics and reporting

### v1.x.x - Previous Versions
- Resume analysis system
- Profile analysis features
- Portfolio analysis
- Community features
- Task management system

---

**🎉 Ready to revolutionize interview preparation with AI-powered practice sessions!**