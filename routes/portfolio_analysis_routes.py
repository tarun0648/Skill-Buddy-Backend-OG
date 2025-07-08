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

@portfolio_analysis_bp.route('/analyze/portfolio', methods=['POST'])
@auth_required
def analyze_portfolio_website():
    """Analyze portfolio website using Claude AI and web scraping"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        data = request.get_json()
        
        if not data or 'portfolio_url' not in data:
            return jsonify({'error': 'Portfolio URL is required'}), 400
        
        portfolio_url = data['portfolio_url'].strip()
        
        # Validate URL format
        if not portfolio_url or not (portfolio_url.startswith('http://') or portfolio_url.startswith('https://')):
            return jsonify({'error': 'Invalid portfolio URL format. Must start with http:// or https://'}), 400
        
        # Get user profile for context
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        # Start portfolio analysis
        analysis_id, success = portfolio_service.start_portfolio_analysis(
            user_id=user_id,
            portfolio_url=portfolio_url,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start portfolio analysis'}), 500
        
        logger.info(f"Portfolio analysis started for user {user_id}, analysis_id: {analysis_id}")
        
        return jsonify({
            'message': 'Portfolio analysis started successfully',
            'analysis_id': analysis_id,
            'status': 'pending',
            'type': 'portfolio'
        }), 201
        
    except Exception as e:
        logger.error(f"Portfolio analysis error: {e}")
        return jsonify({'error': 'Portfolio analysis failed', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/status/<analysis_id>', methods=['GET'])
@auth_required
def get_portfolio_analysis_status(analysis_id):
    """Get portfolio analysis status"""
    try:
        user_id = request.user_id
        analysis_data = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        return jsonify({
            'analysis_id': analysis_id,
            'status': analysis_data.get('status', 'unknown'),
            'type': analysis_data.get('analysis_type'),
            'created_at': analysis_data.get('created_at'),
            'processed_at': analysis_data.get('processed_at'),
            'error_message': analysis_data.get('error_message'),
            'portfolio_url': analysis_data.get('portfolio_url')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting portfolio analysis status: {e}")
        return jsonify({'error': 'Failed to get analysis status', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/results/<analysis_id>', methods=['GET'])
@auth_required
def get_portfolio_analysis_results(analysis_id):
    """Get complete portfolio analysis results"""
    try:
        user_id = request.user_id
        analysis_data = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        if analysis_data.get('status') != 'completed':
            return jsonify({
                'status': analysis_data.get('status', 'unknown'),
                'message': 'Portfolio analysis not completed yet'
            }), 200
        
        return jsonify({
            'analysis_id': analysis_id,
            'status': 'completed',
            'type': analysis_data.get('analysis_type'),
            'portfolio_url': analysis_data.get('portfolio_url'),
            'analysis_results': analysis_data.get('analysis_results'),
            'extracted_data': analysis_data.get('extracted_data'),
            'suggestions': analysis_data.get('suggestions'),
            'score': analysis_data.get('score'),
            'score_breakdown': analysis_data.get('score_breakdown'),
            'processed_at': analysis_data.get('processed_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting portfolio analysis results: {e}")
        return jsonify({'error': 'Failed to get analysis results', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/suggestions/<analysis_id>', methods=['GET'])
@auth_required
def get_portfolio_improvement_suggestions(analysis_id):
    """Get detailed improvement suggestions for portfolio"""
    try:
        user_id = request.user_id
        analysis_data = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        if analysis_data.get('status') != 'completed':
            return jsonify({'error': 'Analysis not completed yet'}), 400
        
        suggestions = analysis_data.get('suggestions', {})
        score_breakdown = analysis_data.get('score_breakdown', {})
        
        return jsonify({
            'analysis_id': analysis_id,
            'type': analysis_data.get('analysis_type'),
            'portfolio_url': analysis_data.get('portfolio_url'),
            'suggestions': suggestions,
            'score': analysis_data.get('score'),
            'score_breakdown': score_breakdown
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting portfolio suggestions: {e}")
        return jsonify({'error': 'Failed to get suggestions', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/user/portfolios', methods=['GET'])
@auth_required
def get_user_portfolio_analyses():
    """Get all portfolio analyses for the authenticated user"""
    try:
        if not portfolio_analysis_model:
            return jsonify({'error': 'Database not available'}), 500
            
        user_id = request.user_id
        analyses = portfolio_analysis_model.get_user_analyses(user_id, 'portfolio')
        
        return jsonify({
            'analyses': analyses,
            'total_count': len(analyses),
            'type': 'portfolio'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting user portfolio analyses: {e}")
        return jsonify({'error': 'Failed to get analyses', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/reanalyze/<analysis_id>', methods=['POST'])
@auth_required
def reanalyze_portfolio(analysis_id):
    """Re-analyze a portfolio with updated user profile"""
    try:
        user_id = request.user_id
        analysis_data = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        portfolio_url = analysis_data.get('portfolio_url')
        
        # Get updated user profile
        user_doc = db.collection('users').document(user_id).get()
        if not user_doc.exists:
            return jsonify({'error': 'User profile not found'}), 404
        
        user_data = user_doc.to_dict()
        user_profile = user_data.get('profile', {})
        
        # Start new analysis
        new_analysis_id, success = portfolio_service.start_portfolio_analysis(
            user_id=user_id,
            portfolio_url=portfolio_url,
            user_profile=user_profile
        )
        
        if not success:
            return jsonify({'error': 'Failed to start re-analysis'}), 500
        
        return jsonify({
            'message': 'Portfolio re-analysis started',
            'new_analysis_id': new_analysis_id,
            'original_analysis_id': analysis_id,
            'status': 'pending'
        }), 200
        
    except Exception as e:
        logger.error(f"Error re-analyzing portfolio: {e}")
        return jsonify({'error': 'Failed to re-analyze portfolio', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/delete/<analysis_id>', methods=['DELETE'])
@auth_required
def delete_portfolio_analysis(analysis_id):
    """Delete a portfolio analysis"""
    try:
        user_id = request.user_id
        analysis_data = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        success = portfolio_analysis_model.delete_analysis(analysis_id)
        
        if success:
            logger.info(f"Successfully deleted portfolio analysis: {analysis_id}")
            return jsonify({'message': 'Portfolio analysis deleted successfully'}), 200
        else:
            return jsonify({'error': 'Failed to delete analysis'}), 500
        
    except Exception as e:
        logger.error(f"Error deleting portfolio analysis: {e}")
        return jsonify({'error': 'Failed to delete analysis', 'details': str(e)}), 500

@portfolio_analysis_bp.route('/extracted-data/<analysis_id>', methods=['GET'])
@auth_required
def get_extracted_portfolio_data(analysis_id):
    """Get raw extracted data from portfolio website"""
    try:
        user_id = request.user_id
        analysis_data = portfolio_analysis_model.get_analysis_by_id(analysis_id)
        
        if not analysis_data or analysis_data.get('user_id') != user_id:
            return jsonify({'error': 'Analysis not found or access denied'}), 404
        
        if analysis_data.get('status') != 'completed':
            return jsonify({'error': 'Analysis not completed yet'}), 400
        
        extracted_data = analysis_data.get('extracted_data', {})
        
        return jsonify({
            'analysis_id': analysis_id,
            'portfolio_url': analysis_data.get('portfolio_url'),
            'extracted_data': extracted_data,
            'extraction_timestamp': analysis_data.get('processed_at')
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting extracted portfolio data: {e}")
        return jsonify({'error': 'Failed to get extracted data', 'details': str(e)}), 500