# services/resume_questions.py
import json
import os
import logging
import requests
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaudeHTTPClient:
    """
    HTTP-based Claude client to avoid library conflicts
    """
    
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
            
            # Create a simple response object that mimics the anthropic client response
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

def generate_interview_questions_from_data(resume_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate interview questions based on resume data using Claude AI
    
    Args:
        resume_data: Dictionary containing parsed resume data
        
    Returns:
        List of interview questions formatted for the API
    """
    logger.info("Generating interview questions based on resume data")
    
    try:
        # Get API key from environment
        claude_api_key = os.environ.get('CLAUDE_API_KEY')
        
        if not claude_api_key:
            logger.error("CLAUDE_API_KEY not found")
            return create_fallback_questions(resume_data)
        
        # Initialize Claude client
        client = ClaudeHTTPClient(claude_api_key)
        
        # Extract key information for context
        personal_info = resume_data.get('personal_information', {})
        work_experience = resume_data.get('work_experience', [])
        education = resume_data.get('education', [])
        skills = resume_data.get('skills', [])
        projects = resume_data.get('projects', [])
        
        # Create context summary
        context_summary = f"""
        Candidate: {personal_info.get('name', 'Unknown')}
        Skills: {', '.join(skills) if skills else 'Not specified'}
        Experience: {len(work_experience)} work experiences
        Education: {len(education)} educational qualifications
        Projects: {len(projects)} projects
        """
        
        # Construct the prompt
        prompt = f"""
        You are an expert technical interviewer with experience in evaluating candidates across various roles and industries.
        
        Based on the following resume data, generate exactly 5 thoughtful and relevant interview questions that would help assess this candidate's skills and experience.
        
        Resume Context:
        {context_summary}
        
        Detailed Resume Data:
        {json.dumps(resume_data, indent=2)}
        
        Generate questions that are:
        - Specific to the candidate's background and experience
        - Balanced between technical and behavioral aspects
        - Open-ended to encourage detailed responses
        - Relevant to their industry and role type
        
        Return the response as a JSON array with exactly this structure:
        [
            {{
                "topic": "Professional Experience & Domain Knowledge",
                "question": "Question text here",
                "type": "behavioral",
                "difficulty": "medium"
            }},
            {{
                "topic": "Technical & Role-Specific Skills",
                "question": "Question text here", 
                "type": "technical",
                "difficulty": "hard"
            }},
            {{
                "topic": "Leadership & Collaboration",
                "question": "Question text here",
                "type": "behavioral",
                "difficulty": "medium"
            }},
            {{
                "topic": "Problem-Solving & Innovation",
                "question": "Question text here",
                "type": "problem-solving", 
                "difficulty": "hard"
            }},
            {{
                "topic": "Career Development Goals",
                "question": "Question text here",
                "type": "general",
                "difficulty": "easy"
            }}
        ]
        
        Respond with valid JSON array only, no additional text.
        """
        
        # Call Claude API
        message = client.messages_create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.7,
            system="You are an expert interviewer who creates tailored interview questions based on candidate resumes. Return valid JSON only.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract response
        response_text = message.content[0].text
        logger.info("Received response from Claude API")
        
        # Parse JSON response
        try:
            # Try to parse the whole response as JSON
            questions_array = json.loads(response_text)
            logger.info(f"Successfully generated {len(questions_array)} interview questions")
            return questions_array
            
        except json.JSONDecodeError:
            logger.warning("Initial JSON parsing failed, attempting to extract JSON from response")
            # Try to extract JSON from code blocks
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                try:
                    questions_array = json.loads(json_match.group(1))
                    logger.info(f"Successfully extracted {len(questions_array)} interview questions")
                    return questions_array
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {e}")
                    return create_fallback_questions(resume_data)
            else:
                logger.error("Could not find JSON block in response")
                return create_fallback_questions(resume_data)
                
    except Exception as e:
        logger.error(f"Error generating interview questions: {e}")
        return create_fallback_questions(resume_data)

def create_fallback_questions(resume_data: Dict[str, Any]) -> list:
    """
    Create fallback interview questions when AI generation fails
    
    Args:
        resume_data: Dictionary containing parsed resume data
        
    Returns:
        List of fallback interview questions
    """
    logger.info("Creating fallback interview questions")
    
    # Extract basic info
    skills = resume_data.get('skills', [])
    work_exp = resume_data.get('work_experience', [])
    projects = resume_data.get('projects', [])
    
    # Determine experience level
    exp_level = "easy"
    if len(work_exp) > 3:
        exp_level = "hard"
    elif len(work_exp) > 1:
        exp_level = "medium"
    
    # Create basic questions
    questions = [
        {
            "topic": "Professional Experience & Domain Knowledge",
            "question": "Can you walk me through your professional background and what led you to your current career path?",
            "type": "behavioral",
            "difficulty": exp_level
        },
        {
            "topic": "Technical & Role-Specific Skills", 
            "question": f"I see you have experience with {', '.join(skills[:3]) if skills else 'various technologies'}. Can you describe a challenging project where you applied these skills?" if skills else "Tell me about the most challenging technical problem you've solved.",
            "type": "technical",
            "difficulty": exp_level
        },
        {
            "topic": "Leadership & Collaboration",
            "question": "Describe a situation where you had to work closely with team members to achieve a goal. What was your role and how did you contribute?",
            "type": "behavioral", 
            "difficulty": "medium"
        },
        {
            "topic": "Problem-Solving & Innovation",
            "question": "Tell me about a time when you had to solve a complex problem at work. What was your approach and what was the outcome?",
            "type": "problem-solving",
            "difficulty": exp_level
        },
        {
            "topic": "Career Development Goals",
            "question": "What are your career goals for the next 2-3 years, and how does this role align with those aspirations?",
            "type": "general",
            "difficulty": "easy"
        }
    ]
    
    return questions

def run_generation_with_args(resume_file_path: str, output_file_path: str) -> list:
    """
    Main function to generate interview questions from a resume file
    
    Args:
        resume_file_path: Path to the JSON resume file
        output_file_path: Path where to save the generated questions
        
    Returns:
        List of generated interview questions
    """
    try:
        logger.info(f"Processing resume file: {resume_file_path}")
        
        # Read resume data from file
        with open(resume_file_path, 'r', encoding='utf-8') as file:
            resume_data = json.load(file)
        
        # Generate interview questions
        questions_data = generate_interview_questions_from_data(resume_data)
        
        # Save to output file
        try:
            with open(output_file_path, 'w', encoding='utf-8') as file:
                json.dump(questions_data, file, indent=2)
            logger.info(f"Interview questions saved to: {output_file_path}")
        except Exception as e:
            logger.warning(f"Could not save questions to file: {e}")
        
        return questions_data
        
    except FileNotFoundError:
        logger.error(f"Resume file not found: {resume_file_path}")
        return [{"error": f"Resume file not found: {resume_file_path}"}]
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in resume file: {resume_file_path}")
        return [{"error": f"Invalid JSON in resume file: {resume_file_path}"}]
    except Exception as e:
        logger.error(f"Error processing resume: {e}")
        return [{"error": f"Error processing resume: {str(e)}"}]