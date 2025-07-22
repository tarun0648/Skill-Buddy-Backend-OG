"""
JD Interview Routes - Job Description Based Interview System
"""

from datetime import datetime
from flask import Blueprint, request, jsonify

# Import services
from services.jd_interview_service import JDInterviewService
from services.firebase_service import FirebaseService
from utils.auth_utils import require_auth
from utils.validation_utils import validate_required_fields

jd_interview_bp = Blueprint('jd_interview', __name__)

@jd_interview_bp.route('/analyze', methods=['POST'])
@require_auth
def analyze_job_description():
    """Analyze uploaded job description and extract key details"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['job_description'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        job_description = data['job_description']
        
        # Extract details from job description
        jd_service = JDInterviewService()
        extracted_data = jd_service.extract_jd_details(job_description)
        
        return jsonify({
            "success": True,
            "extracted_data": extracted_data,
            "message": "Job description analyzed successfully"
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@jd_interview_bp.route('/first-question', methods=['POST'])
@require_auth
def jd_first_question():
    """Get the first question for JD-based interview"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['extracted_data'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        extracted_data = data['extracted_data']
        
        # Get first question based on JD
        jd_service = JDInterviewService()
        result = jd_service.get_jd_first_question(extracted_data)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@jd_interview_bp.route('/next-question', methods=['POST'])
@require_auth
def jd_next_question():
    """Get the next question for JD-based interview"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['extracted_data'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        extracted_data = data['extracted_data']
        last_question = data.get('last_question', '')
        last_answer = data.get('last_answer', '')
        answer_history = data.get('answer_history', '')
        round_number = data.get('interview_round', 1)
        used_questions = data.get('used_questions', [])
        session_id = data.get('session_id', '')
        user_id = request.user_id  # From auth middleware
        
        # Get next question based on JD
        jd_service = JDInterviewService()
        result = jd_service.get_jd_next_question(
            extracted_data, 
            last_question, 
            last_answer, 
            answer_history, 
            round_number, 
            used_questions
        )
        
        # Save to Firebase if not interview complete
        if not result.get('interview_complete', False):
            try:
                firebase_service = FirebaseService()
                firebase_service.save_interview_history({
                    "session_id": session_id,
                    "thread_id": session_id,  # Use session_id as thread_id for JD interviews
                    "user_id": user_id,
                    "role": extracted_data.get("role", "JD-based"),
                    "resume": "",
                    "interview_round": round_number,
                    "question": last_question,
                    "answer": last_answer,
                    "feedback": "",
                    "note_to_user": result.get("note_to_user", ""),
                    "next_question": result.get("next_question", ""),
                    "created_at": datetime.utcnow().isoformat(),
                    "assessment_type": "jd_based",
                    "jd_data": extracted_data
                })
            except Exception as firebase_error:
                # Log the error but don't fail the request
                print(f"Firebase save failed: {firebase_error}")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@jd_interview_bp.route('/history', methods=['GET'])
@require_auth
def get_jd_interview_history():
    """Get JD interview history for a session"""
    try:
        session_id = request.args.get("session_id")
        user_id = request.user_id
        
        if not session_id:
            return jsonify({"success": False, "error": "Missing session_id parameter"}), 400
        
        firebase_service = FirebaseService()
        history = firebase_service.get_interview_history(session_id, user_id, assessment_type="jd_based")
        
        return jsonify({"success": True, "history": history})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@jd_interview_bp.route('/matching-questions', methods=['POST'])
@require_auth
def get_matching_questions():
    """Get predefined questions that match the JD criteria"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['extracted_data'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        extracted_data = data['extracted_data']
        num_questions = data.get('num_questions', 5)
        
        jd_service = JDInterviewService()
        matching_questions = jd_service.find_matching_jd_questions(extracted_data, num_questions)
        
        return jsonify({
            "success": True,
            "matching_questions": matching_questions,
            "count": len(matching_questions),
            "jd_data": extracted_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@jd_interview_bp.route('/generate-custom', methods=['POST'])
@require_auth
def generate_custom_question():
    """Generate a custom question for specific JD requirements"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['extracted_data'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        extracted_data = data['extracted_data']
        last_answer = data.get('last_answer', '')
        answer_history = data.get('answer_history', '')
        question_type = data.get('question_type', 'general')  # general, technical, behavioral
        
        jd_service = JDInterviewService()
        question = jd_service.generate_jd_specific_question(
            extracted_data, last_answer, answer_history, question_type
        )
        
        # Process for video interview
        processed = jd_service.process_jd_question_for_video_interview(question)
        
        return jsonify({
            "success": True,
            "question": processed["question"],
            "note": processed.get("note"),
            "question_type": question_type,
            "jd_data": extracted_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@jd_interview_bp.route('/skills-assessment', methods=['POST'])
@require_auth
def assess_skills():
    """Assess candidate skills based on JD requirements"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['extracted_data', 'interview_history'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        extracted_data = data['extracted_data']
        interview_history = data['interview_history']
        
        jd_service = JDInterviewService()
        assessment = jd_service.assess_candidate_skills(extracted_data, interview_history)
        
        return jsonify({
            "success": True,
            "skills_assessment": assessment,
            "jd_data": extracted_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@jd_interview_bp.route('/compatibility-score', methods=['POST'])
@require_auth
def calculate_compatibility():
    """Calculate compatibility score between candidate and JD"""
    try:
        data = request.json
        validation_result = validate_required_fields(data, ['extracted_data', 'candidate_responses'])
        if not validation_result['valid']:
            return jsonify({"success": False, "error": validation_result['message']}), 400
        
        extracted_data = data['extracted_data']
        candidate_responses = data['candidate_responses']
        
        jd_service = JDInterviewService()
        compatibility_score = jd_service.calculate_compatibility_score(extracted_data, candidate_responses)
        
        return jsonify({
            "success": True,
            "compatibility_score": compatibility_score,
            "jd_data": extracted_data
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500