# services/github_analyzer.py (UPDATED for profile completion integration)
import os
import json
import threading
import logging
import requests
from typing import Dict, Any, Optional, Tuple, List
from config.firebase_config import firebase_config
from models.profile_analysis_model import ProfileAnalysisModel

logger = logging.getLogger(__name__)

class ClaudeHTTPClient:
    """HTTP-based Claude client for GitHub analysis"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1"
        self.headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def messages_create(self, model, max_tokens, system=None, messages=None, temperature=None):
        """Create a message using direct HTTP request"""
        url = f"{self.base_url}/messages"
        
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages or []
        }
        
        if system:
            payload["system"] = system
        
        if temperature is not None:
            payload["temperature"] = temperature
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            
            data = response.json()
            
            class SimpleResponse:
                def __init__(self, data):
                    self.content = [SimpleContent(data["content"][0]["text"])]
            
            class SimpleContent:
                def __init__(self, text):
                    self.text = text
            
            return SimpleResponse(data)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP request to Claude API failed: {e}")
            raise Exception(f"Claude API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Claude API call: {e}")
            raise

class GitHubAnalyzerService:
    """Service for analyzing GitHub profiles using GitHub API and Claude AI - UPDATED for profile completion"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self.analysis_model = ProfileAnalysisModel(self.db)
        self._processing_threads = {}
        self.github_api_base = "https://api.github.com"
    
    def update_user_github_status(self, user_id: str, github_username: str, analysis_completed: bool = False):
        """Update user's GitHub link in profile and recalculate completion"""
        try:
            from models.user_model import UserModel
            user_model = UserModel(self.db)
            
            # Get current user
            user = user_model.get_user_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found for GitHub update")
                return
            
            current_profile = user.get('profile', {})
            old_completion = current_profile.get('completion_status', 0)
            
            # Create GitHub URL from username
            github_url = f"https://github.com/{github_username}"
            
            # Update GitHub link if not already set or different
            current_github = current_profile.get('github_link', '')
            if current_github != github_url:
                update_data = {
                    'profile.github_link': github_url,
                    'updated_at': user_model.db.SERVER_TIMESTAMP if hasattr(user_model.db, 'SERVER_TIMESTAMP') else None
                }
                
                # Recalculate completion
                updated_profile = current_profile.copy()
                updated_profile['github_link'] = github_url
                
                new_completion = user_model.calculate_profile_completion(updated_profile)
                update_data['profile.completion_status'] = new_completion
                update_data['profile.is_profile_complete'] = new_completion == 100
                
                # Calculate XP bonus
                milestones = user_model.get_completion_milestones(old_completion, new_completion)
                if milestones:
                    xp_bonus = user_model.calculate_xp_bonus(milestones)
                    if xp_bonus > 0:
                        current_xp = user.get('xp', {}).get('total_xp', 0)
                        new_total_xp = current_xp + xp_bonus
                        new_level = (new_total_xp // 100) + 1
                        
                        update_data['xp.total_xp'] = new_total_xp
                        update_data['xp.level'] = new_level
                        
                        logger.info(f"GitHub analysis XP bonus: {xp_bonus} for user {user_id}")
                
                # Apply update
                success = user_model.update_user(user_id, update_data)
                if success:
                    logger.info(f"Updated GitHub link for user {user_id}: {github_url}")
                    logger.info(f"Completion updated: {old_completion}% -> {new_completion}%")
                
        except Exception as e:
            logger.error(f"Error updating GitHub status for user {user_id}: {e}")
    
    def start_github_analysis(self, user_id: str, github_username: str, user_profile: Dict[str, Any]) -> Tuple[str, bool]:
        """Start asynchronous GitHub profile analysis - UPDATED"""
        try:
            # Create initial analysis record
            analysis_data = {
                'analysis_type': 'github',
                'github_username': github_username,
                'user_profile_context': user_profile
            }
            
            analysis_id = self.analysis_model.create_analysis_record(user_id, analysis_data)
            
            # Start processing in background thread
            processing_thread = threading.Thread(
                target=self._analyze_github_async,
                args=(analysis_id, user_id, github_username, user_profile),
                daemon=True
            )
            processing_thread.start()
            
            # Track the thread
            self._processing_threads[analysis_id] = processing_thread
            
            logger.info(f"Started GitHub analysis for analysis_id: {analysis_id}")
            return analysis_id, True
            
        except Exception as e:
            logger.error(f"Error starting GitHub analysis: {e}")
            return "", False
    
    def _analyze_github_async(self, analysis_id: str, user_id: str, github_username: str, user_profile: Dict[str, Any]):
        """Analyze GitHub profile asynchronously using GitHub API and Claude AI - UPDATED"""
        try:
            logger.info(f"Starting async GitHub analysis for: {analysis_id}")
            
            # Update status to processing
            self.analysis_model.update_analysis_status(analysis_id, 'processing')
            
            # Update user's GitHub link in profile (if analysis was initiated)
            self.update_user_github_status(user_id, github_username, analysis_completed=False)
            
            # Get GitHub data using GitHub API
            github_data = self._fetch_github_data(github_username)
            
            if 'error' in github_data:
                error_message = github_data['error']
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"GitHub analysis failed for {analysis_id}: {error_message}")
                return
            
            # Get API key from environment
            claude_api_key = os.environ.get('CLAUDE_API_KEY')
            
            if not claude_api_key:
                error_message = "CLAUDE_API_KEY not found"
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"GitHub analysis failed for {analysis_id}: {error_message}")
                return
            
            # Initialize Claude client
            client = ClaudeHTTPClient(claude_api_key)
            
            # Analyze GitHub profile using Claude
            analysis_results, suggestions, grade = self._analyze_github_with_claude(
                client, github_data, user_profile
            )
            
            # Check if analysis was successful
            if isinstance(analysis_results, dict) and 'error' in analysis_results:
                error_message = analysis_results.get('error', 'Unknown analysis error')
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"GitHub analysis failed for {analysis_id}: {error_message}")
                return
            
            # Prepare complete analysis data - FIXED to handle complex data
            complete_data = {
                'analysis_results': self._simplify_analysis_results(analysis_results),
                'suggestions': self._simplify_suggestions(suggestions),
                'grade': int(grade) if isinstance(grade, (int, float)) else 70,
                'github_stats': self._simplify_github_stats(github_data.get('user_stats', {}))
            }
            
            # Update Firebase with analysis results
            self.analysis_model.update_analysis_with_results(analysis_id, complete_data)
            
            # Mark as completed
            self.analysis_model.update_analysis_status(analysis_id, 'completed')
            
            # Update user's GitHub status as completed
            self.update_user_github_status(user_id, github_username, analysis_completed=True)
            
            logger.info(f"GitHub analysis completed successfully for: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error in async GitHub analysis: {e}")
            self.analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        finally:
            # Clean up thread tracking
            if analysis_id in self._processing_threads:
                del self._processing_threads[analysis_id]
    
    def _simplify_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify analysis results for Firestore storage"""
        if not isinstance(analysis_results, dict):
            return {}
        
        simplified = {}
        
        # Extract simple fields
        simple_fields = [
            'overall_score', 'profile_completeness_score', 'repository_quality_score',
            'activity_consistency_score', 'technical_skills_score', 'community_engagement_score',
            'public_repos_count', 'total_stars', 'followers_count', 'account_age_days',
            'grade_explanation'
        ]
        
        for field in simple_fields:
            if field in analysis_results:
                value = analysis_results[field]
                if isinstance(value, (int, float, str, bool)) or value is None:
                    simplified[field] = value
                else:
                    simplified[field] = str(value)
        
        # Handle arrays by converting to simple lists
        if 'strengths' in analysis_results:
            simplified['strengths'] = [str(s) for s in analysis_results['strengths'][:5]]
        
        if 'weaknesses' in analysis_results:
            simplified['weaknesses'] = [str(w) for w in analysis_results['weaknesses'][:5]]
        
        if 'top_languages' in analysis_results:
            top_langs = analysis_results['top_languages']
            if isinstance(top_langs, list):
                simplified['top_languages'] = [str(lang) for lang in top_langs[:5]]
        
        return simplified
    
    def _simplify_suggestions(self, suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify suggestions for Firestore storage"""
        if not isinstance(suggestions, dict):
            return {}
        
        simplified = {}
        
        # Handle improvement suggestions
        if 'improvement_suggestions' in suggestions:
            imp_sugs = suggestions['improvement_suggestions']
            if isinstance(imp_sugs, dict):
                simplified['improvement_suggestions'] = {}
                
                # Handle immediate actions
                if 'immediate_actions' in imp_sugs and isinstance(imp_sugs['immediate_actions'], list):
                    simplified['improvement_suggestions']['immediate_actions'] = []
                    for action in imp_sugs['immediate_actions'][:3]:
                        if isinstance(action, dict):
                            simple_action = {
                                'action': str(action.get('action', ''))[:200],
                                'description': str(action.get('description', ''))[:500],
                                'impact': str(action.get('impact', 'medium'))[:20],
                                'timeframe': str(action.get('timeframe', ''))[:50]
                            }
                            simplified['improvement_suggestions']['immediate_actions'].append(simple_action)
                
                # Handle other suggestion types
                for key in ['repository_improvements', 'skill_development', 'community_engagement']:
                    if key in imp_sugs and isinstance(imp_sugs[key], list):
                        simplified['improvement_suggestions'][key] = []
                        for item in imp_sugs[key][:3]:
                            if isinstance(item, dict):
                                simple_item = {}
                                for k, v in item.items():
                                    if isinstance(v, list):
                                        simple_item[k] = [str(x)[:100] for x in v[:3]]
                                    else:
                                        simple_item[k] = str(v)[:300]
                                simplified['improvement_suggestions'][key].append(simple_item)
        
        # Handle project recommendations
        if 'project_recommendations' in suggestions and isinstance(suggestions['project_recommendations'], list):
            simplified['project_recommendations'] = []
            for project in suggestions['project_recommendations'][:2]:
                if isinstance(project, dict):
                    simple_project = {
                        'project_title': str(project.get('project_title', ''))[:100],
                        'description': str(project.get('description', ''))[:400],
                        'complexity': str(project.get('complexity', 'intermediate'))[:20],
                        'estimated_duration': str(project.get('estimated_duration', ''))[:50],
                        'career_relevance': str(project.get('career_relevance', ''))[:300]
                    }
                    
                    # Handle arrays in projects
                    for array_field in ['technical_skills', 'key_features', 'technologies_to_use', 'learning_outcomes']:
                        if array_field in project and isinstance(project[array_field], list):
                            simple_project[array_field] = [str(x)[:100] for x in project[array_field][:5]]
                    
                    simplified['project_recommendations'].append(simple_project)
        
        # Handle career specific advice
        if 'career_specific_advice' in suggestions and isinstance(suggestions['career_specific_advice'], dict):
            career_advice = suggestions['career_specific_advice']
            simplified['career_specific_advice'] = {}
            
            for key, value in career_advice.items():
                if isinstance(value, list):
                    simplified['career_specific_advice'][key] = [str(x)[:200] for x in value[:5]]
                else:
                    simplified['career_specific_advice'][key] = str(value)[:300]
        
        return simplified
    
    def _simplify_github_stats(self, github_stats: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify GitHub stats for Firestore storage"""
        if not isinstance(github_stats, dict):
            return {}
        
        simplified = {}
        
        # Extract simple numeric and string fields
        simple_fields = [
            'username', 'name', 'bio', 'company', 'location', 'blog',
            'public_repos', 'followers', 'following', 'total_stars', 'total_forks',
            'account_age_days'
        ]
        
        for field in simple_fields:
            if field in github_stats:
                value = github_stats[field]
                if isinstance(value, (int, float)):
                    simplified[field] = value
                elif isinstance(value, str):
                    simplified[field] = value[:200]
                elif value is None:
                    simplified[field] = None
                else:
                    simplified[field] = str(value)[:200]
        
        # Handle dates
        if 'created_at' in github_stats:
            simplified['created_at'] = str(github_stats['created_at'])[:50]
        
        return simplified
    
    def _fetch_github_data(self, github_username: str) -> Dict[str, Any]:
        """Fetch GitHub data using GitHub API"""
        try:
            logger.info(f"Fetching GitHub data for username: {github_username}")
            
            # GitHub API token (optional, for higher rate limits)
            github_token = os.environ.get('GITHUB_TOKEN')
            headers = {}
            if github_token:
                headers['Authorization'] = f'token {github_token}'
            
            # Fetch user profile
            user_url = f"{self.github_api_base}/users/{github_username}"
            user_response = requests.get(user_url, headers=headers, timeout=30)
            
            if user_response.status_code == 404:
                return {'error': f'GitHub user "{github_username}" not found'}
            elif user_response.status_code != 200:
                return {'error': f'GitHub API error: {user_response.status_code}'}
            
            user_data = user_response.json()
            
            # Fetch repositories
            repos_url = f"{self.github_api_base}/users/{github_username}/repos?type=public&sort=updated&per_page=30"
            repos_response = requests.get(repos_url, headers=headers, timeout=30)
            
            if repos_response.status_code != 200:
                repos_data = []
            else:
                repos_data = repos_response.json()
            
            # Process repositories data
            processed_repos = []
            total_stars = 0
            total_forks = 0
            languages_used = {}
            
            for repo in repos_data:
                if not repo.get('fork', False):  # Exclude forked repositories
                    repo_info = {
                        'name': repo.get('name'),
                        'description': repo.get('description'),
                        'language': repo.get('language'),
                        'stars': repo.get('stargazers_count', 0),
                        'forks': repo.get('forks_count', 0),
                        'updated_at': repo.get('updated_at'),
                        'created_at': repo.get('created_at'),
                        'size': repo.get('size', 0),
                        'topics': repo.get('topics', []),
                        'has_readme': bool(repo.get('has_wiki') or repo.get('description'))
                    }
                    processed_repos.append(repo_info)
                    
                    total_stars += repo.get('stargazers_count', 0)
                    total_forks += repo.get('forks_count', 0)
                    
                    # Count languages
                    language = repo.get('language')
                    if language:
                        languages_used[language] = languages_used.get(language, 0) + 1
            
            # Calculate activity metrics
            recent_repos = [repo for repo in processed_repos if repo['updated_at']]
            
            # Compile comprehensive GitHub data
            github_data = {
                'user_stats': {
                    'username': github_username,
                    'name': user_data.get('name'),
                    'bio': user_data.get('bio'),
                    'company': user_data.get('company'),
                    'location': user_data.get('location'),
                    'blog': user_data.get('blog'),
                    'public_repos': user_data.get('public_repos', 0),
                    'followers': user_data.get('followers', 0),
                    'following': user_data.get('following', 0),
                    'created_at': user_data.get('created_at'),
                    'total_stars': total_stars,
                    'total_forks': total_forks,
                    'account_age_days': self._calculate_account_age(user_data.get('created_at'))
                },
                'repository_analysis': {
                    'total_original_repos': len(processed_repos),
                    'languages_used': languages_used,
                    'top_languages': sorted(languages_used.items(), key=lambda x: x[1], reverse=True)[:5],
                    'recent_activity': len([r for r in recent_repos if self._is_recent_activity(r['updated_at'])]),
                    'avg_stars_per_repo': round(total_stars / max(len(processed_repos), 1), 2),
                    'repos_with_description': len([r for r in processed_repos if r['description']]),
                    'repos_with_topics': len([r for r in processed_repos if r['topics']])
                },
                'repositories': processed_repos[:10],
                'profile_completeness': {
                    'has_name': bool(user_data.get('name')),
                    'has_bio': bool(user_data.get('bio')),
                    'has_company': bool(user_data.get('company')),
                    'has_location': bool(user_data.get('location')),
                    'has_blog': bool(user_data.get('blog')),
                    'has_avatar': bool(user_data.get('avatar_url'))
                }
            }
            
            logger.info(f"Successfully fetched GitHub data for {github_username}")
            return github_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching GitHub data: {e}")
            return {'error': f'Network error: {str(e)}'}
        except Exception as e:
            logger.error(f"Error fetching GitHub data: {e}")
            return {'error': f'Data fetch error: {str(e)}'}
    
    def _calculate_account_age(self, created_at: str) -> int:
        """Calculate account age in days"""
        try:
            from datetime import datetime
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            now = datetime.now(created_date.tzinfo)
            return (now - created_date).days
        except:
            return 0
    
    def _is_recent_activity(self, updated_at: str) -> bool:
        """Check if repository has recent activity (within last 6 months)"""
        try:
            from datetime import datetime, timedelta
            updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            six_months_ago = datetime.now(updated_date.tzinfo) - timedelta(days=180)
            return updated_date > six_months_ago
        except:
            return False
    
    def _analyze_github_with_claude(self, client, github_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
        """Analyze GitHub profile using Claude AI - UPDATED with better context"""
        try:
            # Extract user context
            user_profession = user_profile.get('profession', 'Not specified')
            user_career_choices = user_profile.get('career_choices', [])
            user_name = user_profile.get('name', 'User')
            user_college = user_profile.get('college_name', 'Not specified')
            
            # Extract GitHub stats for context
            user_stats = github_data.get('user_stats', {})
            repo_analysis = github_data.get('repository_analysis', {})
            repositories = github_data.get('repositories', [])
            
            # Create a simplified GitHub data summary for the prompt
            github_summary = {
                "user_stats": {
                    "username": user_stats.get('username'),
                    "public_repos": user_stats.get('public_repos', 0),
                    "followers": user_stats.get('followers', 0),
                    "following": user_stats.get('following', 0),
                    "total_stars": user_stats.get('total_stars', 0),
                    "account_age_days": user_stats.get('account_age_days', 0),
                    "has_bio": bool(user_stats.get('bio')),
                    "has_company": bool(user_stats.get('company')),
                    "has_location": bool(user_stats.get('location'))
                },
                "repository_summary": {
                    "total_repos": repo_analysis.get('total_original_repos', 0),
                    "top_languages": repo_analysis.get('top_languages', [])[:3],
                    "recent_activity": repo_analysis.get('recent_activity', 0),
                    "avg_stars": repo_analysis.get('avg_stars_per_repo', 0),
                    "repos_with_description": repo_analysis.get('repos_with_description', 0)
                },
                "sample_repositories": [
                    {
                        "name": repo.get('name'),
                        "language": repo.get('language'),
                        "stars": repo.get('stars', 0),
                        "has_description": bool(repo.get('description'))
                    }
                    for repo in repositories[:5]
                ]
            }
            
            # Create comprehensive prompt for GitHub analysis
            prompt = f"""
            You are an expert software engineering career coach and GitHub profile analyst with deep knowledge of technical hiring and developer career growth.

            **User Context**:
            - Name: {user_name}
            - Profession: {user_profession}
            - Career Interests: {', '.join(user_career_choices) if user_career_choices else 'Not specified'}
            - College: {user_college}

            **GitHub Profile Summary**:
            {json.dumps(github_summary, indent=2)}

            **Analysis Task**: 
            Analyze this GitHub profile and provide a comprehensive assessment with improvement suggestions tailored to their career goals and profession.

            **Return this exact JSON structure**:
            {{
                "overall_score": <number 0-100>,
                "profile_completeness_score": <number 0-100>,
                "repository_quality_score": <number 0-100>,
                "activity_consistency_score": <number 0-100>,
                "technical_skills_score": <number 0-100>,
                "community_engagement_score": <number 0-100>,
                "public_repos_count": {user_stats.get('public_repos', 0)},
                "total_stars": {user_stats.get('total_stars', 0)},
                "followers_count": {user_stats.get('followers', 0)},
                "account_age_days": {user_stats.get('account_age_days', 0)},
                "top_languages": {[lang[0] for lang in repo_analysis.get('top_languages', [])][:3]},
                "strengths": [
                    "specific strength 1 based on their {user_profession} background",
                    "specific strength 2 related to their GitHub activity", 
                    "specific strength 3 considering their career goals"
                ],
                "weaknesses": [
                    "specific weakness 1 that could impact their {user_profession} career",
                    "specific weakness 2 in their GitHub presentation"
                ],
                "grade_explanation": "detailed explanation of the overall score considering their {user_profession} background and career goals"
            }}

            **Guidelines**:
            - Focus on practical, actionable insights for someone in {user_profession}
            - Consider how their GitHub profile supports their career goals in {user_career_choices}
            - Evaluate technical skills demonstration relevant to their profession
            - Assess professional presentation and industry standards
            - Consider their college background: {user_college}

            Return ONLY valid JSON with the exact structure above.
            """

            # Call Claude API
            message = client.messages_create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.3,
                system="You are a GitHub profile analyst and software engineering career coach. Return only valid JSON with the exact structure requested.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract response
            response_text = message.content[0].text
            logger.info("Received GitHub analysis response from Claude API")
            
            # Parse JSON response
            try:
                analysis_data = json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning("Initial JSON parsing failed, attempting to extract JSON from response")
                import re
                json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
                if json_match:
                    try:
                        analysis_data = json.loads(json_match.group(1))
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse extracted JSON: {e}")
                        return self._create_fallback_github_analysis(github_data, user_profile)
                else:
                    logger.error("Could not find JSON block in response")
                    return self._create_fallback_github_analysis(github_data, user_profile)
            
            # Create enhanced suggestions
            suggestions = self._create_enhanced_suggestions(user_profession, user_career_choices, user_stats, repo_analysis)
            
            # Calculate overall grade
            overall_score = analysis_data.get('overall_score', 70)
            
            logger.info(f"Successfully generated GitHub analysis with score: {overall_score}")
            return analysis_data, suggestions, overall_score
            
        except Exception as e:
            logger.error(f"Error in GitHub analysis with Claude: {e}")
            return self._create_fallback_github_analysis(github_data, user_profile)
    
    def _create_enhanced_suggestions(self, user_profession: str, user_career_choices: List[str], user_stats: Dict[str, Any], repo_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced suggestions based on user profile and GitHub data"""
        return {
            "improvement_suggestions": {
                "immediate_actions": [
                    {
                        "action": "Complete GitHub profile information",
                        "description": "Add bio, location, and company information to showcase your professional identity",
                        "impact": "high",
                        "timeframe": "immediate"
                    },
                    {
                        "action": "Add comprehensive README files",
                        "description": "Create detailed README files for all repositories with project descriptions, setup instructions, and usage examples",
                        "impact": "high", 
                        "timeframe": "1-2 weeks"
                    },
                    {
                        "action": "Pin important repositories",
                        "description": "Pin your best repositories that showcase your skills relevant to your career goals",
                        "impact": "medium",
                        "timeframe": "immediate"
                    }
                ],
                "repository_improvements": [
                    {
                        "improvement": "Documentation enhancement",
                        "description": "Improve documentation for all projects with clear explanations",
                        "examples": ["API documentation", "Code comments", "Usage examples"]
                    },
                    {
                        "improvement": "Code quality optimization",
                        "description": "Refactor code to follow best practices and add proper error handling",
                        "examples": ["Clean code principles", "Error handling", "Testing"]
                    }
                ],
                "skill_development": [
                    {
                        "skill": f"Advanced {user_profession} technologies",
                        "relevance": f"Essential for career growth in {user_profession}",
                        "learning_resources": ["Online courses", "Official documentation", "Community tutorials"]
                    },
                    {
                        "skill": "Open source contribution",
                        "relevance": "Demonstrates collaboration skills and community engagement",
                        "learning_resources": ["GitHub guides", "Open source projects", "Contribution guidelines"]
                    }
                ]
            },
            "project_recommendations": [
                {
                    "project_title": f"{user_profession} Portfolio Project",
                    "description": f"Create a comprehensive project that demonstrates your {user_profession} expertise",
                    "technical_skills": [f"Technologies relevant to {user_profession}", "Best practices", "Documentation"],
                    "career_relevance": f"Showcases your capabilities to potential employers in {user_profession}",
                    "complexity": "intermediate",
                    "estimated_duration": "4-6 weeks",
                    "key_features": ["Professional presentation", "Clean code", "Proper documentation"],
                    "learning_outcomes": ["Technical skills", "Project management", "Professional presentation"]
                },
                {
                    "project_title": "Open Source Contribution",
                    "description": "Contribute to open source projects relevant to your field",
                    "technical_skills": ["Collaboration", "Code review", "Version control"],
                    "career_relevance": "Demonstrates ability to work in team environments",
                    "complexity": "beginner",
                    "estimated_duration": "ongoing",
                    "key_features": ["Community engagement", "Code quality", "Documentation"],
                    "learning_outcomes": ["Collaboration skills", "Industry exposure", "Network building"]
                }
            ],
            "career_specific_advice": {
                "for_profession": user_profession,
                "focus_areas": [
                    f"Technologies specifically relevant to {user_profession}",
                    "Industry best practices and standards",
                    "Professional portfolio development"
                ],
                "recommended_technologies": [
                    f"Popular tools in {user_profession}",
                    "Emerging technologies in the field",
                    "Industry-standard frameworks"
                ],
                "networking_opportunities": [
                    "Open source communities",
                    f"{user_profession} focused groups",
                    "Technical conferences and meetups"
                ]
            }
        }
    
    def _create_fallback_github_analysis(self, github_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
        """Create fallback GitHub analysis when AI analysis fails"""
        logger.info("Creating fallback GitHub analysis")
        
        user_stats = github_data.get('user_stats', {})
        repo_analysis = github_data.get('repository_analysis', {})
        user_profession = user_profile.get('profession', 'Developer')
        
        # Calculate basic score
        repo_count = user_stats.get('public_repos', 0)
        stars = user_stats.get('total_stars', 0)
        followers = user_stats.get('followers', 0)
        
        base_score = 50
        base_score += min(repo_count * 2, 20)
        base_score += min(stars, 15)
        base_score += min(followers, 15)
        
        total_score = min(base_score, 100)
        
        fallback_analysis = {
            "overall_score": int(total_score),
            "profile_completeness_score": 70,
            "repository_quality_score": int(min(repo_count * 5, 100)),
            "activity_consistency_score": 60,
            "technical_skills_score": 70,
            "community_engagement_score": int(min((stars + followers) * 2, 100)),
            "public_repos_count": repo_count,
            "total_stars": stars,
            "followers_count": followers,
            "account_age_days": user_stats.get('account_age_days', 0),
            "top_languages": [lang[0] for lang in repo_analysis.get('top_languages', [])][:3],
            "strengths": [
                f"Has {repo_count} public repositories showing active development",
                f"Earned {stars} total stars indicating code quality",
                f"GitHub presence established for {user_profession} career"
            ],
            "weaknesses": [
                "Profile requires comprehensive optimization",
                "Repository documentation could be enhanced"
            ],
            "grade_explanation": f"Score of {total_score} based on {repo_count} repositories, {stars} stars, and {followers} followers. Profile shows potential for {user_profession} career growth with focused improvements."
        }
        
        suggestions = self._create_enhanced_suggestions(
            user_profession,
            user_profile.get('career_choices', []),
            user_stats,
            repo_analysis
        )
        
        return fallback_analysis, suggestions, int(total_score)

# Global service instance
github_service = GitHubAnalyzerService()