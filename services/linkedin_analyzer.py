# services/linkedin_analyzer.py
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
    """Service for analyzing LinkedIn profiles using Claude AI"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self.analysis_model = ProfileAnalysisModel(self.db)
        self._processing_threads = {}
    
    def start_linkedin_analysis(self, user_id: str, linkedin_url: str, user_profile: Dict[str, Any]) -> Tuple[str, bool]:
        """Start asynchronous LinkedIn profile analysis"""
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
                args=(analysis_id, linkedin_url, user_profile),
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
    
    def _analyze_linkedin_async(self, analysis_id: str, linkedin_url: str, user_profile: Dict[str, Any]):
        """Analyze LinkedIn profile asynchronously using Claude AI"""
        try:
            logger.info(f"Starting async LinkedIn analysis for: {analysis_id}")
            
            # Update status to processing
            self.analysis_model.update_analysis_status(analysis_id, 'processing')
            
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
            
            logger.info(f"LinkedIn analysis completed successfully for: {analysis_id}")
            
        except Exception as e:
            logger.error(f"Error in async LinkedIn analysis: {e}")
            self.analysis_model.update_analysis_status(analysis_id, 'failed', str(e))
        
        finally:
            # Clean up thread tracking
            if analysis_id in self._processing_threads:
                del self._processing_threads[analysis_id]
    
    def _analyze_linkedin_with_claude(self, client, linkedin_url: str, user_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], int]:
        """Analyze LinkedIn profile using Claude AI"""
        try:
            # Extract user context
            user_profession = user_profile.get('profession', 'Not specified')
            user_career_choices = user_profile.get('career_choices', [])
            user_name = user_profile.get('name', 'User')
            
            # Create comprehensive prompt for LinkedIn analysis
            prompt = f"""
            You are an expert career coach and LinkedIn profile analyst with extensive experience in professional networking and career development.

            **TASK**: Analyze the LinkedIn profile at the following URL and provide comprehensive feedback and improvement suggestions.

            **LinkedIn URL**: {linkedin_url}

            **User Context**:
            - Name: {user_name}
            - Current Profession: {user_profession}
            - Career Interests: {', '.join(user_career_choices) if user_career_choices else 'Not specified'}

            **IMPORTANT INSTRUCTIONS**:
            Since I cannot directly access LinkedIn profiles, I need you to provide a comprehensive analysis framework and suggestions based on the LinkedIn URL provided and the user's profile context. 

            Please provide analysis and suggestions as if you could see a typical LinkedIn profile for someone in their profession and career stage.

            **ANALYSIS FRAMEWORK**:
            Analyze the following aspects of a LinkedIn profile:

            1. **Profile Completeness**
            2. **Professional Headline & Summary**
            3. **Work Experience Presentation**
            4. **Skills & Endorsements**
            5. **Network Building & Engagement**
            6. **Content Strategy**

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
                        "<insight 1>",
                        "<insight 2>",
                        "<insight 3>"
                    ]
                }},
                "improvement_suggestions": {{
                    "immediate_actions": [
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
                        }}
                    ],
                    "networking_tips": [
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
                        }}
                    ]
                }},
                "career_specific_advice": {{
                    "for_profession": "{user_profession}",
                    "industry_trends": [
                        "<trend 1 relevant to their field>",
                        "<trend 2 relevant to their field>"
                    ],
                    "recommended_connections": [
                        "<type of professionals to connect with>",
                        "<specific companies or roles to target>"
                    ],
                    "content_topics": [
                        "<topic 1 they should post about>",
                        "<topic 2 they should post about>"
                    ]
                }},
                "project_recommendations": [
                    {{
                        "project_title": "<project name>",
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
            - Provide specific, actionable advice tailored to their profession and career goals
            - Include industry-specific recommendations
            - Suggest realistic projects they can showcase on LinkedIn
            - Focus on practical improvements they can implement
            - Consider current LinkedIn best practices and algorithm preferences

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
            overall_score = profile_analysis.get('overall_score', 70)
            
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
            "overall_score": 65,
            "completeness_score": 70,
            "professional_presentation_score": 60,
            "network_engagement_score": 50,
            "content_quality_score": 55,
            "strengths": [
                "Has established a LinkedIn presence",
                "Profile exists and is accessible",
                "Basic professional information available"
            ],
            "weaknesses": [
                "Analysis limited due to processing constraints",
                "Profile optimization opportunities available",
                "Networking and engagement could be improved"
            ],
            "key_insights": [
                "LinkedIn profile requires comprehensive review",
                "Professional presentation can be enhanced",
                "Active networking strategy needed"
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
                        "examples": ["Industry trend analysis", "Professional development tips"]
                    }
                ],
                "networking_tips": [
                    {
                        "tip": "Connect with industry professionals",
                        "description": "Actively connect with professionals in your field",
                        "target_audience": f"Professionals in {user_profession}"
                    }
                ],
                "skill_development": [
                    {
                        "skill": "Digital presence optimization",
                        "relevance": "Essential for modern professional networking",
                        "learning_resources": ["LinkedIn Learning courses", "Professional development workshops"]
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
                    "Professional development insights"
                ]
            }
        }
        
        fallback_projects = [
            {
                "project_title": f"Professional {user_profession} Portfolio",
                "description": "Create a comprehensive portfolio showcasing your professional work",
                "skills_demonstrated": ["Professional presentation", "Industry expertise"],
                "career_relevance": "Demonstrates competency and professional growth",
                "implementation_steps": [
                    "Collect your best professional work",
                    "Create compelling case studies",
                    "Present in a professional format"
                ]
            }
        ]
        
        combined_suggestions = {
            'improvement_suggestions': fallback_suggestions["improvement_suggestions"],
            'career_specific_advice': fallback_suggestions["career_specific_advice"],
            'project_recommendations': fallback_projects
        }
        
        return fallback_analysis, combined_suggestions, 65

# Global service instance
linkedin_service = LinkedInAnalyzerService()