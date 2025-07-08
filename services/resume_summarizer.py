# services/resume_summarizer.py
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

def compare_resume_with_job(resume_data: Dict[str, Any], job_description: str) -> Optional[Dict[str, Any]]:
    """
    Compare a resume with a job description using Claude AI to generate a match analysis.
    
    Args:
        resume_data: Dictionary containing parsed resume data
        job_description: String containing the job description
        
    Returns:
        Dictionary containing match analysis or None if there was an error
    """
    logger.info("Starting resume comparison with job description")
    
    try:
        # Get API key from environment
        claude_api_key = os.environ.get('CLAUDE_API_KEY')
        
        if not claude_api_key:
            logger.error("CLAUDE_API_KEY not found")
            return create_fallback_analysis(resume_data, job_description)
        
        # Initialize Claude client with HTTP approach
        client = ClaudeHTTPClient(claude_api_key)
        
        # Extract key information from resume for better analysis
        personal_info = resume_data.get('personal_information', {})
        work_experience = resume_data.get('work_experience', [])
        education = resume_data.get('education', [])
        skills = resume_data.get('skills', [])
        projects = resume_data.get('projects', [])
        certifications = resume_data.get('certifications', [])
        
        # Create a summary of candidate profile
        candidate_summary = f"""
        Candidate: {personal_info.get('name', 'Unknown')}
        Skills: {', '.join(skills) if skills else 'Not specified'}
        Years of Experience: {len(work_experience)} positions
        Education Level: {len(education)} qualifications
        Project Experience: {len(projects)} projects
        Certifications: {len(certifications)} certifications
        """
        
        # Construct the comprehensive prompt for Claude
        prompt = f"""
        You are an expert hiring manager and talent evaluator with 15+ years of experience in recruitment across multiple industries.

        Your task is to analyze how well a candidate's resume matches a specific job description. Evaluate the candidate holistically, considering technical skills, experience level, and overall suitability.

        **JOB DESCRIPTION:**
        {job_description}

        **CANDIDATE PROFILE SUMMARY:**
        {candidate_summary}

        **DETAILED RESUME DATA:**
        {json.dumps(resume_data, indent=2)}

        **SCORING GUIDELINES:**
        - 90-100: Excellent Match - candidate exceeds most requirements
        - 75-89: Good Match - candidate meets most key requirements with minor gaps
        - 60-74: Moderate Match - candidate meets core requirements but has some gaps
        - 40-59: Poor Match - candidate has relevant background but significant gaps
        - 0-39: Very Poor Match - minimal overlap with job requirements

        **OUTPUT FORMAT:**
        Return a JSON object with exactly this structure:
        {{
            "match_score": <number between 0-100>,
            "match_label": "<Excellent Match|Good Match|Moderate Match|Poor Match|Very Poor Match>",
            "summary": "<2-3 sentence overall assessment>",
            "strengths": [
                "<specific strength 1>",
                "<specific strength 2>",
                "<specific strength 3>",
                "<specific strength 4>",
                "<specific strength 5>"
            ],
            "gaps": [
                "<specific gap or concern 1>",
                "<specific gap or concern 2>",
                "<specific gap or concern 3>",
                "<specific gap or concern 4>"
            ]
        }}

        **IMPORTANT GUIDELINES:**
        - Be specific and evidence-based in your analysis
        - Reference actual skills, experiences, and qualifications from the resume
        - Consider both hard skills and soft skills indicators
        - Be constructive in identifying gaps

        Return ONLY the JSON object, no additional text or explanations.
        """

        # Call Claude API
        message = client.messages_create(
            model="claude-3-sonnet-20240229",
            max_tokens=2000,
            temperature=0.3,  # Lower temperature for more consistent analysis
            system="You are an expert hiring manager who provides detailed, fair, and constructive candidate evaluations. Always return valid JSON.",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        
        # Extract content from Claude's response
        response_text = message.content[0].text
        logger.info("Received response from Claude API")
        
        # Parse JSON response
        try:
            # Try to parse the whole response as JSON
            analysis = json.loads(response_text)
            logger.info(f"Successfully generated resume analysis with match score: {analysis.get('match_score', 'N/A')}")
            return analysis
            
        except json.JSONDecodeError:
            logger.warning("Initial JSON parsing failed, attempting to extract JSON from response")
            # Try to extract JSON from code blocks
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(1))
                    logger.info(f"Successfully extracted resume analysis with match score: {analysis.get('match_score', 'N/A')}")
                    return analysis
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse extracted JSON: {e}")
                    return create_fallback_analysis(resume_data, job_description)
            else:
                logger.error("Could not find JSON block in response")
                return create_fallback_analysis(resume_data, job_description)
                
    except Exception as e:
        logger.error(f"Error in resume comparison: {e}")
        return create_fallback_analysis(resume_data, job_description)

