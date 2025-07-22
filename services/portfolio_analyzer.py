import os
import json
import threading
import logging
import requests
from typing import Dict, Any, Optional, Tuple, List
from config.firebase_config import firebase_config
from models.portfolio_analysis_model import PortfolioAnalysisModel
from services.task_manager import task_manager
from bs4 import BeautifulSoup
import time
import re

logger = logging.getLogger(__name__)

class ClaudeHTTPClient:
    """Simple HTTP client for Claude API"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.anthropic.com/v1/messages"
    
    def messages_create(self, model, max_tokens, system=None, messages=None, temperature=None):
        """Create a message with Claude API"""
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        data = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": messages or []
        }
        
        if system:
            data["system"] = system
        if temperature:
            data["temperature"] = temperature
        
        try:
            response = requests.post(self.base_url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            # Create a simple response object to match the expected interface
            response_data = response.json()
            content = response_data.get('content', [{}])[0]
            
            class SimpleContent:
                def __init__(self, text):
                    self.text = text
            
            class SimpleResponse:
                def __init__(self, data):
                    self.content = [SimpleContent(data.get('text', ''))]
            
            return SimpleResponse(content)
            
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

class PortfolioAnalyzerService:
    """Service for analyzing portfolio websites using web scraping and Claude AI with enhanced parallel processing"""
    
    def __init__(self):
        self.db = firebase_config.get_db()
        self.analysis_model = PortfolioAnalysisModel(self.db)
    
    def start_portfolio_analysis(self, user_id: str, portfolio_url: str, user_profile: Dict[str, Any]) -> Tuple[str, bool]:
        """Start asynchronous portfolio analysis using task manager"""
        try:
            # Create initial analysis record
            analysis_data = {
                'analysis_type': 'portfolio',
                'portfolio_url': portfolio_url,
                'user_profile_context': user_profile
            }
            
            analysis_id = self.analysis_model.create_analysis_record(user_id, analysis_data)
            
            # Prepare task data
            task_data = {
                'analysis_id': analysis_id,
                'portfolio_url': portfolio_url,
                'user_profile': user_profile
            }
            
            # Start task using task manager
            task_id = task_manager.start_task(
                task_type='portfolio',
                user_id=user_id,
                task_data=task_data,
                processing_func=self._analyze_portfolio_task,
                analysis_id=analysis_id,
                portfolio_url=portfolio_url,
                user_profile=user_profile
            )
            
            if not task_id:
                # Clean up analysis record if task failed to start
                self.analysis_model.delete_analysis(analysis_id)
                return "", False
            
            logger.info(f"Started portfolio analysis for user {user_id}, task_id: {task_id}, analysis_id: {analysis_id}")
            return task_id, True
            
        except Exception as e:
            logger.error(f"Error starting portfolio analysis: {e}")
            return "", False
    
    def _analyze_portfolio_task(self, task_id: str, user_id: str, analysis_id: str, portfolio_url: str, user_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze portfolio website asynchronously - called by task manager"""
        try:
            logger.info(f"Starting portfolio analysis task {task_id} for analysis {analysis_id}")
            
            # Update status to processing
            self.analysis_model.update_analysis_status(analysis_id, 'processing')
            
            # Validate portfolio URL
            if not portfolio_url or not portfolio_url.strip():
                error_message = "Portfolio URL is required for analysis"
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: {error_message}")
                return {'status': 'failed', 'error': error_message}
            
            # Validate URL format
            if not portfolio_url.startswith(('http://', 'https://')):
                error_message = "Please provide a valid URL starting with http:// or https://"
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: Invalid URL format")
                return {'status': 'failed', 'error': error_message}
            
            # Extract website data
            try:
                extracted_data = self._extract_website_data(portfolio_url)
            except Exception as e:
                error_message = f"Failed to extract website data: {str(e)}"
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: {error_message}")
                return {'status': 'failed', 'error': error_message}
            
            if 'error' in extracted_data:
                error_message = extracted_data['error']
                
                # Provide more specific error messages
                if "not found" in error_message.lower() or "404" in error_message:
                    error_message = "Portfolio website not found. Please check the URL and ensure the website is accessible."
                elif "timeout" in error_message.lower():
                    error_message = "Website took too long to respond. Please try again or check if the website is down."
                elif "connection" in error_message.lower() or "network" in error_message.lower():
                    error_message = "Network connection issue. Please check your internet connection and try again."
                elif "ssl" in error_message.lower() or "certificate" in error_message.lower():
                    error_message = "SSL certificate issue. Please check if the website has a valid SSL certificate."
                elif "blocked" in error_message.lower() or "forbidden" in error_message.lower():
                    error_message = "Access to the website is blocked or restricted. Please ensure the website allows web scraping."
                
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: {error_message}")
                return {'status': 'failed', 'error': error_message}
            
            # Validate extracted data
            if not extracted_data or not isinstance(extracted_data, dict):
                error_message = "Failed to extract meaningful data from the website. Please ensure it's a valid portfolio website."
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Invalid extracted data for {analysis_id}")
                return {'status': 'failed', 'error': error_message}
            
            # Get API key from environment
            claude_api_key = os.environ.get('CLAUDE_API_KEY')
            
            if not claude_api_key:
                error_message = "AI analysis service is not configured. Please contact support."
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: {error_message}")
                return {'status': 'failed', 'error': error_message}
            
            # Initialize Claude client
            try:
                client = ClaudeHTTPClient(claude_api_key)
            except Exception as e:
                error_message = f"Failed to initialize AI service: {str(e)}"
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: {error_message}")
                return {'status': 'failed', 'error': error_message}
            
            # Analyze portfolio using Claude
            try:
                analysis_results, suggestions, score, score_breakdown = self._analyze_portfolio_with_claude(
                    client, extracted_data, user_profile
                )
            except Exception as e:
                error_message = f"Analysis processing failed: {str(e)}"
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: {error_message}")
                return {'status': 'failed', 'error': error_message}
            
            # Check if analysis was successful
            if isinstance(analysis_results, dict) and 'error' in analysis_results:
                error_message = analysis_results.get('error', 'Unknown analysis error')
                
                # Provide more specific error messages
                if "API rate limit" in error_message.lower():
                    error_message = "Analysis service is temporarily busy. Please try again in a few minutes."
                elif "timeout" in error_message.lower():
                    error_message = "Analysis took too long to complete. Please try again."
                
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Portfolio analysis failed for {analysis_id}: {error_message}")
                return {'status': 'failed', 'error': error_message}
            
            # Validate analysis results
            if not analysis_results or not isinstance(analysis_results, dict):
                error_message = "Failed to generate analysis results. Please try again."
                self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
                logger.error(f"Invalid analysis results for {analysis_id}")
                return {'status': 'failed', 'error': error_message}
            
            # Prepare complete analysis data
            complete_data = {
                'extracted_data': self._simplify_extracted_data(extracted_data),
                'analysis_results': self._simplify_analysis_results(analysis_results),
                'suggestions': self._simplify_suggestions(suggestions),
                'score': int(score) if isinstance(score, (int, float)) else 70,
                'score_breakdown': self._simplify_score_breakdown(score_breakdown)
            }
            
            # Update Firebase with analysis results
            self.analysis_model.update_analysis_with_results(analysis_id, complete_data)
            
            # Mark as completed
            self.analysis_model.update_analysis_status(analysis_id, 'completed')
            
            logger.info(f"Portfolio analysis completed successfully for: {analysis_id}")
            
            return {
                'status': 'completed',
                'analysis_id': analysis_id,
                'extracted_data': extracted_data,
                'analysis_results': analysis_results,
                'suggestions': suggestions,
                'score': score,
                'score_breakdown': score_breakdown
            }
            
        except Exception as e:
            logger.error(f"Error in portfolio analysis task: {e}")
            error_message = f"Unexpected error during analysis: {str(e)}"
            self.analysis_model.update_analysis_status(analysis_id, 'failed', error_message)
            return {'status': 'failed', 'error': error_message}
    
    def get_processing_status(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get processing status of user's latest portfolio analysis task"""
        try:
            # Get latest portfolio task for user
            latest_task = task_manager.get_latest_task(user_id, 'portfolio')
            
            if not latest_task:
                return None
            
            task_id = latest_task['id']
            status_data = task_manager.get_task_status(task_id)
            
            if not status_data:
                return None
            
            # Get analysis details
            analysis_id = latest_task.get('task_data', {}).get('analysis_id')
            analysis_data = None
            if analysis_id:
                analysis_data = self.analysis_model.get_analysis_by_id(analysis_id)
            
            return {
                'task_id': task_id,
                'analysis_id': analysis_id,
                'status': status_data.get('status'),
                'progress': status_data.get('progress', 0),
                'created_at': status_data.get('created_at'),
                'started_at': status_data.get('started_at'),
                'completed_at': status_data.get('completed_at'),
                'error_message': status_data.get('error_message'),
                'portfolio_url': latest_task.get('task_data', {}).get('portfolio_url', ''),
                'is_active': status_data.get('is_active', False)
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio processing status: {e}")
            return None
    
    def get_analysis_results(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get complete portfolio analysis results for user's latest analysis"""
        try:
            # Get latest portfolio task for user
            latest_task = task_manager.get_latest_task(user_id, 'portfolio')
            
            if not latest_task:
                return None
            
            task_id = latest_task['id']
            analysis_id = latest_task.get('task_data', {}).get('analysis_id')
            
            if not analysis_id:
                return None
            
            # Check if task is completed
            if latest_task.get('status') != 'completed':
                return {
                    'status': latest_task.get('status', 'unknown'),
                    'progress': latest_task.get('progress', 0),
                    'message': 'Portfolio analysis not completed yet'
                }
            
            # Get analysis data
            analysis_data = self.analysis_model.get_analysis_by_id(analysis_id)
            if not analysis_data or analysis_data.get('user_id') != user_id:
                return None
            
            if analysis_data.get('status') != 'completed':
                return {
                    'status': analysis_data.get('status', 'unknown'),
                    'message': 'Portfolio analysis not completed yet'
                }
            
            return {
                'status': 'completed',
                'task_id': task_id,
                'analysis_id': analysis_id,
                'portfolio_url': analysis_data.get('portfolio_url', ''),
                'score': analysis_data.get('score'),
                'score_breakdown': analysis_data.get('score_breakdown'),
                'analysis_results': analysis_data.get('analysis_results'),
                'extracted_data': analysis_data.get('extracted_data'),
                'suggestions': analysis_data.get('suggestions'),
                'processed_at': analysis_data.get('processed_at')
            }
            
        except Exception as e:
            logger.error(f"Error getting portfolio analysis results: {e}")
            return None
    
    def _extract_website_data(self, portfolio_url: str) -> Dict[str, Any]:
        """Extract comprehensive data from portfolio website"""
        try:
            logger.info(f"Extracting data from portfolio: {portfolio_url}")
            
            # Set up headers to mimic a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            # Fetch the main page
            response = requests.get(portfolio_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                return {'error': f'Website returned status code: {response.status_code}'}
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract comprehensive website data
            website_data = {
                'url': portfolio_url,
                'title': self._extract_title(soup),
                'meta_description': self._extract_meta_description(soup),
                'personal_information': self._extract_personal_info(soup, portfolio_url),
                'about_section': self._extract_about_section(soup),
                'projects': self._extract_projects(soup, portfolio_url),
                'work_experience': self._extract_work_experience(soup),
                'education': self._extract_education(soup),
                'skills': self._extract_skills(soup),
                'contact_information': self._extract_contact_info(soup),
                'social_links': self._extract_social_links(soup, portfolio_url),
                'technical_details': self._extract_technical_details(soup, response),
                'content_analysis': self._analyze_content_structure(soup),
                'seo_analysis': self._analyze_seo_elements(soup),
                'design_elements': self._analyze_design_elements(soup),
                'navigation': self._extract_navigation(soup),
                'testimonials': self._extract_testimonials(soup),
                'certifications': self._extract_certifications(soup),
                'blog_posts': self._extract_blog_posts(soup, portfolio_url),
                'extracted_at': time.time()
            }
            
            logger.info(f"Successfully extracted data from {portfolio_url}")
            return website_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error extracting portfolio data: {e}")
            return {'error': f'Network error: {str(e)}'}
        except Exception as e:
            logger.error(f"Error extracting portfolio data: {e}")
            return {'error': f'Data extraction error: {str(e)}'}
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract website title"""
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()
        
        # Try h1 as fallback
        h1_tag = soup.find('h1')
        if h1_tag:
            return h1_tag.get_text().strip()
        
        return "No title found"
    
    def _extract_meta_description(self, soup: BeautifulSoup) -> str:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '').strip()
        return ""
    
    def _extract_personal_info(self, soup: BeautifulSoup, base_url: str) -> Dict[str, Any]:
        """Extract personal information"""
        personal_info = {
            'name': '',
            'title': '',
            'location': '',
            'email': '',
            'phone': '',
            'profile_image': ''
        }
        
        # Try to find name from various elements
        name_selectors = [
            'h1.name', '.name', '#name', 
            'h1:first-of-type', '.hero h1', '.intro h1',
            '.about h1', '.profile h1', '.header h1'
        ]
        
        for selector in name_selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                name_text = element.get_text().strip()
                # Filter out common non-name text
                if len(name_text) < 100 and not any(word in name_text.lower() for word in ['welcome', 'hello', 'portfolio', 'developer', 'designer']):
                    personal_info['name'] = name_text
                    break
        
        # Try to find professional title
        title_selectors = [
            '.title', '.job-title', '.profession', '.role',
            'h2:first-of-type', '.hero h2', '.intro h2',
            '.subtitle', '.tagline'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element and element.get_text().strip():
                title_text = element.get_text().strip()
                if len(title_text) < 200:
                    personal_info['title'] = title_text
                    break
        
        # Extract email using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        page_text = soup.get_text()
        email_matches = re.findall(email_pattern, page_text)
        if email_matches:
            # Filter out common non-personal emails
            for email in email_matches:
                if not any(word in email.lower() for word in ['noreply', 'support', 'info', 'admin', 'contact']):
                    personal_info['email'] = email
                    break
        
        # Extract phone number
        phone_pattern = r'[\+]?[1-9]?[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
        phone_matches = re.findall(phone_pattern, page_text)
        if phone_matches:
            personal_info['phone'] = phone_matches[0]
        
        # Extract location
        location_selectors = ['.location', '.city', '.address', '.geo']
        for selector in location_selectors:
            element = soup.select_one(selector)
            if element:
                location_text = element.get_text().strip()
                if len(location_text) < 100:
                    personal_info['location'] = location_text
                    break
        
        # Extract profile image
        img_selectors = [
            '.profile-image img', '.avatar img', '.headshot img',
            '.about img', '.hero img', '.intro img', '.profile img'
        ]
        
        for selector in img_selectors:
            img = soup.select_one(selector)
            if img and img.get('src'):
                src = img.get('src')
                if src and not src.startswith('data:'):  # Skip base64 images
                    personal_info['profile_image'] = urljoin(base_url, src)
                    break
        
        return personal_info
    
    def _extract_about_section(self, soup: BeautifulSoup) -> str:
        """Extract about/bio section"""
        about_selectors = [
            '.about', '#about', '.bio', '#bio',
            '.introduction', '.summary', '.description',
            '.about-me', '.personal', '.story'
        ]
        
        for selector in about_selectors:
            about_section = soup.select_one(selector)
            if about_section:
                # Get text but preserve some structure
                text = about_section.get_text(separator=' ', strip=True)
                if len(text) > 50:  # Only return if substantial content
                    return text[:2000]  # Limit length
        
        # Try to find bio in paragraphs
        paragraphs = soup.find_all('p')
        for p in paragraphs:
            text = p.get_text().strip()
            if len(text) > 100 and any(word in text.lower() for word in ['i am', 'i\'m', 'my name', 'passionate', 'experience']):
                return text[:2000]
        
        return ""
    
    def _extract_projects(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, Any]]:
        """Extract projects/portfolio items"""
        projects = []
        
        project_selectors = [
            '.project', '.portfolio-item', '.work-item',
            '.case-study', '.project-card', '.work',
            '.portfolio-piece', '.project-container'
        ]
        
        for selector in project_selectors:
            project_elements = soup.select(selector)
            for element in project_elements[:15]:  # Limit to 15 projects
                project = {
                    'title': '',
                    'description': '',
                    'technologies': [],
                    'link': '',
                    'image': '',
                    'category': '',
                    'github_link': '',
                    'demo_link': ''
                }
                
                # Extract title
                title_selectors = ['h1', 'h2', 'h3', 'h4', '.title', '.name', '.project-title']
                for title_sel in title_selectors:
                    title_elem = element.find(title_sel)
                    if title_elem:
                        project['title'] = title_elem.get_text().strip()
                        break
                
                # Extract description
                desc_selectors = ['.description', '.summary', 'p', '.project-desc', '.content']
                for desc_sel in desc_selectors:
                    desc_elem = element.find(desc_sel)
                    if desc_elem:
                        project['description'] = desc_elem.get_text().strip()[:500]
                        break
                
                # Extract links
                links = element.find_all('a')
                for link in links:
                    href = link.get('href')
                    if href:
                        full_url = urljoin(base_url, href)
                        link_text = link.get_text().lower()
                        
                        if 'github' in full_url.lower() or 'github' in link_text:
                            project['github_link'] = full_url
                        elif 'demo' in link_text or 'live' in link_text or 'view' in link_text:
                            project['demo_link'] = full_url
                        elif not project['link']:
                            project['link'] = full_url
                
                # Extract image
                img_elem = element.find('img')
                if img_elem and img_elem.get('src'):
                    src = img_elem.get('src')
                    if src and not src.startswith('data:'):
                        project['image'] = urljoin(base_url, src)
                
                # Extract technologies (look for tech-related keywords)
                project_text = element.get_text().lower()
                tech_keywords = [
                    'react', 'javascript', 'python', 'java', 'node.js', 'html', 'css',
                    'angular', 'vue', 'django', 'flask', 'mongodb', 'sql', 'aws',
                    'docker', 'kubernetes', 'git', 'typescript', 'php', 'laravel',
                    'next.js', 'express', 'postgresql', 'mysql', 'redis', 'graphql',
                    'swift', 'kotlin', 'flutter', 'react native', 'firebase'
                ]
                
                found_techs = []
                for tech in tech_keywords:
                    if tech in project_text:
                        found_techs.append(tech.title())
                
                project['technologies'] = found_techs[:8]  # Limit to 8
                
                # Extract category
                category_indicators = ['web', 'mobile', 'desktop', 'api', 'frontend', 'backend', 'fullstack']
                for category in category_indicators:
                    if category in project_text:
                        project['category'] = category
                        break
                
                if project['title']:  # Only add if has title
                    projects.append(project)
        
        return projects
    
    def _extract_work_experience(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract work experience"""
        experience = []
        
        exp_selectors = [
            '.experience', '.work-experience', '.employment',
            '.job', '.position', '.career', '.work-history',
            '.experience-item', '.job-item'
        ]
        
        for selector in exp_selectors:
            exp_section = soup.select_one(selector)
            if exp_section:
                exp_items = exp_section.find_all(['div', 'li', 'article', 'section'])
                
                for item in exp_items[:8]:  # Limit to 8 positions
                    exp_item = {
                        'title': '',
                        'company': '',
                        'duration': '',
                        'description': '',
                        'location': ''
                    }
                    
                    # Try to extract structured information
                    text = item.get_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # Look for specific selectors within the item
                    title_elem = item.find(['.title', '.job-title', '.position', 'h3', 'h4'])
                    if title_elem:
                        exp_item['title'] = title_elem.get_text().strip()[:100]
                    elif len(lines) >= 1:
                        exp_item['title'] = lines[0][:100]
                    
                    company_elem = item.find(['.company', '.employer', '.organization'])
                    if company_elem:
                        exp_item['company'] = company_elem.get_text().strip()[:100]
                    elif len(lines) >= 2:
                        exp_item['company'] = lines[1][:100]
                    
                    duration_elem = item.find(['.duration', '.period', '.date', '.time'])
                    if duration_elem:
                        exp_item['duration'] = duration_elem.get_text().strip()[:50]
                    elif len(lines) >= 3:
                        # Look for date patterns
                        for line in lines:
                            if re.search(r'\d{4}|present|current', line.lower()):
                                exp_item['duration'] = line[:50]
                                break
                    
                    desc_elem = item.find(['.description', '.summary', 'p'])
                    if desc_elem:
                        exp_item['description'] = desc_elem.get_text().strip()[:500]
                    else:
                        exp_item['description'] = text[:500]
                    
                    if exp_item['title'] and len(exp_item['title']) > 2:
                        experience.append(exp_item)
        
        return experience
    
    def _extract_education(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract education information"""
        education = []
        
        edu_selectors = [
            '.education', '#education', '.academic',
            '.degree', '.university', '.school',
            '.education-item', '.study'
        ]
        
        for selector in edu_selectors:
            edu_section = soup.select_one(selector)
            if edu_section:
                edu_items = edu_section.find_all(['div', 'li', 'article'])
                
                for item in edu_items[:5]:  # Limit to 5 education entries
                    edu_item = {
                        'degree': '',
                        'institution': '',
                        'year': '',
                        'description': '',
                        'major': '',
                        'gpa': ''
                    }
                    
                    text = item.get_text()
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    
                    # Look for specific elements
                    degree_elem = item.find(['.degree', '.qualification', 'h3', 'h4'])
                    if degree_elem:
                        edu_item['degree'] = degree_elem.get_text().strip()[:100]
                    elif len(lines) >= 1:
                        edu_item['degree'] = lines[0][:100]
                    
                    institution_elem = item.find(['.institution', '.university', '.school', '.college'])
                    if institution_elem:
                        edu_item['institution'] = institution_elem.get_text().strip()[:100]
                    elif len(lines) >= 2:
                        edu_item['institution'] = lines[1][:100]
                    
                    # Look for years
                    year_pattern = r'20\d{2}|19\d{2}'
                    for line in lines:
                        year_match = re.search(year_pattern, line)
                        if year_match:
                            edu_item['year'] = year_match.group()
                            break
                    
                    edu_item['description'] = text[:300]
                    
                    if edu_item['degree'] and len(edu_item['degree']) > 2:
                        education.append(edu_item)
        
        return education
    
    def _extract_skills(self, soup: BeautifulSoup) -> List[str]:
        """Extract skills/technologies"""
        skills = set()
        
        # Look for skills sections
        skill_selectors = [
            '.skills', '#skills', '.technologies', '.tech-stack',
            '.expertise', '.competencies', '.abilities',
            '.skill-list', '.tech-list'
        ]
        
        for selector in skill_selectors:
            skills_section = soup.select_one(selector)
            if skills_section:
                # Extract from list items
                skill_items = skills_section.find_all(['li', 'span', '.skill', '.tag', '.tech', '.badge'])
                for item in skill_items:
                    skill_text = item.get_text().strip()
                    if skill_text and len(skill_text) < 50 and skill_text not in ['Skills', 'Technologies', 'Expertise']:
                        skills.add(skill_text)
        
        # Also extract from common technology keywords in the page
        page_text = soup.get_text().lower()
        tech_keywords = [
            # Programming Languages
            'python', 'javascript', 'java', 'typescript', 'php', 'ruby', 'c++', 'c#',
            'swift', 'kotlin', 'go', 'rust', 'scala', 'r', 'matlab',
            
            # Frontend
            'react', 'angular', 'vue', 'html', 'css', 'sass', 'less', 'bootstrap',
            'tailwind', 'material-ui', 'chakra', 'styled-components',
            
            # Backend
            'node.js', 'express', 'django', 'flask', 'laravel', 'spring', 'rails',
            'fastapi', 'nestjs', 'koa', 'gin',
            
            # Databases
            'mongodb', 'mysql', 'postgresql', 'redis', 'elasticsearch', 'sqlite',
            'firebase', 'dynamodb', 'cassandra',
            
            # Cloud & DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'gitlab',
            'github actions', 'terraform', 'ansible',
            
            # Mobile
            'react native', 'flutter', 'ionic', 'xamarin',
            
            # Tools & Others
            'git', 'webpack', 'babel', 'jest', 'cypress', 'selenium', 'figma',
            'photoshop', 'sketch', 'adobe xd'
        ]
        
        for keyword in tech_keywords:
            if keyword in page_text:
                skills.add(keyword.title())
        
        # Clean up skills list
        cleaned_skills = []
        for skill in skills:
            # Remove duplicates and clean formatting
            clean_skill = skill.strip().title()
            if clean_skill and len(clean_skill) > 1 and clean_skill not in cleaned_skills:
                cleaned_skills.append(clean_skill)
        
        return cleaned_skills[:25]  # Limit to 25 skills
    
    def _extract_contact_info(self, soup: BeautifulSoup) -> Dict[str, str]:
        """Extract contact information"""
        contact = {
            'email': '',
            'phone': '',
            'location': '',
            'website': ''
        }
        
        # Extract from contact section
        contact_selectors = [
            '.contact', '#contact', '.contact-info',
            '.footer', '.header', '.contact-details'
        ]
        
        for selector in contact_selectors:
            contact_section = soup.select_one(selector)
            if contact_section:
                text = contact_section.get_text()
                
                # Extract email
                email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                email_matches = re.findall(email_pattern, text)
                if email_matches and not contact['email']:
                    contact['email'] = email_matches[0]
                
                # Extract phone
                phone_pattern = r'[\+]?[1-9]?[0-9]{3}[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}'
                phone_matches = re.findall(phone_pattern, text)
                if phone_matches and not contact['phone']:
                    contact['phone'] = phone_matches[0]
        
        return contact
    
    def _extract_social_links(self, soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
        """Extract social media links"""
        social_links = {}
        
        # Common social media platforms
        social_platforms = {
            'linkedin': ['linkedin.com'],
            'github': ['github.com'],
            'twitter': ['twitter.com', 'x.com'],
            'instagram': ['instagram.com'],
            'facebook': ['facebook.com'],
            'youtube': ['youtube.com'],
            'behance': ['behance.net'],
            'dribbble': ['dribbble.com'],
            'medium': ['medium.com'],
            'dev.to': ['dev.to'],
            'stackoverflow': ['stackoverflow.com']
        }
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href')
            if href:
                # Convert relative URLs to absolute
                try:
                    full_url = urljoin(base_url, href)
                    
                    # Check if it matches any social platform
                    for platform, domains in social_platforms.items():
                        if any(domain in full_url.lower() for domain in domains):
                            if platform not in social_links:  # Avoid duplicates
                                social_links[platform] = full_url
                            break
                except:
                    continue
        
        return social_links
    
    def _extract_technical_details(self, soup: BeautifulSoup, response) -> Dict[str, Any]:
        """Extract technical website details"""
        return {
            'has_responsive_design': self._check_responsive_design(soup),
            'load_time': response.elapsed.total_seconds(),
            'has_https': response.url.startswith('https'),
            'page_size_kb': round(len(response.content) / 1024, 2),
            'external_links_count': len([a for a in soup.find_all('a', href=True) 
                                       if a.get('href').startswith('http') and 
                                       urlparse(a.get('href')).netloc != urlparse(response.url).netloc]),
            'internal_links_count': len([a for a in soup.find_all('a', href=True) 
                                       if not a.get('href').startswith('http') or 
                                       urlparse(a.get('href')).netloc == urlparse(response.url).netloc]),
            'images_count': len(soup.find_all('img')),
            'has_favicon': bool(soup.find('link', rel='icon') or soup.find('link', rel='shortcut icon')),
            'has_custom_css': bool(soup.find('link', rel='stylesheet') or soup.find('style')),
            'has_javascript': bool(soup.find('script')),
            'meta_tags_count': len(soup.find_all('meta'))
        }
    
    def _check_responsive_design(self, soup: BeautifulSoup) -> bool:
        """Check if website has responsive design indicators"""
        # Check for viewport meta tag
        viewport = soup.find('meta', attrs={'name': 'viewport'})
        if viewport:
            return True
        
        # Check for responsive CSS classes
        responsive_classes = ['responsive', 'mobile', 'tablet', 'desktop', 'container', 'row', 'col', 'grid']
        for element in soup.find_all(class_=True):
            classes = ' '.join(element.get('class', [])).lower()
            if any(resp_class in classes for resp_class in responsive_classes):
                return True
        
        # Check for CSS media queries
        style_tags = soup.find_all('style')
        for style in style_tags:
            if '@media' in style.get_text():
                return True
        
        return False
    
    def _analyze_content_structure(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze content structure and quality"""
        return {
            'has_header': bool(soup.find('header') or soup.find('.header') or soup.find('#header')),
            'has_navigation': bool(soup.find('nav') or soup.find('.nav') or soup.find('.navigation')),
            'has_footer': bool(soup.find('footer') or soup.find('.footer') or soup.find('#footer')),
            'has_main_content': bool(soup.find('main') or soup.find('.main') or soup.find('#main')),
            'heading_structure': {
                'h1_count': len(soup.find_all('h1')),
                'h2_count': len(soup.find_all('h2')),
                'h3_count': len(soup.find_all('h3')),
                'h4_count': len(soup.find_all('h4'))
            },
            'content_sections': len(soup.find_all(['section', 'article', '.section', '.content-section'])),
            'word_count': len(soup.get_text().split()),
            'paragraph_count': len(soup.find_all('p')),
            'list_count': len(soup.find_all(['ul', 'ol'])),
            'has_call_to_action': bool(soup.find_all(text=lambda text: text and 
                                     any(cta in text.lower() for cta in ['contact', 'hire', 'download', 'view', 'get in touch']))),
            'semantic_elements': len(soup.find_all(['header', 'nav', 'main', 'section', 'article', 'aside', 'footer']))
        }
    
    def _analyze_seo_elements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze SEO elements"""
        title_tag = soup.find('title')
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        
        return {
            'has_title': bool(title_tag),
            'title_length': len(title_tag.get_text()) if title_tag else 0,
            'has_meta_description': bool(meta_desc),
            'meta_description_length': len(meta_desc.get('content')) if meta_desc else 0,
            'has_h1': bool(soup.find('h1')),
            'h1_count': len(soup.find_all('h1')),
            'alt_text_coverage': len([img for img in soup.find_all('img') if img.get('alt')]) / 
                               max(len(soup.find_all('img')), 1),
            'has_canonical': bool(soup.find('link', rel='canonical')),
            'has_robots_meta': bool(soup.find('meta', attrs={'name': 'robots'})),
            'has_og_tags': bool(soup.find('meta', attrs={'property': lambda x: x and x.startswith('og:')})),
            'has_twitter_cards': bool(soup.find('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})),
            'internal_links': len([a for a in soup.find_all('a', href=True) if not a.get('href').startswith('http')]),
            'external_links': len([a for a in soup.find_all('a', href=True) if a.get('href').startswith('http')])
        }
    
    def _analyze_design_elements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Analyze design and UX elements"""
        return {
            'has_custom_css': bool(soup.find('link', rel='stylesheet') or soup.find('style')),
            'has_animations': bool(soup.find_all(class_=lambda x: x and 
                                 any(anim in ' '.join(x).lower() for anim in ['animate', 'fade', 'slide', 'transition']))),
            'css_frameworks': self._detect_css_frameworks(soup),
            'color_scheme': 'unknown',  # Would need more complex analysis
            'font_usage': len(set([elem.get('style', '') for elem in soup.find_all() if elem.get('style') and 'font' in elem.get('style')])),
            'layout_type': 'multi-column' if soup.find_all(class_=lambda x: x and 
                          any(col in ' '.join(x).lower() for col in ['col', 'column', 'grid'])) else 'single-column',
            'has_hero_section': bool(soup.find_all(class_=lambda x: x and 'hero' in ' '.join(x).lower())),
            'button_count': len(soup.find_all(['button', '.btn', '.button'])),
            'form_count': len(soup.find_all('form'))
        }
    
    def _detect_css_frameworks(self, soup: BeautifulSoup) -> List[str]:
        """Detect CSS frameworks used"""
        frameworks = []
        page_content = str(soup).lower()
        
        framework_indicators = {
            'bootstrap': ['bootstrap', 'btn-', 'col-', 'row', 'container'],
            'tailwind': ['tailwind', 'bg-', 'text-', 'p-', 'm-', 'flex'],
            'bulma': ['bulma', 'is-', 'has-'],
            'foundation': ['foundation', 'large-', 'medium-', 'small-'],
            'materialize': ['materialize', 'material'],
            'semantic-ui': ['semantic', 'ui ']
        }
        
        for framework, indicators in framework_indicators.items():
            if any(indicator in page_content for indicator in indicators):
                frameworks.append(framework)
        
        return frameworks
    
    def _extract_navigation(self, soup: BeautifulSoup) -> List[str]:
        """Extract navigation menu items"""
        nav_items = []
        
        nav_selectors = ['nav', '.nav', '.navigation', '.menu', 'header ul', '.navbar']
        
        for selector in nav_selectors:
            nav = soup.select_one(selector)
            if nav:
                links = nav.find_all('a')
                for link in links:
                    text = link.get_text().strip()
                    if text and len(text) < 50 and text not in nav_items:
                        nav_items.append(text)
                if nav_items:  # Stop after finding first nav
                    break
        
        return nav_items[:10]  # Limit to 10 items
    
    def _extract_testimonials(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract testimonials/reviews"""
        testimonials = []
        
        testimonial_selectors = [
            '.testimonial', '.review', '.recommendation',
            '.feedback', '.client-review', '.quote',
            '.testimonials .item', '.reviews .item'
        ]
        
        for selector in testimonial_selectors:
            testimonial_elements = soup.select(selector)
            for element in testimonial_elements[:5]:  # Limit to 5
                testimonial = {
                    'text': '',
                    'author': '',
                    'position': '',
                    'company': ''
                }
                
                # Extract text
                text_elem = element.find(['p', '.text', '.quote', '.content'])
                if text_elem:
                    testimonial['text'] = text_elem.get_text().strip()[:500]
                else:
                    # Get all text if no specific element
                    all_text = element.get_text().strip()
                    if len(all_text) > 20:
                        testimonial['text'] = all_text[:500]
                
                # Extract author
                author_elem = element.find(['.author', '.name', '.client', '.by'])
                if author_elem:
                    testimonial['author'] = author_elem.get_text().strip()
                
                # Extract position/company
                position_elem = element.find(['.position', '.title', '.company', '.role'])
                if position_elem:
                    testimonial['position'] = position_elem.get_text().strip()
                
                if testimonial['text'] and len(testimonial['text']) > 20:
                    testimonials.append(testimonial)
        
        return testimonials
    
    def _extract_certifications(self, soup: BeautifulSoup) -> List[str]:
        """Extract certifications/credentials"""
        certifications = []
        
        cert_selectors = [
            '.certification', '.certificate', '.credential',
            '.award', '.achievement', '.cert',
            '.certifications .item', '.awards .item'
        ]
        
        for selector in cert_selectors:
            cert_elements = soup.select(selector)
            for element in cert_elements:
                cert_text = element.get_text().strip()
                if cert_text and len(cert_text) < 200 and cert_text not in certifications:
                    certifications.append(cert_text)
        
        # Also look for certification keywords in text
        page_text = soup.get_text()
        cert_keywords = [
            'certified', 'certification', 'aws certified', 'google certified',
            'microsoft certified', 'oracle certified', 'cisco certified',
            'pmp', 'scrum master', 'agile', 'comptia'
        ]
        
        for keyword in cert_keywords:
            if keyword in page_text.lower():
                # Try to extract the full certification name
                sentences = page_text.split('.')
                for sentence in sentences:
                    if keyword in sentence.lower() and len(sentence) < 200:
                        cert_name = sentence.strip()
                        if cert_name not in certifications:
                            certifications.append(cert_name)
        
        return certifications[:10]  # Limit to 10
    
    def _extract_blog_posts(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract blog posts/articles"""
        blog_posts = []
        
        blog_selectors = [
            '.blog-post', '.article', '.post',
            '.news-item', '.blog-item', '.entry',
            '.blog .item', '.articles .item'
        ]
        
        for selector in blog_selectors:
            post_elements = soup.select(selector)
            for element in post_elements[:5]:  # Limit to 5
                post = {
                    'title': '',
                    'excerpt': '',
                    'link': '',
                    'date': '',
                    'category': ''
                }
                
                # Extract title
                title_elem = element.find(['h1', 'h2', 'h3', '.title', '.post-title'])
                if title_elem:
                    post['title'] = title_elem.get_text().strip()
                
                # Extract excerpt
                excerpt_elem = element.find(['.excerpt', '.summary', 'p', '.description'])
                if excerpt_elem:
                    post['excerpt'] = excerpt_elem.get_text().strip()[:300]
                
                # Extract link
                link_elem = element.find('a')
                if link_elem and link_elem.get('href'):
                    post['link'] = urljoin(base_url, link_elem.get('href'))
                
                # Extract date
                date_elem = element.find(['.date', '.published', '.time', '.post-date'])
                if date_elem:
                    post['date'] = date_elem.get_text().strip()
                
                # Extract category
                category_elem = element.find(['.category', '.tag', '.post-category'])
                if category_elem:
                    post['category'] = category_elem.get_text().strip()
                
                if post['title']:
                    blog_posts.append(post)
        
        return blog_posts
    
    def _analyze_portfolio_with_claude(self, client, extracted_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], int, Dict[str, Any]]:
        """Analyze portfolio using Claude AI"""
        try:
            # Extract user context
            user_profession = user_profile.get('profession', 'Not specified')
            user_career_choices = user_profile.get('career_choices', [])
            user_name = user_profile.get('name', 'User')
            
            # Create a simplified data summary for the prompt
            portfolio_summary = {
                "website_info": {
                    "title": extracted_data.get('title', ''),
                    "url": extracted_data.get('url', ''),
                    "meta_description": extracted_data.get('meta_description', '')
                },
                "personal_info": extracted_data.get('personal_information', {}),
                "about_section": extracted_data.get('about_section', '')[:500],
                "projects_count": len(extracted_data.get('projects', [])),
                "projects_sample": extracted_data.get('projects', [])[:3],
                "skills": extracted_data.get('skills', [])[:15],
                "work_experience_count": len(extracted_data.get('work_experience', [])),
                "education_count": len(extracted_data.get('education', [])),
                "social_links": extracted_data.get('social_links', {}),
                "contact_info": extracted_data.get('contact_information', {}),
                "technical_details": extracted_data.get('technical_details', {}),
                "content_structure": extracted_data.get('content_analysis', {}),
                "seo_analysis": extracted_data.get('seo_analysis', {}),
                "design_elements": extracted_data.get('design_elements', {})
            }
            
            # Create comprehensive prompt for portfolio analysis
            prompt = f"""
            You are an expert portfolio reviewer and career coach with extensive experience in evaluating professional portfolios across various industries.

            **User Context**:
            - Name: {user_name}
            - Profession: {user_profession}
            - Career Interests: {', '.join(user_career_choices) if user_career_choices else 'Not specified'}

            **Portfolio Data Summary**:
            {json.dumps(portfolio_summary, indent=2)}

            **Analysis Task**: 
            Analyze this portfolio website comprehensively and provide detailed feedback with scoring and improvement suggestions.

            **Scoring Criteria (0-100 scale)**:
            1. **Content Quality (25%)**: Projects showcase, about section, professional presentation
            2. **Technical Implementation (20%)**: Website performance, responsive design, SEO
            3. **Design & UX (20%)**: Visual appeal, navigation, user experience
            4. **Professional Branding (15%)**: Personal branding consistency, contact info
            5. **Career Alignment (10%)**: Relevance to stated career goals
            6. **Completeness (10%)**: Portfolio completeness, missing elements

            **Return this exact JSON structure**:
            {{
                "overall_score": <number 0-100>,
                "content_quality_score": <number 0-100>,
                "technical_implementation_score": <number 0-100>,
                "design_ux_score": <number 0-100>,
                "professional_branding_score": <number 0-100>,
                "career_alignment_score": <number 0-100>,
                "completeness_score": <number 0-100>,
                "strengths": [
                    "strength 1",
                    "strength 2",
                    "strength 3"
                ],
                "weaknesses": [
                    "weakness 1",
                    "weakness 2",
                    "weakness 3"
                ],
                "key_insights": [
                    "insight 1",
                    "insight 2",
                    "insight 3"
                ],
                "grade_explanation": "Detailed explanation of the overall score and reasoning"
            }}

            Focus on practical, actionable insights based on the extracted data. Return ONLY valid JSON.
            """

            # Call Claude API
            message = client.messages_create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                temperature=0.3,
                system="You are a portfolio analysis expert. Return only valid JSON with the exact structure requested.",
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            # Extract response
            response_text = message.content[0].text
            logger.info("Received portfolio analysis response from Claude API")
            
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
                        return self._create_fallback_portfolio_analysis(extracted_data, user_profile)
                else:
                    logger.error("Could not find JSON block in response")
                    return self._create_fallback_portfolio_analysis(extracted_data, user_profile)
            
            # Create score breakdown
            score_breakdown = {
                'content_quality': analysis_data.get('content_quality_score', 70),
                'technical_implementation': analysis_data.get('technical_implementation_score', 70),
                'design_ux': analysis_data.get('design_ux_score', 70),
                'professional_branding': analysis_data.get('professional_branding_score', 70),
                'career_alignment': analysis_data.get('career_alignment_score', 70),
                'completeness': analysis_data.get('completeness_score', 70),
                'weights': {
                    'content_quality': 25,
                    'technical_implementation': 20,
                    'design_ux': 20,
                    'professional_branding': 15,
                    'career_alignment': 10,
                    'completeness': 10
                }
            }
            
            # Create detailed suggestions
            suggestions = self._create_detailed_suggestions(user_profession, extracted_data, analysis_data)
            
            # Calculate overall score
            overall_score = analysis_data.get('overall_score', 70)
            
            logger.info(f"Successfully generated portfolio analysis with score: {overall_score}")
            return analysis_data, suggestions, overall_score, score_breakdown
            
        except Exception as e:
            logger.error(f"Error in portfolio analysis with Claude: {e}")
            return self._create_fallback_portfolio_analysis(extracted_data, user_profile)
    
    def _create_detailed_suggestions(self, user_profession: str, extracted_data: Dict[str, Any], analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed improvement suggestions"""
        projects_count = len(extracted_data.get('projects', []))
        skills_count = len(extracted_data.get('skills', []))
        has_contact = bool(extracted_data.get('contact_information', {}).get('email'))
        has_about = bool(extracted_data.get('about_section'))
        seo_score = extracted_data.get('seo_analysis', {})
        social_links_count = len(extracted_data.get('social_links', {}))
        
        return {
            "immediate_improvements": [
                {
                    "category": "Content Enhancement",
                    "action": "Add more projects to showcase",
                    "description": f"Currently showing {projects_count} projects. Aim for 4-6 diverse projects",
                    "priority": "high" if projects_count < 3 else "medium",
                    "effort": "medium"
                },
                {
                    "category": "Professional Branding",
                    "action": "Complete contact information",
                    "description": "Ensure email, phone, and location are clearly visible",
                    "priority": "high" if not has_contact else "low",
                    "effort": "low"
                },
                {
                    "category": "SEO Optimization",
                    "action": "Improve SEO elements",
                    "description": "Add meta descriptions, optimize titles, and improve alt text coverage",
                    "priority": "high" if not seo_score.get('has_meta_description') else "medium",
                    "effort": "low"
                }
            ],
            "content_improvements": [
                {
                    "area": "Project Descriptions",
                    "suggestion": "Add detailed project descriptions with challenges solved",
                    "examples": ["Problem statement", "Solution approach", "Technologies used", "Results achieved"]
                },
                {
                    "area": "About Section",
                    "suggestion": "Craft a compelling professional story" if not has_about else "Enhance the about section",
                    "examples": ["Career journey", "Passion for technology", "Unique value proposition", "Professional goals"]
                },
                {
                    "area": "Case Studies",
                    "suggestion": "Convert projects into detailed case studies",
                    "examples": ["Before/after scenarios", "User research", "Design process", "Impact metrics"]
                }
            ],
            "technical_improvements": [
                {
                    "area": "Performance Optimization",
                    "suggestion": "Improve website loading speed",
                    "action_items": ["Optimize images", "Minify CSS/JS", "Enable caching", "Use CDN"]
                },
                {
                    "area": "SEO Enhancement",
                    "suggestion": "Improve search engine visibility",
                    "action_items": ["Add meta descriptions", "Optimize page titles", "Use proper heading structure", "Add alt text to images"]
                },
                {
                    "area": "Mobile Responsiveness",
                    "suggestion": "Ensure perfect mobile experience",
                    "action_items": ["Test on all devices", "Optimize touch targets", "Improve mobile navigation"]
                }
            ],
            "career_specific_advice": {
                "for_profession": user_profession,
                "industry_focus": [
                    f"Highlight {user_profession.lower()}-specific projects",
                    "Show understanding of industry trends",
                    "Include relevant certifications"
                ],
                "skill_development": [
                    "Add projects using latest technologies",
                    "Show continuous learning journey",
                    "Include open source contributions"
                ],
                "networking": [
                    "Link to professional social profiles",
                    "Add testimonials from colleagues",
                    "Include speaking engagements or articles"
                ]
            },
            "project_recommendations": [
                {
                    "project_type": f"Advanced {user_profession} Project",
                    "description": "Create a signature project that demonstrates your expertise",
                    "requirements": [
                        "Use modern technology stack",
                        "Solve a real-world problem",
                        "Document the entire process",
                        "Include live demo and code repository"
                    ],
                    "estimated_duration": "4-6 weeks",
                    "impact": "High - showcases technical depth and problem-solving"
                },
                {
                    "project_type": "Industry-Specific Application",
                    "description": f"Build an application relevant to {user_profession} field",
                    "requirements": [
                        "Research industry pain points",
                        "Create user-centered solution",
                        "Implement best practices",
                        "Gather user feedback"
                    ],
                    "estimated_duration": "6-8 weeks",
                    "impact": "High - demonstrates industry knowledge and practical skills"
                }
            ]
        }
    
    def _simplify_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify extracted data for Firestore storage"""
        simplified = {}
        
        # Keep essential extracted data
        essential_fields = [
            'url', 'title', 'meta_description', 'personal_information',
            'about_section', 'contact_information', 'social_links'
        ]
        
        for field in essential_fields:
            if field in extracted_data:
                simplified[field] = extracted_data[field]
        
        # Simplify complex arrays
        if 'projects' in extracted_data:
            projects = extracted_data['projects'][:8]
            simplified['projects'] = projects
            simplified['projects_count'] = len(extracted_data['projects'])
        
        if 'skills' in extracted_data:
            simplified['skills'] = extracted_data['skills'][:20]
            simplified['skills_count'] = len(extracted_data['skills'])
        
        if 'work_experience' in extracted_data:
            simplified['work_experience'] = extracted_data['work_experience'][:5]
            simplified['work_experience_count'] = len(extracted_data['work_experience'])
        
        if 'education' in extracted_data:
            simplified['education'] = extracted_data['education'][:3]
            simplified['education_count'] = len(extracted_data['education'])
        
        # Add summary statistics
        simplified['extraction_summary'] = {
            'total_projects': len(extracted_data.get('projects', [])),
            'total_skills': len(extracted_data.get('skills', [])),
            'total_work_experience': len(extracted_data.get('work_experience', [])),
            'total_education': len(extracted_data.get('education', [])),
            'has_about_section': bool(extracted_data.get('about_section')),
            'has_contact_info': bool(extracted_data.get('contact_information', {}).get('email')),
            'social_links_count': len(extracted_data.get('social_links', {})),
            'has_blog_posts': len(extracted_data.get('blog_posts', [])) > 0,
            'has_testimonials': len(extracted_data.get('testimonials', [])) > 0,
            'extracted_at': extracted_data.get('extracted_at')
        }
        
        # Include technical and SEO details
        if 'technical_details' in extracted_data:
            simplified['technical_details'] = extracted_data['technical_details']
        
        if 'seo_analysis' in extracted_data:
            simplified['seo_analysis'] = extracted_data['seo_analysis']
        
        if 'content_analysis' in extracted_data:
            simplified['content_analysis'] = extracted_data['content_analysis']
        
        return simplified
    
    def _simplify_analysis_results(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify analysis results for Firestore storage"""
        if not isinstance(analysis_results, dict):
            return {}
        
        simplified = {}
        
        # Extract simple fields
        simple_fields = [
            'overall_score', 'content_quality_score', 'technical_implementation_score',
            'design_ux_score', 'professional_branding_score', 'career_alignment_score',
            'completeness_score', 'grade_explanation'
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
        
        if 'key_insights' in analysis_results:
            simplified['key_insights'] = [str(i) for i in analysis_results['key_insights'][:5]]
        
        return simplified
    
    def _simplify_suggestions(self, suggestions: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify suggestions for Firestore storage"""
        if not isinstance(suggestions, dict):
            return {}
        
        simplified = {}
        
        # Handle immediate improvements
        if 'immediate_improvements' in suggestions:
            improvements = suggestions['immediate_improvements']
            if isinstance(improvements, list):
                simplified['immediate_improvements'] = []
                for improvement in improvements[:3]:
                    if isinstance(improvement, dict):
                        simple_improvement = {
                            'category': str(improvement.get('category', ''))[:100],
                            'action': str(improvement.get('action', ''))[:200],
                            'description': str(improvement.get('description', ''))[:400],
                            'priority': str(improvement.get('priority', 'medium'))[:20],
                            'effort': str(improvement.get('effort', 'medium'))[:20]
                        }
                        simplified['immediate_improvements'].append(simple_improvement)
        
        # Handle other suggestion categories
        for key in ['content_improvements', 'technical_improvements']:
            if key in suggestions and isinstance(suggestions[key], list):
                simplified[key] = []
                for item in suggestions[key][:3]:
                    if isinstance(item, dict):
                        simple_item = {}
                        for k, v in item.items():
                            if isinstance(v, list):
                                simple_item[k] = [str(x)[:150] for x in v[:4]]
                            else:
                                simple_item[k] = str(v)[:400]
                        simplified[key].append(simple_item)
        
        # Handle career specific advice
        if 'career_specific_advice' in suggestions:
            career_advice = suggestions['career_specific_advice']
            if isinstance(career_advice, dict):
                simplified['career_specific_advice'] = {}
                for key, value in career_advice.items():
                    if isinstance(value, list):
                        simplified['career_specific_advice'][key] = [str(x)[:200] for x in value[:3]]
                    else:
                        simplified['career_specific_advice'][key] = str(value)[:400]
        
        # Handle project recommendations
        if 'project_recommendations' in suggestions:
            projects = suggestions['project_recommendations']
            if isinstance(projects, list):
                simplified['project_recommendations'] = []
                for project in projects[:2]:
                    if isinstance(project, dict):
                        simple_project = {
                            'project_type': str(project.get('project_type', ''))[:100],
                            'description': str(project.get('description', ''))[:400],
                            'estimated_duration': str(project.get('estimated_duration', ''))[:50],
                            'impact': str(project.get('impact', ''))[:300]
                        }
                        
                        # Handle requirements array
                        if 'requirements' in project and isinstance(project['requirements'], list):
                            simple_project['requirements'] = [str(x)[:150] for x in project['requirements'][:5]]
                        
                        simplified['project_recommendations'].append(simple_project)
        
        return simplified
    
    def _simplify_score_breakdown(self, score_breakdown: Dict[str, Any]) -> Dict[str, Any]:
        """Simplify score breakdown for Firestore storage"""
        if not isinstance(score_breakdown, dict):
            return {}
        
        simplified = {}
        
        # Extract numeric scores
        score_fields = [
            'content_quality', 'technical_implementation', 'design_ux',
            'professional_branding', 'career_alignment', 'completeness'
        ]
        
        for field in score_fields:
            if field in score_breakdown:
                value = score_breakdown[field]
                if isinstance(value, (int, float)):
                    simplified[field] = value
                else:
                    simplified[field] = 70  # Default score
        
        # Handle weights
        if 'weights' in score_breakdown and isinstance(score_breakdown['weights'], dict):
            simplified['weights'] = score_breakdown['weights']
        
        return simplified
    
    def _create_fallback_portfolio_analysis(self, extracted_data: Dict[str, Any], user_profile: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any], int, Dict[str, Any]]:
        """Create fallback portfolio analysis when AI analysis fails"""
        logger.info("Creating fallback portfolio analysis")
        
        user_profession = user_profile.get('profession', 'Professional')
        
        # Calculate basic scores based on extracted data
        projects_count = len(extracted_data.get('projects', []))
        skills_count = len(extracted_data.get('skills', []))
        has_about = bool(extracted_data.get('about_section'))
        has_contact = bool(extracted_data.get('contact_information', {}).get('email'))
        social_links_count = len(extracted_data.get('social_links', {}))
        work_exp_count = len(extracted_data.get('work_experience', []))
        education_count = len(extracted_data.get('education', []))
        
        # Technical metrics
        technical_details = extracted_data.get('technical_details', {})
        has_https = technical_details.get('has_https', False)
        has_responsive = technical_details.get('has_responsive_design', False)
        load_time = technical_details.get('load_time', 5.0)
        
        # SEO metrics
        seo_analysis = extracted_data.get('seo_analysis', {})
        has_meta_desc = seo_analysis.get('has_meta_description', False)
        has_title = seo_analysis.get('has_title', False)
        alt_coverage = seo_analysis.get('alt_text_coverage', 0.0)
        
        # Content structure
        content_analysis = extracted_data.get('content_analysis', {})
        has_nav = content_analysis.get('has_navigation', False)
        word_count = content_analysis.get('word_count', 0)
        
        # Scoring logic
        content_score = min(30 + (projects_count * 8) + (has_about * 15) + (work_exp_count * 5), 100)
        
        technical_score = 40
        technical_score += 15 if has_https else 0
        technical_score += 15 if has_responsive else 0
        technical_score += 15 if load_time < 3.0 else (10 if load_time < 5.0 else 5)
        technical_score += 10 if has_meta_desc else 0
        technical_score += 5 if alt_coverage > 0.7 else 0
        
        design_score = 50
        design_score += 10 if has_nav else 0
        design_score += 15 if word_count > 500 else (10 if word_count > 200 else 0)
        design_score += min(social_links_count * 5, 25)
        
        branding_score = 40
        branding_score += 25 if has_contact else 0
        branding_score += 15 if has_about else 0
        branding_score += min(social_links_count * 4, 20)
        
        alignment_score = 65 + min(projects_count * 5, 25) + (10 if skills_count > 5 else 0)
        
        completeness_score = 20
        completeness_score += 15 if projects_count > 0 else 0
        completeness_score += 15 if has_about else 0
        completeness_score += 15 if has_contact else 0
        completeness_score += 10 if work_exp_count > 0 else 0
        completeness_score += 10 if education_count > 0 else 0
        completeness_score += 10 if skills_count > 0 else 0
        completeness_score += 5 if social_links_count > 0 else 0
        
        # Calculate weighted overall score
        overall_score = int(
            (content_score * 0.25) + 
            (technical_score * 0.20) + 
            (design_score * 0.20) + 
            (branding_score * 0.15) + 
            (alignment_score * 0.10) + 
            (completeness_score * 0.10)
        )
        
        fallback_analysis = {
            "overall_score": overall_score,
            "content_quality_score": content_score,
            "technical_implementation_score": technical_score,
            "design_ux_score": design_score,
            "professional_branding_score": branding_score,
            "career_alignment_score": alignment_score,
            "completeness_score": completeness_score,
            "strengths": [
                f"Portfolio showcases {projects_count} projects" if projects_count > 0 else "Portfolio structure established",
                f"Lists {skills_count} technical skills" if skills_count > 0 else "Skills section present",
                "Professional web presence established",
                f"Includes {work_exp_count} work experiences" if work_exp_count > 0 else "Ready for content expansion"
            ][:3],
            "weaknesses": [
                "Analysis requires comprehensive review" if overall_score > 60 else "Significant improvements needed",
                "Portfolio could benefit from detailed optimization",
                "Consider enhancing content depth and technical implementation"
            ],
            "key_insights": [
                "Portfolio shows professional foundation" if overall_score > 50 else "Portfolio needs fundamental improvements",
                "Room for content enhancement and technical optimization",
                f"Strong alignment with {user_profession} career goals" if alignment_score > 70 else "Career alignment needs improvement"
            ],
            "grade_explanation": f"Score of {overall_score} based on content quality ({content_score}), technical implementation ({technical_score}), design ({design_score}), professional branding ({branding_score}), career alignment ({alignment_score}), and completeness ({completeness_score}). Detailed AI analysis recommended for comprehensive feedback."
        }
        
        # Create detailed suggestions
        fallback_suggestions = self._create_detailed_suggestions(user_profession, extracted_data, fallback_analysis)
        
        # Create score breakdown
        score_breakdown = {
            'content_quality': content_score,
            'technical_implementation': technical_score,
            'design_ux': design_score,
            'professional_branding': branding_score,
            'career_alignment': alignment_score,
            'completeness': completeness_score,
            'weights': {
                'content_quality': 25,
                'technical_implementation': 20,
                'design_ux': 20,
                'professional_branding': 15,
                'career_alignment': 10,
                'completeness': 10
            }
        }
        
        return fallback_analysis, fallback_suggestions, overall_score, score_breakdown
    
# Global service instance
portfolio_service = PortfolioAnalyzerService() 