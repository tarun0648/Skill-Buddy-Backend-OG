# routes/portfolio_analysis_routes.py
from flask import Blueprint, request, jsonify
from config.firebase_config import firebase_config
from services.portfolio_analyzer import portfolio_service
from models.portfolio_analysis_model import PortfolioAnalysisModel
import logging
from datetime import datetime

# Create blueprint
portfolio_analysis_bp = Blueprint('portfolio_analysis', __name__)

# Initialize components
db = firebase_config.get_db()
if db:
    portfolio_analysis_model = PortfolioAnalysisModel(db)
else:
    portfolio_analysis_model = None

logger = logging.getLogger(__name__)

def auth_required(f):
    """Local auth decorator for portfolio analysis routes"""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required in X-User-ID header'}), 401
        
        # Verify user exists in database
        if db:
            try:
                doc_ref = db.collection('users').document(user_id)
                doc = doc_ref.get()
                if not doc.exists:
                    return jsonify({'error': 'Invalid user ID'}), 401
            except Exception as e:
                return jsonify({'error': 'User verification failed'}), 401
        
        request.user_id = user_id
        return f(*args, **kwargs)
    
    return decorated

@portfolio_analysis_bp.route('/analyze', methods=['POST'])
@auth_required
def analyze_portfolio():
    """Analyze portfolio website using enhanced parallel processing"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'portfolio_url' not in data:
            return jsonify({'error': 'Portfolio URL is required'}), 400
        
        portfolio_url = data['portfolio_url'].strip()
        
        # Validate URL format
        if not portfolio_url or not portfolio_url.startswith(('http://', 'https://')):
            return jsonify({'error': 'Invalid portfolio URL format. Must be a valid HTTP/HTTPS URL.'}), 400
        
        # Get user profile for context
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        # Start portfolio analysis using enhanced service
        task_id, success = portfolio_service.start_portfolio_analysis(
            user_id=user_id,
            portfolio_url=portfolio_url,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start portfolio analysis'}), 500
        
        logger.info(f"Portfolio analysis started for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'Portfolio analysis started',
            'user_id': user_id,
            'task_id': task_id,
            'status': 'pending',
            'progress': 0
        }), 200
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {str(e)}")
        return jsonify({'error': 'Failed to start portfolio analysis', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/status/<user_id>', methods=['GET'])
@auth_required
def get_portfolio_analysis_status(user_id):
    """Get portfolio analysis status for user with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get portfolio processing status using enhanced service
        status_data = portfolio_service.get_processing_status(user_id)
        
        if not status_data:
            return jsonify({'error': 'No portfolio analysis found for user'}), 404
        
        return jsonify({
            'user_id': user_id,
            'task_id': status_data.get('task_id'),
            'analysis_id': status_data.get('analysis_id'),
            'status': status_data.get('status'),
            'progress': status_data.get('progress', 0),
            'portfolio_url': status_data.get('portfolio_url', ''),
            'created_at': status_data.get('created_at'),
            'started_at': status_data.get('started_at'),
            'completed_at': status_data.get('completed_at'),
            'error_message': status_data.get('error_message'),
            'is_active': status_data.get('is_active', False)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting portfolio analysis status: {e}")
        return jsonify({'error': 'Failed to get portfolio analysis status', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/results/<user_id>', methods=['GET'])
@auth_required
def get_portfolio_analysis_results(user_id):
    """Get portfolio analysis results for user with enhanced tracking"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get portfolio results using enhanced service
        results = portfolio_service.get_analysis_results(user_id)
        
        if not results:
            return jsonify({'error': 'No portfolio analysis results found for user'}), 404
        
        # If processing is not completed, return status info
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': results.get('message', 'Portfolio analysis in progress')
            }), 200
        
        # Return completed results
        return jsonify({
            'user_id': user_id,
            'task_id': results.get('task_id'),
            'analysis_id': results.get('analysis_id'),
            'status': 'completed',
            'portfolio_url': results.get('portfolio_url', ''),
            'score': results.get('score'),
            'score_breakdown': results.get('score_breakdown'),
            'analysis_results': results.get('analysis_results'),
            'extracted_data': results.get('extracted_data'),
            'suggestions': results.get('suggestions'),
            'processed_at': results.get('processed_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting portfolio analysis results: {e}")
        return jsonify({'error': 'Failed to get portfolio analysis results', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/suggestions/<user_id>', methods=['GET'])
@auth_required
def get_portfolio_improvement_suggestions(user_id):
    """Get improvement suggestions for user's latest portfolio analysis"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get portfolio results using enhanced service
        results = portfolio_service.get_analysis_results(user_id)
        
        if not results:
            return jsonify({'error': 'No portfolio analysis results found for user'}), 404
        
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': 'Portfolio analysis not completed yet'
            }), 200
        
        suggestions = results.get('suggestions', {})
        
        return jsonify({
            'user_id': user_id,
            'analysis_id': results.get('analysis_id'),
            'suggestions': suggestions,
            'portfolio_url': results.get('portfolio_url', ''),
            'score': results.get('score')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting portfolio improvement suggestions: {e}")
        return jsonify({'error': 'Failed to get portfolio improvement suggestions', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/reanalyze/<user_id>', methods=['POST'])
@auth_required
def reanalyze_portfolio(user_id):
    """Reanalyze portfolio for user"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get user's current portfolio URL
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        portfolio_url = user_profile.get('portfolio_link', '')
        
        if not portfolio_url:
            return jsonify({'error': 'No portfolio URL found for user'}), 400
        
        # Start portfolio reanalysis
        task_id, success = portfolio_service.start_portfolio_analysis(
            user_id=user_id,
            portfolio_url=portfolio_url,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start portfolio reanalysis'}), 500
        
        logger.info(f"Portfolio reanalysis started for user {user_id}, task_id: {task_id}")
        
        return jsonify({
            'message': 'Portfolio reanalysis started',
            'user_id': user_id,
            'task_id': task_id,
            'status': 'pending',
            'progress': 0
        }), 200
        
    except Exception as e:
        logger.error(f"Portfolio reanalysis error: {str(e)}")
        return jsonify({'error': 'Failed to start portfolio reanalysis', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/delete/<user_id>', methods=['DELETE'])
@auth_required
def delete_portfolio_analysis(user_id):
    """Delete user's latest portfolio analysis"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        if not portfolio_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
        
        # Get user's latest portfolio analysis
        user_analyses = portfolio_analysis_model.get_user_analyses(user_id)
        
        if not user_analyses:
            return jsonify({'error': 'No portfolio analyses found for user'}), 404
        
        # Get the latest analysis
        latest_analysis = user_analyses[0]  # Already sorted by created_at desc
        analysis_id = latest_analysis['id']
        
        # Delete from database
        success = portfolio_analysis_model.delete_analysis(analysis_id)
        
        if not success:
            return jsonify({'error': 'Failed to delete portfolio analysis from database'}), 500
        
        logger.info(f"Portfolio analysis deleted for user {user_id}, analysis_id: {analysis_id}")
        
        return jsonify({
            'message': 'Portfolio analysis deleted successfully',
            'user_id': user_id,
            'analysis_id': analysis_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting portfolio analysis: {e}")
        return jsonify({'error': 'Failed to delete portfolio analysis', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/extracted-data/<user_id>', methods=['GET'])
@auth_required
def get_extracted_portfolio_data(user_id):
    """Get extracted data from user's latest portfolio analysis"""
    try:
        # Verify the user_id in URL matches the authenticated user
        if user_id != request.user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        # Get portfolio results using enhanced service
        results = portfolio_service.get_analysis_results(user_id)
        
        if not results:
            return jsonify({'error': 'No portfolio analysis results found for user'}), 404
        
        if results.get('status') != 'completed':
            return jsonify({
                'user_id': user_id,
                'status': results.get('status'),
                'progress': results.get('progress', 0),
                'message': 'Portfolio analysis not completed yet'
            }), 200
        
        extracted_data = results.get('extracted_data', {})
        
        return jsonify({
            'user_id': user_id,
            'analysis_id': results.get('analysis_id'),
            'extracted_data': extracted_data,
            'portfolio_url': results.get('portfolio_url', '')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting extracted portfolio data: {e}")
        return jsonify({'error': 'Failed to get extracted portfolio data', 'details': str(e)}), 500