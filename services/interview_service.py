"""
Interview Service - Business logic for traditional role-based interviews
"""

import json
import os
import re
import random
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

class InterviewService:
    """Service for managing traditional role-based interviews"""
    
    def __init__(self):
        self.questions_json_path = os.path.join(
            os.path.dirname(__file__), '..', 'data', 'interview_questions.json'
        )
        self._load_questions()
    
    def _load_questions(self):
        """Load questions from JSON file"""
        try:
            with open(self.questions_json_path, 'r', encoding='utf-8') as f:
                self.questions_db = json.load(f)
        except FileNotFoundError:
            print(f"Questions file not found: {self.questions_json_path}")
            self.questions_db = []
        except json.JSONDecodeError as e:
            print(f"Error parsing questions JSON: {e}")
            self.questions_db = []
    
    def get_questions_by_criteria(self, role: str, level: str, topic: str) -> List[Dict]:
        """Get questions filtered by role, level, and topic"""
        filtered_questions = []
        
        for question in self.questions_db:
            # Map difficulty levels
            question_level = question.get('difficulty', '').lower()
            if question_level in ['mid', 'mid/senior']:
                mapped_level = 'mid'
            elif question_level in ['senior', 'executive']:
                mapped_level = 'senior'
            else:
                mapped_level = 'junior'
            
            # Check if question matches criteria
            if (question.get('role') == role and 
                mapped_level == level and 
                question.get('topic') == topic):
                # Add id if not present
                if 'id' not in question:
                    question['id'] = len(filtered_questions) + 1
                filtered_questions.append(question)
        
        # Fallback strategies if no exact match
        if not filtered_questions and topic:
            filtered_questions = self._get_fallback_questions(role, level)
        
        return filtered_questions
    
    def _get_fallback_questions(self, role: str, level: str) -> List[Dict]:
        """Get fallback questions when exact match not found"""
        fallback_questions = []
        
        # Try role and level match
        for question in self.questions_db:
            question_level = self._map_difficulty_level(question.get('difficulty', ''))
            if question.get('role') == role and question_level == level:
                if 'id' not in question:
                    question['id'] = len(fallback_questions) + 1
                fallback_questions.append(question)
        
        # Try just role match if still empty
        if not fallback_questions:
            for question in self.questions_db:
                if question.get('role') == role:
                    if 'id' not in question:
                        question['id'] = len(fallback_questions) + 1
                    fallback_questions.append(question)
        
        return fallback_questions
    
    def _map_difficulty_level(self, difficulty: str) -> str:
        """Map difficulty levels to standard format"""
        difficulty_lower = difficulty.lower()
        if difficulty_lower in ['mid', 'mid/senior']:
            return 'mid'
        elif difficulty_lower in ['senior', 'executive']:
            return 'senior'
        else:
            return 'junior'
    
    def save_ai_question_to_json(self, question_text: str, role: str, level: str, 
                                topic: str, category: str = "AI Generated") -> bool:
        """Save AI-generated questions to the JSON file for future use"""
        try:
            # Create new question object
            new_question = {
                "question": question_text,
                "role": role,
                "difficulty": level.capitalize(),
                "company": "",
                "year": "2025",
                "category": category,
                "topic": topic,
                "source": "AI Generated"
            }
            
            # Add to questions array
            self.questions_db.append(new_question)
            
            # Save back to file
            with open(self.questions_json_path, 'w', encoding='utf-8') as f:
                json.dump(self.questions_db, f, indent=2, ensure_ascii=False)
            
            print(f"[DEBUG] Saved new AI question to JSON: {question_text[:50]}...")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to save AI question to JSON: {e}")
            return False
    
    def process_question_for_video_interview(self, question: str, role: str) -> Dict[str, str]:
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
                # Replace the code-writing request with a conceptual question
                new_question = re.sub(pattern, replacement, question, flags=re.IGNORECASE)
                # Clean up the question
                new_question = new_question.replace("  ", " ").strip()
                if not new_question.endswith("?"):
                    new_question += "?"
                
                return {
                    "question": new_question,
                    "note": "I'm asking for your conceptual understanding and approach, not code writing."
                }
        
        # If no code patterns found, return the original question
        return {
            "question": question,
            "note": None
        }
    
    def should_end_interview(self, round_number: int, last_answer: str, 
                           min_questions: int, max_questions: int) -> Tuple[bool, str]:
        """Determine if interview should end"""
        # Analyze answer quality
        is_vague_answer = self._is_vague_answer(last_answer)
        
        # 1. Maximum questions reached
        if round_number >= max_questions:
            return True, f"Interview completed! We've covered {round_number} questions to assess your experience."
        
        # 2. Early ending due to consistent poor responses (after minimum questions)
        elif round_number >= min_questions and is_vague_answer:
            if len(last_answer.strip()) < 20:  # Very short answers consistently
                return True, "Thank you for your time! I'd recommend practicing with more detailed responses to better showcase your experience."
        
        # 3. Natural conclusion - if we've asked enough questions and got good responses
        elif round_number >= 6 and not is_vague_answer and len(last_answer.strip()) > 50:
            return True, "Excellent! We've had a comprehensive discussion about your experience. Thank you for sharing your insights."
        
        return False, ""
    
    def _is_vague_answer(self, answer: str) -> bool:
        """Check if answer is vague or out of context"""
        answer_lower = answer.strip().lower()
        answer_words = answer_lower.split()
        
        # Vague detection
        vague_phrases = ["i don't know", "not sure", "maybe", "idk", "no idea", "unsure", "don't know"]
        
        if len(answer_words) < 10:
            return any(phrase in answer_lower for phrase in vague_phrases)
        else:
            vague_word_count = sum(1 for word in answer_words if any(phrase in word for phrase in vague_phrases))
            return vague_word_count > len(answer_words) * 0.3
    
    def should_use_predefined_question(self, round_number: int, last_answer: str) -> bool:
        """Determine if we should use predefined question"""
        # Use predefined questions for odd rounds (3, 5, 7, 9...)
        if round_number % 2 == 1 and round_number > 1:
            # Override if previous answer was vague or out of context
            if self._is_vague_answer(last_answer) or self._is_out_of_context(last_answer):
                return False
            return True
        return False
    
    def _is_out_of_context(self, answer: str) -> bool:
        """Check if answer is out of context"""
        answer_lower = answer.strip().lower()
        answer_words = answer_lower.split()
        
        out_of_context_phrases = [
            "hello", "hi", "hey", "lol", "love you", "useless", "joke", "funny", "smart", "dumb",
            "goodbye", "bye", "thanks", "thank you", "ok", "okay", "yes", "no"
        ]
        
        if len(answer_words) < 5:
            return any(phrase in answer_lower for phrase in out_of_context_phrases)
        else:
            out_of_context_count = sum(1 for word in answer_words if any(phrase in word for phrase in out_of_context_phrases))
            return out_of_context_count > 2
    
    def build_ai_context(self, role: str, level: str, topic: str, round_number: int, 
                        last_answer: str, answer_history: str) -> str:
        """Build enhanced context for AI question generation"""
        available_questions = self.get_questions_by_criteria(role, level, topic)
        question_index = round_number // 2
        
        if len(available_questions) == 0:
            # No predefined questions at all - generate role-based questions
            if round_number == 1:
                return f"Generate a professional {role} interview question to start the conversation. Focus on {topic} area. Level: {level}. Make it engaging and open-ended."
            elif round_number % 2 == 1:
                return f"Generate a NEW professional {role} interview question. Focus on {topic} area. Level: {level}. Ask about DIFFERENT aspects, scenarios, or challenges."
            else:
                return f"Generate a follow-up question based on their previous answer. Role: {role}, Topic: {topic}."
        else:
            # We have some predefined questions
            if round_number > 3 and question_index >= len(available_questions):
                return f"Generate a NEW professional {role} interview question. Focus on {topic} area. Level: {level}."
            else:
                return f"Generate a follow-up question based on their previous answer. Role: {role}, Topic: {topic}."
    
    def generate_note_to_user(self, last_answer: str, role: str, existing_note: str) -> Optional[str]:
        """Generate appropriate note to user based on answer quality"""
        if existing_note:
            return None
        
        answer_lower = last_answer.lower()
        
        if self._is_vague_answer(last_answer):
            return "Take your time — feel free to share whatever experience relates most closely."
        elif self._is_out_of_context(last_answer):
            return f"Let's stay focused on your {role} experience. Appreciate your message — now, back to your professional experience."
        elif any(kw in answer_lower for kw in ["talk about", "instead", "other topic", "different topic", "side project"]):
            return f"This session is focused on your {role} experience. For other topics, please start a new interview session."
        
        return None
    
    def should_save_ai_question(self, round_number: int, last_answer: str, answer_history: str) -> bool:
        """Determine if AI-generated question should be saved"""
        is_follow_up = bool(last_answer and answer_history)
        
        if not is_follow_up:
            return True  # New role-based question
        elif not self._is_vague_answer(last_answer) and not self._is_out_of_context(last_answer):
            return True  # Good answer, might be new question
        
        return False
    
    def get_available_topics(self, role: str = None, level: str = None) -> List[str]:
        """Get list of available topics for given role and level"""
        topics = set()
        
        for question in self.questions_db:
            if role and question.get('role') != role:
                continue
            if level:
                question_level = self._map_difficulty_level(question.get('difficulty', ''))
                if question_level != level:
                    continue
            
            topic = question.get('topic')
            if topic:
                topics.add(topic)
        
        return sorted(list(topics))
    
    def get_questions_count(self, role: str = None, level: str = None, topic: str = None) -> int:
        """Get count of available questions by criteria"""
        if role and level and topic:
            return len(self.get_questions_by_criteria(role, level, topic))
        
        count = 0
        for question in self.questions_db:
            if role and question.get('role') != role:
                continue
            if level:
                question_level = self._map_difficulty_level(question.get('difficulty', ''))
                if question_level != level:
                    continue
            if topic and question.get('topic') != topic:
                continue
            
            count += 1
        
        return count