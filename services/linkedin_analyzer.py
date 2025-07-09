import os
import json
import threading
import logging
import requests
from typing import Dict, Any, Optional, Tuple
from config.firebase_config import firebase_config
from models.profile_analysis_model import ProfileAnalysisModel

logger = logging.getLogger(__name__)

class ClaudeHTTPClient:
    """HTTP-based Claude client for LinkedIn analysis"""
    
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

class LinkedInAnalyzerService:
    """Service for analyzing LinkedIn profiles using Claude AI - UPDATED for profile completion integration"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self.analysis_model = ProfileAnalysisModel(self.db)
        self._processing_threads = {}
    
    def update_user_linkedin_status(self, user_id: str, linkedin_url: str, analysis_completed: bool = False):
        """Update user's LinkedIn link in profile and recalculate completion"""
        try:
            from models.user_model import UserModel
            user_model = UserModel(self.db)
            
            # Get current user
            user = user_model.get_user_by_id(user_id)
            if not user:
                logger.error(f"User {user_id} not found for LinkedIn update")
                return
            
            current_profile = user.get('profile', {})
            old_completion = current_profile.get('completion_status', 0)
            
            # Update LinkedIn link if not already set or different
            current_linkedin = current_profile.get('linkedin_link', '')
            if current_linkedin != linkedin_url:
                update_data = {
                    'profile.linkedin_link': linkedin_url,
                    'updated_at': user_model.db.SERVER_TIMESTAMP if hasattr(user_model.db, 'SERVER_TIMESTAMP') else None
                }
                
                # Recalculate completion
                updated_profile = current_profile.copy()
                updated_profile['linkedin_link'] = linkedin_url
                
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
                        
                        logger.info(f"LinkedIn analysis XP bonus: {xp_bonus} for user {user_id}")
                
                # Apply update
                success = user_model.update_user(user_id, update_data)
                if success:
                    logger.info(f"Updated LinkedIn link for user {user_id}: {linkedin_url}")
                    logger.info(f"Completion updated: {old_completion}% -> {new_completion}%")
                
        except Exception as e:
            logger.error(f"Error updating LinkedIn status for user {user_id}: {e}")
    
    def start_linkedin_analysis(self, user_id: str, linkedin_url: str, user_profile: Dict[str, Any]) -> Tuple[str, bool]:
        """Start asynchronous LinkedIn profile analysis - UPDATED"""
        try:
            # Create initial analysis record
            analysis_data = {
                'analysis_type': 'linkedin',
                'profile_url': linkedin_url,
                'user_profile_context': user_profile
            }
            
            analysis_id = self.analysis_model.create_analysis_record(user_id, analysis_data)
            
            # Start processing in background thread
            processing_thread = threading.Thread(
                target=self._analyze_linkedin_async,
                args=(analysis_id, user_id, linkedin_url, user_profile),
                daemon=True
            )
            processing_thread.start()
            
            # Track the thread
            self._processing_threads[analysis_id] = processing_thread
            
            logger.info(f"Started LinkedIn analysis for analysis_id: {analysis_id}")
            return analysis_id, True
            
        except Exception as e:
            logger.error(f"Error starting LinkedIn analysis: {e}")
            return "", False
    
    def _analyze_linkedin_async(self, analysis_id: str, user_id: str, linkedin_url: str, user_profile: Dict[str, Any]):
        """Analyze LinkedIn profile asynchronously using Claude AI - UPDATED"""
        try:
            logger.info(f"Starting async LinkedIn analysis for: {analysis_id}")
            
            # Update status to processing
            self.analysis_model.update_analysis_status(analysis_id, 'processing')
            
            # Update user's LinkedIn link in profile (if analysis was initiated)
            self.update_user_linkedin_status(user_id, linkedin_url, analysis_completed=False)
            
            # Get API key from environment
            claude_api_key = os.environ.get('CLAUDE_API_KEY')
            
            if not claude_api_key:
                error_message = "CLAUDE_API_KEY not found"
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"LinkedIn analysis failed for {analysis_id}: {error_message}")
                return
            
            # Initialize Claude client
            client = ClaudeHTTPClient(claude_api_key)
            
            # Analyze LinkedIn profile using Claude
            analysis_results, suggestions, grade = self._analyze_linkedin_with_claude(
                client, linkedin_url, user_profile
            )
            
            # Check if analysis was successful
            if isinstance(analysis_results, dict) and 'error' in analysis_results:
                error_message = analysis_results.get('error', 'Unknown analysis error')
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"LinkedIn analysis failed for {analysis_id}: {error_message}")
                return
            
            # Prepare complete analysis data
            complete_data = {
                'analysis_results': analysis_results,
                'suggestions': suggestions,
                'grade': grade
            }
            
            # Update Firebase with analysis results
            self.analysis_model.update_analysis_with_results(analysis_id, complete_data)
            
            # Mark as completed
            self.analysis_model.update_analysis_status(analysis_id, 'completed')
            
            # Update user's LinkedIn status as completed
            self.update_user_linkedin_status(user_id, linkedin_url, analysis_completed=True)
            
            logger.info(f"LinkedIn analysis completed successfully for: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error in async LinkedIn analysis: {e}")
            self.analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        finally:
            # Clean up thread tracking
            if analysis_id in self._processing_threads:
                del self._processing_threads[analysis_id]
    
    def _analyze_linkedin_with_claude(self, client, linkedin_url: str, user_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
        """Analyze LinkedIn profile using Claude AI - UPDATED with better context"""
        try:
            # Extract user context
            user_profession = user_profile.get('profession', 'Not specified')
            user_career_choices = user_profile.get('career_choices', [])
            user_name = user_profile.get('name', 'User')
            user_college = user_profile.get('college_name', 'Not specified')
            
            # Create comprehensive prompt for LinkedIn analysis
            prompt = f"""
            You are an expert career coach and LinkedIn profile analyst with extensive experience in professional networking and career development.

            **TASK**: Analyze the LinkedIn profile and provide comprehensive feedback and improvement suggestions.

            **LinkedIn URL**: {linkedin_url}

            **User Context**:
            - Name: {user_name}
            - Current Profession: {user_profession}
            - Career Interests: {', '.join(user_career_choices) if user_career_choices else 'Not specified'}
            - College: {user_college}

            **IMPORTANT INSTRUCTIONS**:
            Since I cannot directly access LinkedIn profiles, I need you to provide a comprehensive analysis framework and suggestions based on the LinkedIn URL provided and the user's profile context. 

            Analyze as if this were a typical LinkedIn profile for someone in their profession and career stage, and provide actionable recommendations.

            **ANALYSIS FRAMEWORK**:
            Analyze the following aspects of a LinkedIn profile:

            1. **Profile Completeness & Professional Presentation**
            2. **Headline & Summary Optimization**
            3. **Experience Section & Achievements**
            4. **Skills & Endorsements Strategy**
            5. **Network Building & Engagement**
            6. **Content Strategy & Thought Leadership**

            **OUTPUT FORMAT**:
            Return a JSON object with exactly this structure:

            {{
                "profile_analysis": {{
                    "overall_score": <number 0-100>,
                    "completeness_score": <number 0-100>,
                    "professional_presentation_score": <number 0-100>,
                    "network_engagement_score": <number 0-100>,
                    "content_quality_score": <number 0-100>,
                    "strengths": [
                        "<specific strength 1>",
                        "<specific strength 2>",
                        "<specific strength 3>"
                    ],
                    "weaknesses": [
                        "<specific weakness 1>",
                        "<specific weakness 2>",
                        "<specific weakness 3>"
                    ],
                    "key_insights": [
                        "<actionable insight 1>",
                        "<actionable insight 2>",
                        "<actionable insight 3>"
                    ]
                }},
                "improvement_suggestions": {{
                    "immediate_actions": [
                        {{
                            "action": "<specific action>",
                            "description": "<detailed description>",
                            "impact": "<high/medium/low>",
                            "timeframe": "<immediate/1-2 weeks/1 month>"
                        }},
                        {{
                            "action": "<specific action>",
                            "description": "<detailed description>",
                            "impact": "<high/medium/low>",
                            "timeframe": "<immediate/1-2 weeks/1 month>"
                        }},
                        {{
                            "action": "<specific action>",
                            "description": "<detailed description>",
                            "impact": "<high/medium/low>",
                            "timeframe": "<immediate/1-2 weeks/1 month>"
                        }}
                    ],
                    "content_strategy": [
                        {{
                            "strategy": "<content strategy>",
                            "description": "<how to implement>",
                            "examples": ["<example 1>", "<example 2>"]
                        }},
                        {{
                            "strategy": "<content strategy>",
                            "description": "<how to implement>",
                            "examples": ["<example 1>", "<example 2>"]
                        }}
                    ],
                    "networking_tips": [
                        {{
                            "tip": "<networking tip>",
                            "description": "<implementation details>",
                            "target_audience": "<who to connect with>"
                        }},
                        {{
                            "tip": "<networking tip>",
                            "description": "<implementation details>",
                            "target_audience": "<who to connect with>"
                        }}
                    ],
                    "skill_development": [
                        {{
                            "skill": "<skill to develop>",
                            "relevance": "<why important for their career>",
                            "learning_resources": ["<resource 1>", "<resource 2>"]
                        }},
                        {{
                            "skill": "<skill to develop>",
                            "relevance": "<why important for their career>",
                            "learning_resources": ["<resource 1>", "<resource 2>"]
                        }}
                    ]
                }},
                "career_specific_advice": {{
                    "for_profession": "{user_profession}",
                    "industry_trends": [
                        "<trend 1 relevant to {user_profession}>",
                        "<trend 2 relevant to {user_profession}>"
                    ],
                    "recommended_connections": [
                        "<type of professionals to connect with>",
                        "<specific companies or roles to target>"
                    ],
                    "content_topics": [
                        "<topic 1 they should post about>",
                        "<topic 2 they should post about>",
                        "<topic 3 they should post about>"
                    ]
                }},
                "project_recommendations": [
                    {{
                        "project_title": "<project name for {user_profession}>",
                        "description": "<what the project involves>",
                        "skills_demonstrated": ["<skill 1>", "<skill 2>"],
                        "career_relevance": "<how it helps their career goals>",
                        "implementation_steps": [
                            "<step 1>",
                            "<step 2>",
                            "<step 3>"
                        ]
                    }},
                    {{
                        "project_title": "<project name for {user_profession}>",
                        "description": "<what the project involves>",
                        "skills_demonstrated": ["<skill 1>", "<skill 2>"],
                        "career_relevance": "<how it helps their career goals>",
                        "implementation_steps": [
                            "<step 1>",
                            "<step 2>",
                            "<step 3>"
                        ]
                    }}
                ]
            }}

            **GUIDELINES**:
            - Provide specific, actionable advice tailored to {user_profession} and their career goals
            - Include industry-specific recommendations for {user_profession}
            - Suggest realistic projects they can showcase on LinkedIn
            - Focus on practical improvements they can implement
            - Consider current LinkedIn best practices and algorithm preferences
            - Tailor suggestions to their college background: {user_college}

            Return ONLY the JSON object with no additional text.
            """

            # Call Claude API
            message = client.messages_create(
                model="claude-3-sonnet-20240229",
                max_tokens=4000,
                temperature=0.3,
                system="You are an expert LinkedIn profile analyst and career coach. You provide comprehensive, actionable advice for professional development. Always return valid JSON.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract response
            response_text = message.content[0].text
            logger.info("Received LinkedIn analysis response from Claude API")
            
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
                        return self._create_fallback_linkedin_analysis(user_profile)
                else:
                    logger.error("Could not find JSON block in response")
                    return self._create_fallback_linkedin_analysis(user_profile)
            
            # Extract components
            profile_analysis = analysis_data.get('profile_analysis', {})
            improvement_suggestions = analysis_data.get('improvement_suggestions', {})
            career_advice = analysis_data.get('career_specific_advice', {})
            project_recommendations = analysis_data.get('project_recommendations', [])
            
            # Calculate overall grade
            overall_score = profile_analysis.get('overall_score', 75)
            
            # Combine all suggestions
            combined_suggestions = {
                'improvement_suggestions': improvement_suggestions,
                'career_specific_advice': career_advice,
                'project_recommendations': project_recommendations
            }
            
            logger.info(f"Successfully generated LinkedIn analysis with score: {overall_score}")
            return profile_analysis, combined_suggestions, overall_score
            
        except Exception as e:
            logger.error(f"Error in LinkedIn analysis with Claude: {e}")
            return self._create_fallback_linkedin_analysis(user_profile)
    
    def _create_fallback_linkedin_analysis(self, user_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
        """Create fallback LinkedIn analysis when AI analysis fails"""
        logger.info("Creating fallback LinkedIn analysis")
        
        user_profession = user_profile.get('profession', 'Professional')
        user_career_choices = user_profile.get('career_choices', [])
        
        fallback_analysis = {
            "overall_score": 75,
            "completeness_score": 70,
            "professional_presentation_score": 75,
            "network_engagement_score": 70,
            "content_quality_score": 65,
            "strengths": [
                "LinkedIn profile established and accessible",
                f"Profile indicates {user_profession} background",
                "Ready for professional networking optimization"
            ],
            "weaknesses": [
                "Requires comprehensive profile review",
                "Professional presentation can be enhanced",
                "Networking strategy needs development"
            ],
            "key_insights": [
                "LinkedIn is crucial for professional networking",
                "Profile optimization can significantly impact career opportunities",
                "Regular engagement increases professional visibility"
            ]
        }
        
        fallback_suggestions = {
            "improvement_suggestions": {
                "immediate_actions": [
                    {
                        "action": "Complete all profile sections",
                        "description": "Ensure all LinkedIn sections are filled out completely",
                        "impact": "high",
                        "timeframe": "1-2 weeks"
                    },
                    {
                        "action": "Update professional headline",
                        "description": "Create a compelling headline that showcases your value proposition",
                        "impact": "high",
                        "timeframe": "immediate"
                    },
                    {
                        "action": "Write engaging summary",
                        "description": "Craft a professional summary that tells your career story",
                        "impact": "high",
                        "timeframe": "1 week"
                    }
                ],
                "content_strategy": [
                    {
                        "strategy": "Regular industry insights sharing",
                        "description": "Share relevant industry news and insights weekly",
                        "examples": [f"{user_profession} industry trends", "Professional development tips"]
                    },
                    {
                        "strategy": "Thought leadership content",
                        "description": "Create original content about your expertise",
                        "examples": ["Career advice posts", "Industry analysis"]
                    }
                ],
                "networking_tips": [
                    {
                        "tip": "Connect with industry professionals",
                        "description": "Actively connect with professionals in your field",
                        "target_audience": f"Professionals in {user_profession}"
                    },
                    {
                        "tip": "Engage with others' content",
                        "description": "Comment meaningfully on posts from your network",
                        "target_audience": "Industry peers and leaders"
                    }
                ],
                "skill_development": [
                    {
                        "skill": "Digital presence optimization",
                        "relevance": "Essential for modern professional networking",
                        "learning_resources": ["LinkedIn Learning courses", "Professional development workshops"]
                    },
                    {
                        "skill": "Content creation",
                        "relevance": "Builds thought leadership and visibility",
                        "learning_resources": ["Writing workshops", "Content strategy courses"]
                    }
                ]
            },
            "career_specific_advice": {
                "for_profession": user_profession,
                "industry_trends": [
                    f"Stay updated with {user_profession} industry developments",
                    "Network with industry leaders and peers"
                ],
                "recommended_connections": [
                    f"Senior {user_profession} professionals",
                    "Industry thought leaders and influencers"
                ],
                "content_topics": [
                    f"{user_profession} best practices",
                    "Professional development insights",
                    "Industry trends and analysis"
                ]
            }
        }
        
        fallback_projects = [
            {
                "project_title": f"Professional {user_profession} Portfolio",
                "description": "Create a comprehensive LinkedIn portfolio showcasing your work",
                "skills_demonstrated": ["Professional presentation", "Industry expertise"],
                "career_relevance": "Demonstrates competency and professional growth",
                "implementation_steps": [
                    "Curate your best professional work",
                    "Create compelling project descriptions",
                    "Share projects as LinkedIn posts"
                ]
            },
            {
                "project_title": f"{user_profession} Thought Leadership Series",
                "description": "Develop a series of posts about your professional expertise",
                "skills_demonstrated": ["Thought leadership", "Content creation"],
                "career_relevance": "Establishes expertise and builds professional network",
                "implementation_steps": [
                    "Identify key topics in your field",
                    "Research and write insightful posts",
                    "Engage with responses and build discussions"
                ]
            }
        ]
        
        combined_suggestions = {
            'improvement_suggestions': fallback_suggestions["improvement_suggestions"],
            'career_specific_advice': fallback_suggestions["career_specific_advice"],
            'project_recommendations': fallback_projects
        }
        
        return fallback_analysis, combined_suggestions, 75

# Global service instance
linkedin_service = LinkedInAnalyzerService()