def create_fallback_analysis(resume_data: Dict[str, Any], job_description: str) -> Dict[str, Any]:
    """
    Create a basic fallback analysis when AI analysis fails
    
    Args:
        resume_data: Dictionary containing parsed resume data
        job_description: String containing the job description
        
    Returns:
        Dictionary containing basic match analysis
    """
    logger.info("Creating fallback analysis")
    
    # Extract basic information
    skills = resume_data.get('skills', [])
    work_exp = resume_data.get('work_experience', [])
    education = resume_data.get('education', [])
    projects = resume_data.get('projects', [])
    
    # Simple keyword matching for basic analysis
    job_lower = job_description.lower()
    resume_skills_lower = [skill.lower() for skill in skills]
    
    # Count skill matches
    skill_matches = sum(1 for skill in resume_skills_lower if skill in job_lower)
    skill_match_ratio = skill_matches / max(len(skills), 1) if skills else 0
    
    # Basic scoring logic
    base_score = 40  # Base score
    
    # Add points for experience
    if len(work_exp) > 0:
        base_score += min(len(work_exp) * 10, 30)
    
    # Add points for education
    if len(education) > 0:
        base_score += min(len(education) * 5, 15)
    
    # Add points for skills match
    base_score += skill_match_ratio * 30
    
    # Add points for projects
    if len(projects) > 0:
        base_score += min(len(projects) * 5, 15)
    
    # Cap at 100
    match_score = min(base_score, 100)
    
    # Determine match label
    if match_score >= 80:
        match_label = "Good Match"
    elif match_score >= 60:
        match_label = "Moderate Match"
    elif match_score >= 40:
        match_label = "Poor Match"
    else:
        match_label = "Very Poor Match"
    
    return {
        "match_score": int(match_score),
        "match_label": match_label,
        "summary": f"Basic analysis shows a {match_label.lower()} based on {len(work_exp)} work experiences, {len(skills)} listed skills, and {skill_matches} skill matches with the job description.",
        "strengths": [
            f"Has {len(work_exp)} work experiences" if work_exp else "Entry-level candidate",
            f"Lists {len(skills)} relevant skills" if skills else "Developing skill set",
            f"Educational background with {len(education)} qualifications" if education else "Building educational foundation",
            f"Project experience with {len(projects)} projects" if projects else "Gaining practical experience",
            "Potential for growth and development"
        ][:5],
        "gaps": [
            "Limited skill alignment analysis due to processing constraints",
            "Detailed experience relevance needs manual review",
            "Industry-specific requirements need closer evaluation",
            "Soft skills assessment requires interview evaluation"
        ]
    }

def resume_job_match_analysis(resume_file_path: str, job_description: str) -> Optional[Dict[str, Any]]:
    """
    Process a resume file and compare it with a job description.
    
    Args:
        resume_file_path: Path to the JSON resume file
        job_description: String containing the job description
        
    Returns:
        Dictionary containing match analysis or None if there was an error
    """
    try:
        logger.info(f"Processing resume file: {resume_file_path}")
        
        # Validate inputs
        if not job_description or not job_description.strip():
            logger.warning("No job description provided")
            return create_fallback_analysis({}, "")
        
        # Read resume data from file
        with open(resume_file_path, 'r', encoding='utf-8') as file:
            resume_data = json.load(file)
        
        # Validate resume data
        if not isinstance(resume_data, dict):
            logger.error("Invalid resume data format")
            return create_fallback_analysis({}, job_description)
        
        # Compare resume with job description
        result = compare_resume_with_job(resume_data, job_description)
        
        return result
        
    except FileNotFoundError:
        logger.error(f"Resume file not found: {resume_file_path}")
        return create_fallback_analysis({}, job_description)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in resume file: {resume_file_path}")
        return create_fallback_analysis({}, job_description)
    except Exception as e:
        logger.error(f"Error processing resume: {e}")
        return create_fallback_analysis({}, job_description)