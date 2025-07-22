"""
Assistant Client - OpenAI Assistant integration for interview questions
"""

import openai
import json
import logging
from config.settings import Config

logger = logging.getLogger(__name__)

class AssistantClient:
    """Client for interacting with OpenAI Assistant API"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        self.assistant_id = Config.OPENAI_ASSISTANT_ID
    
    def create_thread(self) -> str:
        """Create a new conversation thread"""
        try:
            thread = self.client.beta.threads.create()
            logger.info(f"Thread created: {thread.id}")
            return thread.id
        except Exception as e:
            logger.error(f"Failed to create thread: {e}")
            raise Exception(f"Failed to create interview thread: {e}")
    
    def run_assistant(self, thread_id: str, role: str, resume: str, 
                     last_question: str = "", last_answer: str = "", 
                     answer_feedback: str = "", answer_history: str = "") -> dict:
        """Run the assistant to generate interview questions"""
        try:
            # Build message content
            message_content = self._build_message_content(
                role, resume, last_question, last_answer, answer_feedback, answer_history
            )
            
            logger.info(f"Adding message to thread {thread_id}")
            
            # Add user message to thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message_content
            )
            
            # Run the assistant
            logger.info(f"Running assistant for thread {thread_id}")
            run = self.client.beta.threads.runs.create_and_poll(
                assistant_id=self.assistant_id,
                thread_id=thread_id,
                temperature=0.7
            )
            
            logger.info(f"Assistant run status: {run.status}")
            
            if run.status != "completed":
                raise RuntimeError(f"Assistant run did not complete: {run.status}")
            
            # Get the response
            return self._extract_assistant_response(thread_id, role)
            
        except Exception as e:
            logger.error(f"Assistant run failed: {e}")
            return self._generate_fallback_response(role, last_question)
    
    def _build_message_content(self, role: str, resume: str, last_question: str, 
                              last_answer: str, answer_feedback: str, answer_history: str) -> str:
        """Build the message content for the assistant"""
        if not last_question and not last_answer:
            # First message: introduce the role and context
            if resume:
                return f"I'm ready for my video interview as a {role}. This is a video interview where I can speak but cannot write code. Here is my resume: {resume}"
            else:
                return f"I'm ready for my video interview as a {role}. This is a video interview where I can speak but cannot write code."
        else:
            # Subsequent messages: provide context about the role and previous interaction
            role_context = f"Role: {role}. This is a video interview - I can speak but cannot write or show code. "
            
            # Analyze answer quality for better follow-up
            answer_analysis = self._analyze_answer_quality(last_answer)
            
            if answer_analysis["is_vague"]:
                return f"{role_context}Previous question: {last_question}. My answer was vague: {last_answer or 'N/A'}. Please ask a follow-up question to help me elaborate on my {role} experience. Ask for conceptual explanations, not code examples."
            elif answer_analysis["is_out_of_context"]:
                return f"{role_context}Previous question: {last_question}. My answer was off-topic: {last_answer or 'N/A'}. Please redirect me back to {role} related questions. Ask for conceptual explanations, not code examples."
            else:
                return f"{role_context}Previous question: {last_question}. My answer: {last_answer or 'N/A'}. Please ask follow-up questions that focus on concepts, experiences, and explanations rather than code writing."
    
    def _analyze_answer_quality(self, answer: str) -> dict:
        """Analyze the quality of the candidate's answer"""
        answer_lower = answer.strip().lower()
        
        # Vague answer detection
        vague_keywords = ["i don't know", "not sure", "maybe", "idk", "no idea", "unsure", "don't know"]
        is_vague = any(kw in answer_lower for kw in vague_keywords)
        
        # Out of context detection
        out_of_context_keywords = [
            "hello", "hi", "hey", "lol", "love you", "useless", "joke", "funny", "smart", "dumb",
            "goodbye", "bye", "thanks", "thank you", "ok", "okay", "yes", "no", "how are you"
        ]
        is_out_of_context = any(kw in answer_lower for kw in out_of_context_keywords)
        
        return {
            "is_vague": is_vague,
            "is_out_of_context": is_out_of_context,
            "length": len(answer.strip()),
            "word_count": len(answer.split())
        }
    
    def _extract_assistant_response(self, thread_id: str, role: str) -> dict:
        """Extract and process the assistant's response"""
        try:
            # Fetch messages from the thread
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            
            # Log message history for debugging
            logger.info(f"Thread message history for {thread_id}:")
            for m in messages.data:
                logger.info(f"  {m.role}: {m.content[0].text.value.strip()}")
            
            # Find the latest assistant message
            for message in messages.data:
                if message.role == "assistant" and message.content:
                    content = message.content[0].text.value.strip()
                    logger.info(f"Raw assistant response: {content}")
                    
                    try:
                        response_json = json.loads(content)
                        
                        # Post-process the response for video interviews
                        return self._post_process_response(response_json, role)
                        
                    except json.JSONDecodeError as e:
                        logger.warning(f"Failed to parse assistant response as JSON: {e}")
                        # Try to extract question from plain text
                        return self._extract_question_from_text(content, role)
            
            raise ValueError("No assistant response found in thread")
            
        except Exception as e:
            logger.error(f"Failed to extract assistant response: {e}")
            return self._generate_fallback_response(role)
    
    def _post_process_response(self, response_json: dict, role: str) -> dict:
        """Post-process the assistant response for video interviews"""
        if "next_question" in response_json:
            question = response_json["next_question"]
            
            # Check if the question asks for code writing
            code_keywords = [
                "write", "show me the code", "write code", "code example", 
                "show code", "demonstrate with code", "write a function",
                "show me how to", "code snippet", "write a program"
            ]
            
            question_lower = question.lower()
            if any(keyword in question_lower for keyword in code_keywords):
                # Replace with a more appropriate question
                response_json["next_question"] = self._convert_to_conceptual_question(question)
                response_json["note_to_user"] = "I'm asking for your conceptual understanding and approach, not code writing."
        
        return response_json
    
    def _convert_to_conceptual_question(self, question: str) -> str:
        """Convert code-writing questions to conceptual questions"""
        replacements = {
            "write": "explain how you would approach",
            "show me the code": "explain the concept behind",
            "write code": "describe your approach to",
            "code example": "conceptual understanding of",
            "show code": "explain the principles of",
            "demonstrate with code": "describe how you would solve",
            "write a function": "explain the logic behind",
            "show me how to": "describe your methodology for",
            "code snippet": "conceptual approach to",
            "write a program": "explain your strategy for"
        }
        
        question_lower = question.lower()
        for old_phrase, new_phrase in replacements.items():
            if old_phrase in question_lower:
                return question.lower().replace(old_phrase, new_phrase).capitalize()
        
        return f"Can you explain the concept behind {question.replace('write', '').replace('code', '').strip()} and how you would approach it conceptually?"
    
    def _extract_question_from_text(self, content: str, role: str) -> dict:
        """Extract question from plain text response"""
        # Try to find question-like sentences
        sentences = content.split('.')
        for sentence in sentences:
            if '?' in sentence and len(sentence.strip()) > 10:
                return {
                    "next_question": sentence.strip(),
                    "note_to_user": f"Continuing our {role} interview discussion."
                }
        
        # Fallback
        return self._generate_fallback_response(role)
    
    def _generate_fallback_response(self, role: str, last_question: str = "") -> dict:
        """Generate a fallback response when assistant fails"""
        fallback_questions = [
            f"Can you describe a specific challenge you've solved recently in your {role} experience and explain your approach?",
            f"Tell me about a project you're particularly proud of in your {role} career.",
            f"How do you stay updated with the latest trends and technologies in your {role} field?",
            f"Describe a time when you had to learn something new quickly for your {role} work.",
            f"What motivates you most about working as a {role}?"
        ]
        
        import random
        question = random.choice(fallback_questions)
        
        return {
            "next_question": question,
            "note_to_user": "Let's continue exploring your experience and approach to challenges."
        }
    
    def get_thread_messages(self, thread_id: str) -> list:
        """Get all messages from a thread"""
        try:
            messages = self.client.beta.threads.messages.list(thread_id=thread_id)
            return [
                {
                    "role": msg.role,
                    "content": msg.content[0].text.value if msg.content else "",
                    "created_at": msg.created_at
                }
                for msg in messages.data
            ]
        except Exception as e:
            logger.error(f"Failed to get thread messages: {e}")
            return []
    
    def delete_thread(self, thread_id: str) -> bool:
        """Delete a conversation thread"""
        try:
            self.client.beta.threads.delete(thread_id)
            logger.info(f"Thread deleted: {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {e}")
            return False