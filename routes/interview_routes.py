"""
Interview Routes - Traditional Role-based Interview System
"""

import os
import json
import random
import re
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

# Import services
from services.interview_service import InterviewService
from services.assistant_client import AssistantClient
from services.firebase_service import FirebaseService
from utils.auth_utils import require_auth
from utils.validation_utils import validate_required_fields
from utils.file_utils import allowed_file, save_upload_file

interview_bp = Blueprint('interview', __name__)

# Interview ending constants
MAX_QUESTIONS = 8  # Maximum questions for a full interview
MIN_QUESTIONS = 5  # Minimum questions before considering early ending

# Upload configuration
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@interview_bp.route('/start-session', methods=['POST'])
@require_auth
def start_session():
    """Start a new interview session"""
    try:
        assistant_client = AssistantClient()
        thread_id = assistant_client.create_thread()
        
        return jsonify({
            "success": True, 
            "thread_id": thread_id,
            "message": "Interview session started successfully"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@interview_bp.route('/first-question', methods=['POST'])
@require_auth
def first_question():
    """Get the first question for role-based interview"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['role', 'level', 'topic'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        role = data['role']
        level = data['level']
        topic = data['topic']
        
        interview_service = InterviewService()
        
        # Get predefined questions for the criteria
        available_questions = interview_service.get_questions_by_criteria(role, level, topic)
        
        if available_questions:
            # Use predefined question
            question = available_questions[0]
            note_to_user = random.choice([
                "Welcome! When you're ready, we'll get started. Just be yourself—this is your space to share your story.",
                "Hey there! Take a moment to settle in. This is just a conversation, so no pressure.",
                "Ready to begin? There's no rush—take your time and answer in your own way.",
                "Let's start whenever you feel comfortable. Remember, it's okay to pause and think things through.",
                "You've got this! Treat this like a friendly chat and show us your unique perspective.",
                "Hi! We're excited to hear from you. Just relax and let your experiences shine through.",
                "This is your moment to share your journey. Take a breath, and let's get started when you're ready."
            ])
            
            return jsonify({
                "success": True,
                "question": question['question'],
                "note_to_user": note_to_user,
                "question_source": "predefined",
                "question_difficulty": question.get("difficulty", "medium"),
                "question_category": question.get("category", "General")
            })
        else:
            # Fallback to AI-generated question
            assistant_client = AssistantClient()
            thread_id = assistant_client.create_thread()
            
            # Generate first AI question
            assistant_response = assistant_client.run_assistant(
                thread_id, role, '',  # Pass empty string for resume
                "", "",  # No previous question/answer for first question
                "", ""   # No feedback/history for first question
            )
            
            if "next_question" in assistant_response:
                # Post-process AI response to make it video-interview appropriate
                processed_question = interview_service.process_question_for_video_interview(
                    assistant_response["next_question"], role
                )
                assistant_response["next_question"] = processed_question["question"]
                if processed_question["note"]:
                    assistant_response["note_to_user"] = processed_question["note"]
                
                # Add a welcome note for AI-generated questions
                if not assistant_response.get("note_to_user"):
                    assistant_response["note_to_user"] = f"Welcome! I'll be asking you questions about {role} experience. Let's get started!"
                
                # Save the first AI-generated question to JSON
                interview_service.save_ai_question_to_json(
                    assistant_response["next_question"], 
                    role, 
                    level, 
                    topic, 
                    category="AI Generated"
                )
                
                return jsonify({
                    "success": True,
                    "question": assistant_response["next_question"],
                    "note_to_user": assistant_response["note_to_user"],
                    "question_source": "ai_generated",
                    "thread_id": thread_id
                })
            else:
                return jsonify({"success": False, "error": "Failed to generate AI question."}), 500
                
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@interview_bp.route('/next-question', methods=['POST'])
@require_auth
def next_question():
    """Get the next question in the interview"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['thread_id', 'role'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        thread_id = data['thread_id']
        role = data['role']
        level = data.get('level', 'junior')
        topic = data.get('topic', '')
        last_question = data.get('last_question', '')
        last_answer = data.get('last_answer', '')
        answer_feedback = data.get('answer_feedback', '')
        answer_history = data.get('answer_history', '')
        session_id = data.get('session_id', thread_id)
        user_id = request.user_id  # From auth middleware
        round_number = data.get('interview_round', 1)
        
        interview_service = InterviewService()
        assistant_client = AssistantClient()
        firebase_service = FirebaseService()
        
        # Check if interview should end
        should_end, end_reason = interview_service.should_end_interview(
            round_number, last_answer, MIN_QUESTIONS, MAX_QUESTIONS
        )
        
        if should_end:
            return jsonify({
                "success": True,
                "interview_complete": True,
                "end_reason": end_reason,
                "total_questions": round_number,
                "role": role,
                "level": level,
                "topic": topic,
                "note_to_user": "Interview completed successfully!"
            })
        
        # Determine question strategy
        use_predefined = interview_service.should_use_predefined_question(
            round_number, last_answer
        )
        
        if use_predefined:
            # Try to get predefined question
            available_questions = interview_service.get_questions_by_criteria(role, level, topic)
            question_index = round_number // 2
            
            if question_index < len(available_questions):
                selected_question = available_questions[question_index]
                
                # Save to Firebase
                firebase_service.save_interview_history({
                    "session_id": session_id,
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "role": role,
                    "level": level,
                    "topic": topic,
                    "interview_round": round_number,
                    "question": last_question,
                    "answer": last_answer,
                    "feedback": answer_feedback,
                    "note_to_user": f"Here's a {role} question about {topic}.",
                    "next_question": selected_question["question"],
                    "created_at": datetime.utcnow().isoformat(),
                    "assessment_type": "role_based"
                })
                
                return jsonify({
                    "success": True,
                    "next_question": selected_question["question"],
                    "note_to_user": f"Here's a {role} question about {topic}.",
                    "question_source": "predefined",
                    "question_difficulty": selected_question.get("difficulty", "medium")
                })
        
        # Use AI-generated question
        enhanced_context = interview_service.build_ai_context(
            role, level, topic, round_number, last_answer, answer_history
        )
        
        assistant_response = assistant_client.run_assistant(
            thread_id, role, enhanced_context,
            last_question, last_answer,
            answer_feedback, answer_history
        )
        
        # Enhanced backend post-processing for note_to_user
        note_to_user = interview_service.generate_note_to_user(
            last_answer, role, assistant_response.get("note_to_user")
        )
        
        if note_to_user:
            assistant_response["note_to_user"] = note_to_user
        
        # Add question source indicator
        assistant_response["question_source"] = "ai_generated"
        
        # Post-process AI response for video interview
        if "next_question" in assistant_response:
            processed_question = interview_service.process_question_for_video_interview(
                assistant_response["next_question"], role
            )
            assistant_response["next_question"] = processed_question["question"]
            if processed_question["note"]:
                assistant_response["note_to_user"] = processed_question["note"]
            
            # Save NEW role-based questions to JSON
            should_save = interview_service.should_save_ai_question(
                round_number, last_answer, answer_history
            )
            if should_save:
                interview_service.save_ai_question_to_json(
                    assistant_response["next_question"], 
                    role, level, topic, 
                    category="AI Generated"
                )
        
        # Save to Firebase
        firebase_service.save_interview_history({
            "session_id": session_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "role": role,
            "level": level,
            "topic": topic,
            "interview_round": round_number,
            "question": last_question,
            "answer": last_answer,
            "feedback": answer_feedback,
            "note_to_user": assistant_response.get("note_to_user", ""),
            "next_question": assistant_response.get("next_question", ""),
            "created_at": datetime.utcnow().isoformat(),
            "assessment_type": "role_based"
        })
        
        return jsonify({"success": True, **assistant_response})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@interview_bp.route('/history', methods=['GET'])
@require_auth
def get_interview_history():
    """Get interview history for a session"""
    try:
        session_id = request.args.get("session_id")
        user_id = request.user_id
        
        if not session_id:
            return jsonify({"success": False, "error": "Missing session_id parameter"}), 400
        
        firebase_service = FirebaseService()
        history = firebase_service.get_interview_history(session_id, user_id)
        
        return jsonify({
            "success": True, 
            "history": history,
            "session_id": session_id,
            "user_id": user_id,
            "count": len(history)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@interview_bp.route('/upload-video', methods=['POST'])
@require_auth
def upload_video():
    """Upload video response for interview question"""
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        question_id = request.form.get('question_id', 'unknown')
        session_id = request.form.get('session_id', 'unknown')
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if file and allowed_file(file.filename, ['mp4', 'webm', 'avi', 'mov']):
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = secure_filename(
                f"{session_id}_q{question_id}_{timestamp}.{file.filename.split('.')[-1]}"
            )
            filepath = save_upload_file(file, filename, UPLOAD_FOLDER)
            
            return jsonify({'success': True, 'filename': filename, 'filepath': filepath})
        else:
            return jsonify({'error': 'Invalid file type. Only video files are allowed.'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@interview_bp.route('/save-summary', methods=['POST'])
@require_auth
def save_interview_summary():
    """Save interview summary"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['session_id'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        session_id = data['session_id']
        user_id = request.user_id
        
        # Add user_id to summary data
        data['user_id'] = user_id
        data['created_at'] = datetime.utcnow().isoformat()
        
        # Save to Firebase
        firebase_service = FirebaseService()
        firebase_service.save_interview_summary(data)
        
        # Also save as file for backup
        summary_filename = f"{session_id}_summary.json"
        summary_filepath = os.path.join(UPLOAD_FOLDER, summary_filename)
        with open(summary_filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        return jsonify({
            'success': True, 
            'status': 'success', 
            'summary_file': summary_filename,
            'message': 'Interview summary saved successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@interview_bp.route('/questions/topics', methods=['GET'])
def get_available_topics():
    """Get available topics for interviews"""
    try:
        role = request.args.get('role')
        level = request.args.get('level', 'junior')
        
        interview_service = InterviewService()
        topics = interview_service.get_available_topics(role, level)
        
        return jsonify({
            "success": True,
            "topics": topics,
            "role": role,
            "level": level
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@interview_bp.route('/questions/count', methods=['GET'])
def get_questions_count():
    """Get count of available questions"""
    try:
        role = request.args.get('role')
        level = request.args.get('level', 'junior')
        topic = request.args.get('topic')
        
        interview_service = InterviewService()
        count = interview_service.get_questions_count(role, level, topic)
        
        return jsonify({
            "success": True,
            "count": count,
            "role": role,
            "level": level,
            "topic": topic
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@interview_bp.route('/user/all-data', methods=['GET'])
@require_auth
def get_all_user_interview_data():
    """Get all interview data for the authenticated user"""
    try:
        user_id = request.user_id
        limit = request.args.get('limit', 100, type=int)
        
        # Validate limit
        if limit > 500:
            limit = 500  # Cap at 500 for performance
        elif limit < 1:
            limit = 50   # Default minimum
        
        firebase_service = FirebaseService()
        user_data = firebase_service.get_all_user_interview_data(user_id, limit)
        
        return jsonify({
            "success": True,
            "data": user_data
        })
        
    except Exception as e:
        logging.error(f"Failed to get user interview data: {e}")
        return jsonify({
            "success": False, 
            "error": str(e)
        }), 500