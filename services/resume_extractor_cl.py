# services/resume_extractor_cl.py
import os
import json
import PyPDF2
import time
import re
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure upload folder
UPLOAD_FOLDER = 'uploads/resumes'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

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
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response content: {e.response.text}")
            raise Exception(f"Claude API request failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Claude API call: {e}")
            raise

def get_claude_client():
    """
    Create and return a Claude client with HTTP fallback
    """
    try:
        # Get API key from environment
        claude_api_key = os.environ.get('CLAUDE_API_KEY')
        
        if not claude_api_key:
            raise ValueError("CLAUDE_API_KEY not found in environment variables")
        
        if not claude_api_key.startswith('sk-ant-'):
            raise ValueError("Invalid CLAUDE_API_KEY format. Should start with 'sk-ant-'")
        
        # Use HTTP client directly to avoid library conflicts
        client = ClaudeHTTPClient(claude_api_key)
        logger.info("Claude HTTP client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize Claude client: {e}")
        raise Exception(f"Could not initialize Claude client: {e}")

def verify_resume_with_claude(client, pdf_text):
    """
    Use Claude to verify if the document appears to be a resume
    """
    logger.info("Verifying document is a resume...")
    verification_start = time.time()
    
    try:
        verification_message = client.messages_create(
            model="claude-3-sonnet-20240229",
            max_tokens=150,
            system="You are an expert at identifying resumes from document text.",
            messages=[
                {
                    "role": "user", 
                    "content": f"""Here is text extracted from a document. Analyze it and determine if it appears to be a resume/CV.

                      TEXT:
                      {pdf_text[:2000]}

                      Is this document a resume/CV? Respond with a JSON object containing:
                      1. "is_resume": true or false
                      2. "confidence": a score from 0-100
                      3. "reason": brief explanation for your determination

                      Return ONLY the JSON object with no additional text."""
                }
            ]
        )
        
        verification_time = time.time() - verification_start
        logger.info(f"Verification completed in {verification_time:.2f} seconds")
        
        verification_text = verification_message.content[0].text
        
        try:
            if "```json" in verification_text:
                json_match = re.search(r'```json\n([\s\S]*?)\n```', verification_text)
                if json_match:
                    verification_text = json_match.group(1)
            verification_result = json.loads(verification_text)
            logger.info(f"Verification result: {'Resume' if verification_result['is_resume'] else 'Not a resume'} (Confidence: {verification_result['confidence']}%)")
            return verification_result
        except (json.JSONDecodeError, AttributeError) as e:
            logger.error(f"Error parsing verification response: {e}")
            default_result = {"is_resume": True, "confidence": 50, "reason": "Verification response parsing failed, proceeding with caution"}
            return default_result
            
    except Exception as e:
        logger.error(f"Error in resume verification: {e}")
        return {"is_resume": True, "confidence": 30, "reason": f"Verification failed: {str(e)}, proceeding with caution"}

