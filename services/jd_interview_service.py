"""
JD Interview Service - Business logic for job description based interviews
"""

import json
import os
import re
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import openai
from config.settings import Config

class JDInterviewService:
    """Service for managing job description based interviews"""
    
    def __init__(self):
        self.jd_questions_json_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'jd-predefined.json'
        )
        self._load_jd_questions()
        self.openai_client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        
        # Interview configuration
        self.MAX_QUESTIONS = 8
        self.MIN_QUESTIONS = 5
        self.VAGUE_THRESHOLD = 3
    
    def _load_jd_questions(self):
        """Load JD questions from JSON file"""
        try:
            with open(self.jd_questions_json_path, 'r', encoding='utf-8') as f:
                self.jd_questions_db = json.load(f)
        except FileNotFoundError:
            print(f"JD Questions file not found: {self.jd_questions_json_path}")
            self.jd_questions_db = []
        except json.JSONDecodeError as e:
            print(f"Error parsing JD questions JSON: {e}")
            self.jd_questions_db = []
    
    def extract_jd_details(self, job_description: str) -> Dict[str, Any]:
        """Extract key details from job description using OpenAI"""
        try:
            prompt = f"""
            Analyze this job description and extract the following information in JSON format:
            
            {job_description}
            
            Please provide:
            {{
                "role": "extracted role title",
                "level": "junior/mid/senior based on requirements",
                "skills": ["skill1", "skill2", "skill3"],
                "technologies": ["tech1", "tech2", "tech3"],
                "responsibilities": ["responsibility1", "responsibility2"],
                "requirements": ["requirement1", "requirement2"],
                "company_type": "startup/enterprise/agency/etc",
                "industry": "tech/finance/healthcare/etc"
            }}
            
            Focus on the most important and specific details. If information is not clear, make reasonable inferences.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            extracted_data = json.loads(response.choices[0].message.content)
            return extracted_data
            
        except Exception as e:
            print(f"Error extracting JD details: {e}")
            # Fallback to basic extraction
            return {
                "role": "Software Developer",
                "level": "mid",
                "skills": ["programming", "problem solving"],
                "technologies": ["general"],
                "responsibilities": ["development"],
                "requirements": ["experience"],
                "company_type": "tech",
                "industry": "technology"
            }
    
    def find_matching_jd_questions(self, extracted_data: Dict, num_questions: int = 5) -> List[Dict]:
        """Find predefined questions that match the extracted JD details"""
        # Extract key information
        role = extracted_data.get("role", "").lower()
        level = extracted_data.get("level", "mid").lower()
        skills = [skill.lower() for skill in extracted_data.get("skills", [])]
        technologies = [tech.lower() for tech in extracted_data.get("technologies", [])]
        
        # Score each question based on relevance
        scored_questions = []
        
        for question in self.jd_questions_db:
            score = self._calculate_question_score(question, role, level, skills, technologies, extracted_data)
            
            if score > 0:
                scored_questions.append((score, question))
        
        # Sort by score and take top questions with variety
        scored_questions.sort(key=lambda x: x[0], reverse=True)
        return self._select_diverse_questions(scored_questions, num_questions)
    
    def _calculate_question_score(self, question: Dict, role: str, level: str, 
                                skills: List[str], technologies: List[str], 
                                extracted_data: Dict) -> int:
        """Calculate relevance score for a question"""
        score = 0
        question_text = question.get("question", "").lower()
        question_role = question.get("role", "").lower()
        question_difficulty = question.get("difficulty", "").lower()
        question_topic = question.get("topic", "").lower()
        
        # Role matching
        if role in question_role or question_role in role:
            score += 10
        
        # Level matching
        if level in question_difficulty or question_difficulty in level:
            score += 5
        
        # Skills matching
        for skill in skills:
            if skill in question_text or skill in question_topic:
                score += 3
        
        # Technology matching
        for tech in technologies:
            if tech in question_text or tech in question_topic:
                score += 3
        
        # JD-specific fields matching
        jd_skills = question.get("jd_skills", [])
        jd_technologies = question.get("jd_technologies", [])
        jd_industry = question.get("jd_industry", "").lower()
        jd_company_type = question.get("jd_company_type", "").lower()
        
        # Match against JD skills and technologies
        for skill in skills:
            if skill.lower() in [s.lower() for s in jd_skills]:
                score += 4
        
        for tech in technologies:
            if tech.lower() in [t.lower() for t in jd_technologies]:
                score += 4
        
        # Industry and company type matching
        if extracted_data.get("industry", "").lower() == jd_industry:
            score += 2
        if extracted_data.get("company_type", "").lower() == jd_company_type:
            score += 2
        
        return score
    
    def _select_diverse_questions(self, scored_questions: List[Tuple], num_questions: int) -> List[Dict]:
        """Select diverse questions from scored list"""
        selected_questions = []
        seen_topics = set()
        
        for score, question in scored_questions:
            if len(selected_questions) >= num_questions:
                break
            
            topic = question.get("topic", "")
            if topic not in seen_topics or len(selected_questions) < 3:
                selected_questions.append(question)
                seen_topics.add(topic)
        
        # Add general questions if not enough
        if len(selected_questions) < num_questions:
            general_questions = [q for q in self.jd_questions_db if q.get("category") == "Behavioral"]
            for question in general_questions:
                if len(selected_questions) >= num_questions:
                    break
                if question not in selected_questions:
                    selected_questions.append(question)
        
        return selected_questions[:num_questions]
    
    def generate_jd_specific_question(self, extracted_data: Dict, last_answer: str = "", 
                                    answer_history: str = "", question_type: str = "general") -> str:
        """Generate AI question specific to the job description"""
        try:
            # Create context from extracted data
            context = self._build_jd_context(extracted_data)
            
            # Create prompt based on question type and history
            prompt = self._build_question_prompt(context, last_answer, answer_history, question_type)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            question = response.choices[0].message.content.strip()
            
            # Clean up the question
            if question.startswith('"') and question.endswith('"'):
                question = question[1:-1]
            
            return question
            
        except Exception as e:
            print(f"Error generating JD-specific question: {e}")
            return "Tell me about your experience with the technologies mentioned in this role."
    
    def _build_jd_context(self, extracted_data: Dict) -> str:
        """Build context string from extracted JD data"""
        return f"""
        Job Role: {extracted_data.get('role', 'Software Developer')}
        Level: {extracted_data.get('level', 'mid')}
        Required Skills: {', '.join(extracted_data.get('skills', []))}
        Technologies: {', '.join(extracted_data.get('technologies', []))}
        Responsibilities: {', '.join(extracted_data.get('responsibilities', []))}
        Requirements: {', '.join(extracted_data.get('requirements', []))}
        Company Type: {extracted_data.get('company_type', 'tech')}
        Industry: {extracted_data.get('industry', 'technology')}
        """
    
    def _build_question_prompt(self, context: str, last_answer: str, answer_history: str, 
                             question_type: str) -> str:
        """Build prompt for question generation"""
        base_requirements = """
        Generate a question that:
        1. Is specific to this job description
        2. Is appropriate for a video interview (no code writing requests)
        3. Helps assess the candidate's fit for this specific role
        4. Is conversational and engaging
        """
        
        if last_answer and answer_history:
            return f"""
            You are conducting a video interview for this position:
            {context}
            
            Previous answer: {last_answer}
            Interview history: {answer_history}
            
            {base_requirements}
            5. Builds on their previous response
            6. Is a natural follow-up question
            
            Return only the question, no additional text.
            """
        else:
            return f"""
            You are conducting a video interview for this position:
            {context}
            
            {base_requirements}
            5. Focuses on their background and motivation
            6. Is an engaging opening question
            
            Return only the question, no additional text.
            """
    
    def process_jd_question_for_video_interview(self, question: str) -> Dict[str, str]:
        """Convert code-writing questions into conceptual questions for video interviews"""
        question_lower = question.lower()
        
        # Define patterns that indicate code-writing requests
        code_patterns = [
            ("write", "explain how you would approach"),
            ("show me the code", "explain the concept behind"),
            ("write code", "describe your approach to"),
            ("code example", "conceptual understanding of"),
            ("show code", "explain the principles of"),
            ("demonstrate with code", "describe how you would solve"),
            ("write a function", "explain the logic behind"),
            ("show me how to", "describe your methodology for"),
            ("code snippet", "conceptual approach to"),
            ("write a program", "explain your strategy for"),
            ("implement", "describe your approach to"),
            ("create a", "explain how you would design"),
            ("build a", "describe your methodology for"),
            ("develop a", "explain your approach to"),
            ("code this", "explain the concept of"),
            ("program this", "describe how you would approach"),
            ("algorithm", "explain the logic and approach"),
            ("function", "explain the concept and methodology"),
            ("class", "explain the design principles"),
            ("method", "explain the approach and reasoning")
        ]
        
        # Check if the question contains code-writing patterns
        for pattern, replacement in code_patterns:
            if pattern in question_lower:
                new_question = question.replace(pattern, replacement, flags=re.IGNORECASE)
                new_question = new_question.replace("  ", " ").strip()
                if not new_question.endswith("?"):
                    new_question += "?"
                
                return {
                    "question": new_question,
                    "note": "I'm asking for your conceptual understanding and approach, not code writing."
                }
        
        return {
            "question": question,
            "note": None
        }
    
    def get_jd_first_question(self, extracted_data: Dict) -> Dict[str, Any]:
        """Get the first question for JD-based interview"""
        # Get matching predefined questions
        matching_questions = self.find_matching_jd_questions(extracted_data, num_questions=1)
        
        if matching_questions:
            # Use the best matching predefined question
            selected_question = matching_questions[0]
            question_text = selected_question["question"]
            
            # Process for video interview
            processed = self.process_jd_question_for_video_interview(question_text)
            
            notes = [
                "Welcome! I've analyzed your job description and prepared some questions. Let's get started!",
                "Hi there! I've reviewed the role requirements and I'm excited to learn more about your experience.",
                "Welcome to your interview! I've tailored these questions specifically to this position.",
                "Hello! I've studied the job description and I'm ready to explore how your background fits this role.",
                "Welcome! Let's dive into how your experience aligns with what we're looking for in this position."
            ]
            note_to_user = random.choice(notes)
            
            return {
                "success": True,
                "question": processed["question"],
                "note_to_user": note_to_user,
                "question_source": "predefined",
                "jd_data": extracted_data,
                "question_difficulty": selected_question.get("difficulty", "medium"),
                "question_category": selected_question.get("category", "General")
            }
        else:
            # Fallback to AI-generated question
            ai_question = self.generate_jd_specific_question(extracted_data)
            processed = self.process_jd_question_for_video_interview(ai_question)
            
            # Save the first AI-generated JD question
            self.save_jd_ai_question_to_json(processed["question"], extracted_data, "AI Generated")
            
            return {
                "success": True,
                "question": processed["question"],
                "note_to_user": "Welcome! I've analyzed your job description and I'm ready to learn more about your experience.",
                "question_source": "ai_generated",
                "jd_data": extracted_data
            }
    
    def get_jd_next_question(self, extracted_data: Dict, last_question: str, last_answer: str,
                           answer_history: str, round_number: int, used_questions: List = None) -> Dict[str, Any]:
        """Get the next question for JD-based interview"""
        if used_questions is None:
            used_questions = []
        
        # Check if interview should end
        should_end, end_reason = self._should_end_jd_interview(round_number, last_answer, extracted_data)
        
        if should_end:
            return {
                "success": True,
                "interview_complete": True,
                "end_reason": end_reason,
                "total_questions": round_number,
                "jd_data": extracted_data,
                "note_to_user": "Interview completed successfully!"
            }
        
        # Determine question strategy
        use_predefined = self._should_use_predefined_jd_question(round_number, last_answer)
        
        if use_predefined:
            # Try to get predefined question
            available_questions = self.find_matching_jd_questions(extracted_data, num_questions=10)
            available_questions = [q for q in available_questions if q["question"] not in used_questions]
            
            if available_questions:
                question_index = ((round_number // 2) - 1) % len(available_questions)
                selected_question = available_questions[question_index]
                
                # Process for video interview
                processed = self.process_jd_question_for_video_interview(selected_question["question"])
                
                return {
                    "success": True,
                    "next_question": processed["question"],
                    "note_to_user": f"Here's a question about {selected_question.get('topic', 'this role')}.",
                    "question_source": "predefined",
                    "question_difficulty": selected_question.get("difficulty", "medium"),
                    "question_category": selected_question.get("category", "General"),
                    "jd_data": extracted_data
                }
        
        # Use AI-generated question
        try:
            ai_question = self.generate_jd_specific_question(extracted_data, last_answer, answer_history)
            processed = self.process_jd_question_for_video_interview(ai_question)
            
            # Determine if we should save this question
            should_save = self._should_save_jd_question(last_answer, answer_history)
            if should_save:
                self.save_jd_ai_question_to_json(processed["question"], extracted_data, "AI Generated")
            
            # Generate appropriate note
            note = self._generate_jd_note(last_answer)
            
            return {
                "success": True,
                "next_question": processed["question"],
                "note_to_user": note,
                "question_source": "ai_generated",
                "jd_data": extracted_data
            }
        except Exception as e:
            print(f"Error generating AI question: {e}")
            # Fallback to a general question
            fallback_question = "Tell me more about your experience with the technologies mentioned in this role."
            processed = self.process_jd_question_for_video_interview(fallback_question)
            return {
                "success": True,
                "next_question": processed["question"],
                "note_to_user": "Let me ask you about your technical experience.",
                "question_source": "ai_generated",
                "jd_data": extracted_data
            }
    
    def _should_end_jd_interview(self, round_number: int, last_answer: str, extracted_data: Dict) -> Tuple[bool, str]:
        """Determine if JD interview should end"""
        is_vague_answer = self._is_vague_jd_answer(last_answer)
        
        # 1. Maximum questions reached
        if round_number >= self.MAX_QUESTIONS:
            role = extracted_data.get('role', 'position')
            return True, f"Interview completed! We've covered {round_number} questions to assess your fit for this {role}."
        
        # 2. Early ending due to consistent poor responses
        elif round_number >= self.MIN_QUESTIONS and is_vague_answer:
            if len(last_answer.strip()) < 20:
                return True, "Thank you for your time! I'd recommend practicing with more detailed responses to better showcase your experience."
        
        # 3. Natural conclusion
        elif round_number >= 6 and not is_vague_answer and len(last_answer.strip()) > 50:
            role = extracted_data.get('role', 'this role')
            return True, f"Excellent! We've had a comprehensive discussion about your experience. Thank you for sharing your insights about {role}."
        
        return False, ""
    
    def _is_vague_jd_answer(self, answer: str) -> bool:
        """Check if answer is vague for JD interview"""
        answer_lower = answer.strip().lower()
        
        # Check for empty or very short responses
        if len(answer_lower) <= 10:
            return True
        
        # Check for vague keywords
        vague_answers = [
            "i don't know", "not sure", "maybe", "idk", "no idea", "unsure", "don't know",
            "i'm not sure", "i guess", "possibly"
        ]
        
        # Check for out of context keywords
        out_of_context_keywords = [
            "hello", "hi", "hey", "lol", "goodbye", "bye", "thanks", "thank you", "ok", "okay"
        ]
        
        is_vague = any(kw in answer_lower for kw in vague_answers)
        is_out_of_context = any(kw in answer_lower for kw in out_of_context_keywords)
        
        # Improve detection - only flag if primarily vague/out-of-context
        if is_vague or is_out_of_context:
            words = answer_lower.split()
            if len(words) > 0:
                vague_count = sum(1 for word in words if any(kw in word for kw in vague_answers + out_of_context_keywords))
                return vague_count / len(words) > 0.5 or len(words) <= 3
        
        return False
    
    def _should_use_predefined_jd_question(self, round_number: int, last_answer: str) -> bool:
        """Determine if we should use predefined question for JD interview"""
        # Use predefined questions for odd rounds (3, 5, 7, 9...)
        if round_number % 2 == 1 and round_number > 1:
            # Override if previous answer was vague
            if self._is_vague_jd_answer(last_answer):
                return False
            return True
        return False
    
    def _should_save_jd_question(self, last_answer: str, answer_history: str) -> bool:
        """Determine if JD AI question should be saved"""
        is_follow_up = bool(last_answer and answer_history)
        
        if not is_follow_up:
            return True  # New JD-based question
        elif not self._is_vague_jd_answer(last_answer):
            return True  # Good answer, might be new question
        
        return False
    
    def _generate_jd_note(self, last_answer: str) -> str:
        """Generate appropriate note for JD interview"""
        if self._is_vague_jd_answer(last_answer):
            answer_lower = last_answer.strip().lower()
            
            # Check for different types of vague answers
            out_of_context_keywords = ["hello", "hi", "hey", "lol", "goodbye", "bye"]
            if any(kw in answer_lower for kw in out_of_context_keywords):
                return "Let's stay focused on your professional experience. I'd love to hear about your background and skills."
            elif len(answer_lower) <= 10:
                return "It looks like you didn't say much. Feel free to share any experience or thoughts related to the question!"
            else:
                return "I understand you're not sure. Let me ask you something different that might be easier to answer."
        else:
            return "Let me ask you a follow-up question based on your response."
    
    def save_jd_ai_question_to_json(self, question_text: str, extracted_data: Dict, category: str = "AI Generated") -> bool:
        """Save AI-generated JD questions to the JSON file for future use"""
        try:
            # Create new question object
            new_question = {
                "question": question_text,
                "role": extracted_data.get("role", "Software Developer"),
                "difficulty": extracted_data.get("level", "mid").capitalize(),
                "company": "",
                "year": "2025",
                "category": category,
                "topic": ", ".join(extracted_data.get("skills", [])[:3]),  # Use first 3 skills as topic
                "source": "AI Generated",
                "jd_skills": extracted_data.get("skills", []),
                "jd_technologies": extracted_data.get("technologies", []),
                "jd_industry": extracted_data.get("industry", "technology"),
                "jd_company_type": extracted_data.get("company_type", "tech")
            }
            
            # Add to questions array
            self.jd_questions_db.append(new_question)
            
            # Save back to file
            with open(self.jd_questions_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.jd_questions_db, f, indent=2, ensure_ascii=False)
            
            print(f"[DEBUG] Saved new JD AI question to JSON: {question_text[:50]}...")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save JD AI question to JSON: {e}")
            return False
    
    def assess_candidate_skills(self, extracted_data: Dict, interview_history: List[Dict]) -> Dict[str, Any]:
        """Assess candidate skills based on JD requirements and interview responses"""
        required_skills = extracted_data.get("skills", [])
        required_technologies = extracted_data.get("technologies", [])
        
        # Analyze responses for skill mentions
        skill_mentions = {}
        tech_mentions = {}
        
        for entry in interview_history:
            answer = entry.get("answer", "").lower()
            
            # Check for skill mentions
            for skill in required_skills:
                if skill.lower() in answer:
                    skill_mentions[skill] = skill_mentions.get(skill, 0) + 1
            
            # Check for technology mentions
            for tech in required_technologies:
                if tech.lower() in answer:
                    tech_mentions[tech] = tech_mentions.get(tech, 0) + 1
        
        # Calculate coverage scores
        skills_coverage = len(skill_mentions) / len(required_skills) if required_skills else 0
        tech_coverage = len(tech_mentions) / len(required_technologies) if required_technologies else 0
        
        # Overall assessment
        overall_score = (skills_coverage + tech_coverage) / 2 * 100
        
        return {
            "overall_score": round(overall_score, 2),
            "skills_coverage": round(skills_coverage * 100, 2),
            "technology_coverage": round(tech_coverage * 100, 2),
            "skill_mentions": skill_mentions,
            "technology_mentions": tech_mentions,
            "required_skills": required_skills,
            "required_technologies": required_technologies,
            "assessment_date": datetime.utcnow().isoformat()
        }
    
    def calculate_compatibility_score(self, extracted_data: Dict, candidate_responses: List[str]) -> Dict[str, Any]:
        """Calculate compatibility score between candidate and JD requirements"""
        try:
            # Combine all candidate responses
            combined_responses = " ".join(candidate_responses).lower()
            
            # Score different aspects
            role_fit_score = self._calculate_role_fit(extracted_data, combined_responses)
            skills_match_score = self._calculate_skills_match(extracted_data, combined_responses)
            experience_score = self._calculate_experience_level_match(extracted_data, combined_responses)
            cultural_fit_score = self._calculate_cultural_fit(extracted_data, combined_responses)
            
            # Weighted overall score
            overall_score = (
                role_fit_score * 0.3 +
                skills_match_score * 0.4 +
                experience_score * 0.2 +
                cultural_fit_score * 0.1
            )
            
            return {
                "overall_compatibility": round(overall_score, 2),
                "role_fit": round(role_fit_score, 2),
                "skills_match": round(skills_match_score, 2),
                "experience_level": round(experience_score, 2),
                "cultural_fit": round(cultural_fit_score, 2),
                "recommendation": self._get_compatibility_recommendation(overall_score),
                "calculated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"Error calculating compatibility score: {e}")
            return {
                "overall_compatibility": 0,
                "error": "Failed to calculate compatibility score"
            }
    
    def _calculate_role_fit(self, extracted_data: Dict, responses: str) -> float:
        """Calculate how well candidate fits the role"""
        role_keywords = extracted_data.get("responsibilities", []) + extracted_data.get("requirements", [])
        if not role_keywords:
            return 50.0  # Neutral score if no keywords
        
        matches = sum(1 for keyword in role_keywords if keyword.lower() in responses)
        return min(100.0, (matches / len(role_keywords)) * 100)
    
    def _calculate_skills_match(self, extracted_data: Dict, responses: str) -> float:
        """Calculate skills match score"""
        required_skills = extracted_data.get("skills", []) + extracted_data.get("technologies", [])
        if not required_skills:
            return 50.0
        
        matches = sum(1 for skill in required_skills if skill.lower() in responses)
        return min(100.0, (matches / len(required_skills)) * 100)
    
    def _calculate_experience_level_match(self, extracted_data: Dict, responses: str) -> float:
        """Calculate experience level match"""
        required_level = extracted_data.get("level", "mid").lower()
        
        # Look for experience indicators in responses
        experience_indicators = {
            "junior": ["beginner", "learning", "new to", "junior", "entry level"],
            "mid": ["experience", "worked with", "familiar", "intermediate", "mid level"],
            "senior": ["expert", "lead", "senior", "advanced", "extensive", "mentor", "architect"]
        }
        
        level_matches = sum(1 for indicator in experience_indicators.get(required_level, []) if indicator in responses)
        return min(100.0, level_matches * 25)  # Each match gives 25 points, max 100
    
    def _calculate_cultural_fit(self, extracted_data: Dict, responses: str) -> float:
        """Calculate cultural fit based on company type and communication style"""
        company_type = extracted_data.get("company_type", "").lower()
        
        # Basic cultural fit indicators
        positive_indicators = ["team", "collaborate", "communication", "learn", "grow", "challenge"]
        matches = sum(1 for indicator in positive_indicators if indicator in responses)
        
        return min(100.0, matches * 15)  # Each match gives 15 points
    
    def _get_compatibility_recommendation(self, score: float) -> str:
        """Get recommendation based on compatibility score"""
        if score >= 80:
            return "Excellent match - Highly recommended for next round"
        elif score >= 65:
            return "Good match - Recommended for consideration"
        elif score >= 50:
            return "Moderate match - May require additional assessment"
        else:
            return "Low match - Consider other candidates"