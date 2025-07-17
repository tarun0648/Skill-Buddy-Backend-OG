import os
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlencode
import secrets
import hashlib
from config.firebase_config import firebase_config

logger = logging.getLogger(__name__)

class SSOService:
    """Service for handling LinkedIn and GitHub SSO with data fetching"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        
        # LinkedIn OAuth Configuration
        self.linkedin_client_id = os.environ.get('LINKEDIN_CLIENT_ID')
        self.linkedin_client_secret = os.environ.get('LINKEDIN_CLIENT_SECRET')
        self.linkedin_redirect_uri = os.environ.get('LINKEDIN_REDIRECT_URI', 'http://localhost:3000/auth/linkedin/callback')
        
        # GitHub OAuth Configuration
        self.github_client_id = os.environ.get('GITHUB_CLIENT_ID')
        self.github_client_secret = os.environ.get('GITHUB_CLIENT_SECRET')
        self.github_redirect_uri = os.environ.get('GITHUB_REDIRECT_URI', 'http://localhost:3000/auth/github/callback')
        
        # OAuth URLs
        self.linkedin_auth_url = "https://www.linkedin.com/oauth/v2/authorization"
        self.linkedin_token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.linkedin_profile_url = "https://api.linkedin.com/v2/people/~"
        self.linkedin_email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
        
        self.github_auth_url = "https://github.com/login/oauth/authorize"
        self.github_token_url = "https://github.com/login/oauth/access_token"
        self.github_user_url = "https://api.github.com/user"
        self.github_email_url = "https://api.github.com/user/emails"
        
        # State storage for OAuth security
        self.state_collection = 'oauth_states'
    
    def generate_state(self, provider: str, user_email: str = None) -> str:
        """Generate secure state parameter for OAuth"""
        state = secrets.token_urlsafe(32)
        
        # Store state in database with expiration
        state_data = {
            'state': state,
            'provider': provider,
            'user_email': user_email,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(minutes=10),
            'used': False
        }
        
        if self.db:
            self.db.collection(self.state_collection).document(state).set(state_data)
        
        return state
    
    def verify_state(self, state: str, provider: str) -> Tuple[bool, Optional[str]]:
        """Verify OAuth state parameter"""
        try:
            if not self.db:
                return False, None
            
            doc = self.db.collection(self.state_collection).document(state).get()
            if not doc.exists:
                return False, None
            
            state_data = doc.to_dict()
            
            # Check if state matches provider and hasn't expired or been used
            if (state_data.get('provider') == provider and 
                state_data.get('expires_at') > datetime.utcnow() and 
                not state_data.get('used')):
                
                # Mark as used
                doc.reference.update({'used': True})
                return True, state_data.get('user_email')
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error verifying state: {e}")
            return False, None
    
    def cleanup_expired_states(self):
        """Clean up expired OAuth states"""
        try:
            if not self.db:
                return
            
            expired_query = self.db.collection(self.state_collection)\
                .where('expires_at', '<', datetime.utcnow())
            
            expired_docs = expired_query.get()
            for doc in expired_docs:
                doc.reference.delete()
                
        except Exception as e:
            logger.error(f"Error cleaning up expired states: {e}")

    # ==================== LINKEDIN SSO ====================
    
    def get_linkedin_auth_url(self, user_email: str = None, fetch_data: bool = False) -> str:
        """Generate LinkedIn OAuth authorization URL"""
        state = self.generate_state('linkedin', user_email)
        
        # Define scopes based on whether we need to fetch data
        if fetch_data:
            scopes = ['r_liteprofile', 'r_emailaddress', 'r_basicprofile', 'r_organization_social']
        else:
            scopes = ['r_liteprofile', 'r_emailaddress']
        
        params = {
            'response_type': 'code',
            'client_id': self.linkedin_client_id,
            'redirect_uri': self.linkedin_redirect_uri,
            'state': state,
            'scope': ' '.join(scopes)
        }
        
        return f"{self.linkedin_auth_url}?{urlencode(params)}"
    
    def exchange_linkedin_code(self, code: str, state: str) -> Tuple[bool, Dict[str, Any]]:
        """Exchange LinkedIn authorization code for access token"""
        try:
            # Verify state
            state_valid, user_email = self.verify_state(state, 'linkedin')
            if not state_valid:
                return False, {'error': 'Invalid or expired state parameter'}
            
            # Exchange code for token
            token_data = {
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': self.linkedin_redirect_uri,
                'client_id': self.linkedin_client_id,
                'client_secret': self.linkedin_client_secret
            }
            
            token_response = requests.post(
                self.linkedin_token_url,
                data=token_data,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            if token_response.status_code != 200:
                return False, {'error': 'Failed to exchange code for token'}
            
            token_info = token_response.json()
            access_token = token_info.get('access_token')
            
            if not access_token:
                return False, {'error': 'No access token received'}
            
            # Fetch user profile
            profile_data = self.fetch_linkedin_profile(access_token)
            
            return True, {
                'access_token': access_token,
                'profile_data': profile_data,
                'user_email': user_email,
                'provider': 'linkedin'
            }
            
        except Exception as e:
            logger.error(f"Error exchanging LinkedIn code: {e}")
            return False, {'error': str(e)}
    
    def fetch_linkedin_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch LinkedIn profile data"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            # Fetch basic profile
            profile_response = requests.get(
                f"{self.linkedin_profile_url}?projection=(id,firstName,lastName,headline,summary,positions,educations,skills,profilePicture(displayImage~:playableStreams))",
                headers=headers,
                timeout=30
            )
            
            if profile_response.status_code != 200:
                return {'error': 'Failed to fetch LinkedIn profile'}
            
            profile_data = profile_response.json()
            
            # Fetch email
            email_response = requests.get(
                self.linkedin_email_url,
                headers=headers,
                timeout=30
            )
            
            email_data = {}
            if email_response.status_code == 200:
                email_data = email_response.json()
            
            # Process and structure the data
            structured_data = self.process_linkedin_data(profile_data, email_data)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error fetching LinkedIn profile: {e}")
            return {'error': str(e)}
    
    def process_linkedin_data(self, profile_data: Dict[str, Any], email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and structure LinkedIn data"""
        try:
            # Extract basic info
            first_name = profile_data.get('firstName', {}).get('localized', {}).get('en_US', '')
            last_name = profile_data.get('lastName', {}).get('localized', {}).get('en_US', '')
            full_name = f"{first_name} {last_name}".strip()
            
            # Extract email
            email = ''
            if email_data.get('elements'):
                email = email_data['elements'][0].get('handle~', {}).get('emailAddress', '')
            
            # Extract headline and summary
            headline = profile_data.get('headline', {}).get('localized', {}).get('en_US', '')
            summary = profile_data.get('summary', {}).get('localized', {}).get('en_US', '')
            
            # Extract positions (work experience)
            positions = []
            if profile_data.get('positions', {}).get('elements'):
                for position in profile_data['positions']['elements']:
                    position_data = {
                        'title': position.get('title', {}).get('localized', {}).get('en_US', ''),
                        'company': position.get('companyName', {}).get('localized', {}).get('en_US', ''),
                        'description': position.get('description', {}).get('localized', {}).get('en_US', ''),
                        'start_date': self.format_linkedin_date(position.get('timePeriod', {}).get('startDate')),
                        'end_date': self.format_linkedin_date(position.get('timePeriod', {}).get('endDate')),
                        'current': not position.get('timePeriod', {}).get('endDate')
                    }
                    positions.append(position_data)
            
            # Extract education
            educations = []
            if profile_data.get('educations', {}).get('elements'):
                for education in profile_data['educations']['elements']:
                    edu_data = {
                        'school': education.get('schoolName', {}).get('localized', {}).get('en_US', ''),
                        'degree': education.get('degreeName', {}).get('localized', {}).get('en_US', ''),
                        'field': education.get('fieldOfStudy', {}).get('localized', {}).get('en_US', ''),
                        'start_date': self.format_linkedin_date(education.get('timePeriod', {}).get('startDate')),
                        'end_date': self.format_linkedin_date(education.get('timePeriod', {}).get('endDate'))
                    }
                    educations.append(edu_data)
            
            # Extract skills
            skills = []
            if profile_data.get('skills', {}).get('elements'):
                for skill in profile_data['skills']['elements']:
                    skill_name = skill.get('name', {}).get('localized', {}).get('en_US', '')
                    if skill_name:
                        skills.append(skill_name)
            
            # Extract profile picture
            profile_picture = ''
            if profile_data.get('profilePicture', {}).get('displayImage~', {}).get('elements'):
                elements = profile_data['profilePicture']['displayImage~']['elements']
                for element in elements:
                    if element.get('data', {}).get('com.linkedin.digitalmedia.mediaartifact.StillImage'):
                        profile_picture = element['data']['com.linkedin.digitalmedia.mediaartifact.StillImage']['storageArtifacts'][0]['fileIdentifyingUrlPathSegment']
                        break
            
            structured_data = {
                'personal_information': {
                    'name': full_name,
                    'email': email,
                    'headline': headline,
                    'summary': summary,
                    'profile_picture': profile_picture,
                    'linkedin_id': profile_data.get('id', '')
                },
                'work_experience': positions,
                'education': educations,
                'skills': skills,
                'raw_data': profile_data,
                'fetched_at': datetime.utcnow().isoformat()
            }
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error processing LinkedIn data: {e}")
            return {'error': str(e)}

    # ==================== GITHUB SSO ====================
    
    def get_github_auth_url(self, user_email: str = None, fetch_data: bool = False) -> str:
        """Generate GitHub OAuth authorization URL"""
        state = self.generate_state('github', user_email)
        
        # Define scopes based on whether we need to fetch data
        if fetch_data:
            scopes = ['user', 'user:email', 'repo', 'read:org']
        else:
            scopes = ['user', 'user:email']
        
        params = {
            'client_id': self.github_client_id,
            'redirect_uri': self.github_redirect_uri,
            'scope': ' '.join(scopes),
            'state': state,
            'allow_signup': 'true'
        }
        
        return f"{self.github_auth_url}?{urlencode(params)}"
    
    def exchange_github_code(self, code: str, state: str) -> Tuple[bool, Dict[str, Any]]:
        """Exchange GitHub authorization code for access token"""
        try:
            # Verify state
            state_valid, user_email = self.verify_state(state, 'github')
            if not state_valid:
                return False, {'error': 'Invalid or expired state parameter'}
            
            # Exchange code for token
            token_data = {
                'client_id': self.github_client_id,
                'client_secret': self.github_client_secret,
                'code': code,
                'redirect_uri': self.github_redirect_uri
            }
            
            token_response = requests.post(
                self.github_token_url,
                data=token_data,
                headers={'Accept': 'application/json'},
                timeout=30
            )
            
            if token_response.status_code != 200:
                return False, {'error': 'Failed to exchange code for token'}
            
            token_info = token_response.json()
            access_token = token_info.get('access_token')
            
            if not access_token:
                return False, {'error': 'No access token received'}
            
            # Fetch user profile
            profile_data = self.fetch_github_profile(access_token)
            
            return True, {
                'access_token': access_token,
                'profile_data': profile_data,
                'user_email': user_email,
                'provider': 'github'
            }
            
        except Exception as e:
            logger.error(f"Error exchanging GitHub code: {e}")
            return False, {'error': str(e)}
    
    def fetch_github_profile(self, access_token: str) -> Dict[str, Any]:
        """Fetch GitHub profile data"""
        try:
            headers = {
                'Authorization': f'token {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # Fetch user profile
            user_response = requests.get(
                self.github_user_url,
                headers=headers,
                timeout=30
            )
            
            if user_response.status_code != 200:
                return {'error': 'Failed to fetch GitHub profile'}
            
            user_data = user_response.json()
            
            # Fetch emails
            email_response = requests.get(
                self.github_email_url,
                headers=headers,
                timeout=30
            )
            
            emails = []
            if email_response.status_code == 200:
                emails = email_response.json()
            
            # Fetch repositories
            repos_response = requests.get(
                f"https://api.github.com/users/{user_data['login']}/repos?type=owner&sort=updated&per_page=50",
                headers=headers,
                timeout=30
            )
            
            repos = []
            if repos_response.status_code == 200:
                repos = repos_response.json()
            
            # Fetch organizations
            orgs_response = requests.get(
                f"https://api.github.com/users/{user_data['login']}/orgs",
                headers=headers,
                timeout=30
            )
            
            orgs = []
            if orgs_response.status_code == 200:
                orgs = orgs_response.json()
            
            # Process and structure the data
            structured_data = self.process_github_data(user_data, emails, repos, orgs)
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error fetching GitHub profile: {e}")
            return {'error': str(e)}
    
    def process_github_data(self, user_data: Dict[str, Any], emails: list, repos: list, orgs: list) -> Dict[str, Any]:
        """Process and structure GitHub data"""
        try:
            # Find primary email
            primary_email = ''
            for email in emails:
                if email.get('primary'):
                    primary_email = email.get('email', '')
                    break
            
            if not primary_email and emails:
                primary_email = emails[0].get('email', '')
            
            # Process repositories
            processed_repos = []
            total_stars = 0
            total_forks = 0
            languages_used = {}
            
            for repo in repos:
                if not repo.get('fork'):  # Exclude forked repositories
                    repo_data = {
                        'name': repo.get('name'),
                        'description': repo.get('description'),
                        'language': repo.get('language'),
                        'stars': repo.get('stargazers_count', 0),
                        'forks': repo.get('forks_count', 0),
                        'url': repo.get('html_url'),
                        'created_at': repo.get('created_at'),
                        'updated_at': repo.get('updated_at'),
                        'topics': repo.get('topics', []),
                        'size': repo.get('size', 0)
                    }
                    processed_repos.append(repo_data)
                    
                    total_stars += repo.get('stargazers_count', 0)
                    total_forks += repo.get('forks_count', 0)
                    
                    # Count languages
                    language = repo.get('language')
                    if language:
                        languages_used[language] = languages_used.get(language, 0) + 1
            
            # Process organizations
            processed_orgs = []
            for org in orgs:
                org_data = {
                    'name': org.get('login'),
                    'description': org.get('description'),
                    'url': org.get('html_url'),
                    'avatar_url': org.get('avatar_url')
                }
                processed_orgs.append(org_data)
            
            structured_data = {
                'personal_information': {
                    'name': user_data.get('name', ''),
                    'email': primary_email,
                    'username': user_data.get('login', ''),
                    'bio': user_data.get('bio', ''),
                    'company': user_data.get('company', ''),
                    'location': user_data.get('location', ''),
                    'blog': user_data.get('blog', ''),
                    'twitter_username': user_data.get('twitter_username', ''),
                    'avatar_url': user_data.get('avatar_url', ''),
                    'github_id': user_data.get('id', ''),
                    'profile_url': user_data.get('html_url', '')
                },
                'statistics': {
                    'public_repos': user_data.get('public_repos', 0),
                    'followers': user_data.get('followers', 0),
                    'following': user_data.get('following', 0),
                    'total_stars': total_stars,
                    'total_forks': total_forks,
                    'account_created': user_data.get('created_at', ''),
                    'last_updated': user_data.get('updated_at', '')
                },
                'repositories': processed_repos,
                'languages': dict(sorted(languages_used.items(), key=lambda x: x[1], reverse=True)),
                'organizations': processed_orgs,
                'emails': emails,
                'raw_data': user_data,
                'fetched_at': datetime.utcnow().isoformat()
            }
            
            return structured_data
            
        except Exception as e:
            logger.error(f"Error processing GitHub data: {e}")
            return {'error': str(e)}
    
    # ==================== HELPER METHODS ====================
    
    def format_linkedin_date(self, date_obj: Dict[str, Any]) -> str:
        """Format LinkedIn date object to string"""
        if not date_obj:
            return ''
        
        year = date_obj.get('year', '')
        month = date_obj.get('month', '')
        
        if year and month:
            return f"{year}-{month:02d}"
        elif year:
            return str(year)
        
        return ''
    
    def get_debug_info(self) -> Dict[str, Any]:
        """Get debug information about SSO configuration"""
        return {
            'linkedin_configured': bool(self.linkedin_client_id and self.linkedin_client_secret),
            'github_configured': bool(self.github_client_id and self.github_client_secret),
            'linkedin_client_id': self.linkedin_client_id[:10] + '...' if self.linkedin_client_id else None,
            'github_client_id': self.github_client_id[:10] + '...' if self.github_client_id else None,
            'linkedin_redirect_uri': self.linkedin_redirect_uri,
            'github_redirect_uri': self.github_redirect_uri,
            'database_available': self.db is not None
        }

# Global SSO service instance
sso_service = SSOService()