def extract_resume_details(resume_file_path):
    """
    Extract structured details from a resume using Claude
    """
    logger.info("Starting Resume Parsing Process")
    
    try:
        # Initialize client with proper error handling
        client = get_claude_client()
        
        # Extract text from PDF
        logger.info("Extracting text from PDF...")
        text_extraction_start = time.time()
        
        pdf_text = ""
        try:
            with open(resume_file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                for page_num in range(len(pdf_reader.pages)):
                    page = pdf_reader.pages[page_num]
                    pdf_text += page.extract_text()
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return {"error": f"PDF extraction failed: {str(e)}"}, None, 0
        
        if not pdf_text.strip():
            return {"error": "No text could be extracted from the PDF"}, None, 0
        
        text_extraction_time = time.time() - text_extraction_start
        logger.info(f"Text extraction completed in {text_extraction_time:.2f} seconds")
        logger.info(f"Extracted {len(pdf_text)} characters from PDF")
        
        # Verify the document is a resume
        verification_result = verify_resume_with_claude(client, pdf_text)
        
        if not verification_result['is_resume'] and verification_result['confidence'] > 70:
            return verification_result, None, 0
        
        # Create the JSON structure template
        json_structure = """
        {
          "personal_information": {
            "name": "",
            "email": "",
            "phone": "",
            "city": "",
            "country": ""
          },
          "summary": "",
          "education": [
            {
              "school": "",
              "degree": "",
              "start_year": "",
              "end_year": "",
              "major": "",
              "gpa": ""
            }
          ],
          "work_experience": [
            {
              "company": "",
              "role": "",
              "start_year": "",
              "end_year": "",
              "city": "",
              "country": "",
              "description": ""
            }
          ],
          "projects": [
            {
              "name": "",
              "start_year": "",
              "end_year": "",
              "description": ""
            }
          ],
          "certifications": [
            {
              "name": "",
              "issuer": "",
              "date": "",
              "id": ""
            }
          ],
          "awards": [
            {
              "title": "",
              "issuer": "",
              "year": ""
            }
          ],
          "skills": [],
          "is_resume": true
        }
        """
        
        # Send the text to Claude
        logger.info("Sending request to Claude API for resume parsing...")
        api_call_start = time.time()
        
        try:
            message = client.messages_create(
                model="claude-3-sonnet-20240229",
                max_tokens=4096,
                system="You are an expert resume parser that extracts structured information from resumes. You will return the parsed data in valid JSON format ONLY. No explanations or other text.",
                messages=[
                    {
                        "role": "user", 
                        "content": f"""Here is the resume text extracted from a PDF:

{pdf_text}

Extract the following information from the resume and return it as a JSON object with the following structure:

{json_structure}

If any field is not present in the resume, use null or an empty string as appropriate. Do not make up information. Extract information directly from the resume. Return ONLY the JSON with no additional text or explanations."""
                    }
                ]
            )
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return {"error": f"Claude API call failed: {str(e)}"}, None, 0
        
        api_response_time = time.time() - api_call_start
        logger.info(f"Claude API response received in {api_response_time:.2f} seconds")
        
        # Extract the JSON content
        response_text = message.content[0].text
        
        # Parse the JSON response
        try:
            parsed_json = json.loads(response_text)
            logger.info("Successfully parsed JSON response")
        except json.JSONDecodeError:
            logger.warning("Initial JSON parsing failed, attempting to extract JSON from response...")
            json_match = re.search(r'```json\n([\s\S]*?)\n```', response_text)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group(1))
                    logger.info("Successfully extracted and parsed JSON from response")
                except json.JSONDecodeError:
                    logger.error("Could not parse extracted JSON")
                    return {"error": "Could not parse JSON from Claude's response", "raw_response": response_text}, None, 0
            else:
                logger.error("Could not find JSON block in response")
                return {"error": "Could not find JSON in Claude's response", "raw_response": response_text}, None, 0
        
        # Save the extracted data to a JSON file
        logger.info("Saving extracted data to JSON file...")
        filename_without_ext = os.path.splitext(os.path.basename(resume_file_path))[0]
        json_output_path = os.path.join(UPLOAD_FOLDER, f"{filename_without_ext}_extracted_resume.json")
        
        try:
            with open(json_output_path, 'w', encoding='utf-8') as json_file:
                json.dump(parsed_json, json_file, indent=2)
            logger.info(f"Extracted resume data saved to: {json_output_path}")
        except Exception as e:
            logger.warning(f"Could not save JSON file: {e}")
            json_output_path = None
        
        logger.info("Resume Parsing Complete")
        return parsed_json, json_output_path, 1
        
    except Exception as e:
        logger.error(f"Unexpected error in extract_resume_details: {e}")
        return {"error": f"Resume extraction failed: {str(e)}"}, None, 0

def process_resume_file(file_path, job_description=""):
    """
    Process a resume file and extract structured information
    
    Args:
        file_path: Path to the resume file
        job_description: Job description for matching analysis
        
    Returns:
        Tuple containing (extracted_resume, questions, summary)
    """
    try:
        logger.info(f"Processing resume file: {file_path}")
        
        # Extract resume details
        extracted_resume, json_output_path, flag = extract_resume_details(file_path)
        
        if flag == 0:
            return extracted_resume, None, None
        
        # Generate interview questions
        try:
            from services.resume_questions import generate_interview_questions_from_data
            questions = generate_interview_questions_from_data(extracted_resume)
        except ImportError:
            logger.warning("resume_questions module not found, skipping question generation")
            questions = None
        except Exception as e:
            logger.error(f"Error generating questions: {e}")
            questions = None
        
        # Generate job match summary if job description is provided
        summary = None
        if job_description and job_description.strip():
            try:
                from services.resume_summarizer import compare_resume_with_job
                summary = compare_resume_with_job(extracted_resume, job_description)
            except ImportError:
                logger.warning("resume_summarizer module not found, skipping job match analysis")
            except Exception as e:
                logger.error(f"Error in job match analysis: {e}")
                summary = None
        
        return extracted_resume, questions, summary
        
    except Exception as e:
        logger.error(f"Error processing resume file: {e}")
        return {"error": f"Resume processing failed: {str(e)}"}, None, None