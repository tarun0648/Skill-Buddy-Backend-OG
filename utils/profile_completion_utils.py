# utils/profile_completion_utils.py (FIXED)
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class ProfileCompletionManager:
    """Utility class to manage profile completion logic - FIXED"""
    
    # Profile completion steps and their percentages
    COMPLETION_STEPS = {
        'name': 10,           # 10%
        'profession': 10,     # 10%
        'career_choices': 10, # 10%
        'college_name': 10,   # 10%
        'college_email': 15,  # 15% (Total basic profile: 55%)
        'github_link': 15,    # 15%
        'linkedin_link': 15,  # 15%
        'resume_uploaded': 15 # 15%
        # Total: 100%
    }
    
    # XP rewards for milestones
    XP_REWARDS = {
        10: 5,   # Name
        20: 5,   # Profession
        30: 5,   # Career choices
        40: 5,   # College name
        55: 15,  # College email (basic profile complete)
        70: 15,  # GitHub or LinkedIn added
        85: 15,  # Both GitHub and LinkedIn, or Resume added
        100: 50  # Complete profile
    }
    
    @staticmethod
    def calculate_completion_percentage(profile: Dict[str, Any]) -> int:
        """Calculate profile completion percentage based on current requirements - FIXED"""
        completion = 0
        
        # Debug logging
        logger.debug(f"Calculating completion for profile keys: {list(profile.keys())}")
        
        # Basic profile steps (55% total)
        name = profile.get('name', '')
        if name and str(name).strip():
            completion += ProfileCompletionManager.COMPLETION_STEPS['name']
            logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['name']}% for name: '{name}'")
        
        profession = profile.get('profession', '')
        if profession and str(profession).strip():
            completion += ProfileCompletionManager.COMPLETION_STEPS['profession']
            logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['profession']}% for profession: '{profession}'")
        
        career_choices = profile.get('career_choices', [])
        if career_choices and isinstance(career_choices, list):
            # Check if any choice is not empty
            valid_choices = [choice for choice in career_choices if choice and str(choice).strip()]
            if valid_choices:
                completion += ProfileCompletionManager.COMPLETION_STEPS['career_choices']
                logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['career_choices']}% for career_choices: {valid_choices}")
        
        college_name = profile.get('college_name', '')
        if college_name and str(college_name).strip():
            completion += ProfileCompletionManager.COMPLETION_STEPS['college_name']
            logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['college_name']}% for college_name: '{college_name}'")
        
        college_email = profile.get('college_email', '')
        if college_email and str(college_email).strip():
            completion += ProfileCompletionManager.COMPLETION_STEPS['college_email']
            logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['college_email']}% for college_email: '{college_email}'")
        
        # Additional profile elements (45% total)
        github_link = profile.get('github_link', '')
        if github_link and str(github_link).strip() and str(github_link).strip() != '':
            completion += ProfileCompletionManager.COMPLETION_STEPS['github_link']
            logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['github_link']}% for github_link: '{github_link}'")
        
        linkedin_link = profile.get('linkedin_link', '')
        if linkedin_link and str(linkedin_link).strip() and str(linkedin_link).strip() != '':
            completion += ProfileCompletionManager.COMPLETION_STEPS['linkedin_link']
            logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['linkedin_link']}% for linkedin_link: '{linkedin_link}'")
        
        has_resume = profile.get('has_resume', False)
        if has_resume is True:
            completion += ProfileCompletionManager.COMPLETION_STEPS['resume_uploaded']
            logger.debug(f"Added {ProfileCompletionManager.COMPLETION_STEPS['resume_uploaded']}% for has_resume: {has_resume}")
        
        final_completion = min(completion, 100)
        logger.debug(f"Final completion percentage: {final_completion}%")
        return final_completion
    
    @staticmethod
    def get_milestones_reached(old_completion: int, new_completion: int) -> List[int]:
        """Get milestones that were just reached"""
        milestones = [10, 20, 30, 40, 55, 70, 85, 100]
        reached = []
        
        for milestone in milestones:
            if old_completion < milestone <= new_completion:
                reached.append(milestone)
        
        return reached
    
    @staticmethod
    def calculate_xp_bonus(milestones: List[int]) -> int:
        """Calculate XP bonus for reached milestones"""
        xp_bonus = 0
        
        for milestone in milestones:
            xp_bonus += ProfileCompletionManager.XP_REWARDS.get(milestone, 0)
        
        return xp_bonus
    
    @staticmethod
    def get_next_steps(profile: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get next steps for profile completion - FIXED"""
        completion_status = ProfileCompletionManager.calculate_completion_percentage(profile)
        next_steps = []
        
        # Basic profile steps (55% total)
        if not profile.get('name') or not str(profile.get('name')).strip():
            next_steps.append({
                'step': 'name',
                'description': 'Add your name',
                'completion': 10,
                'category': 'basic',
                'priority': 'high'
            })
        elif not profile.get('profession') or not str(profile.get('profession')).strip():
            next_steps.append({
                'step': 'profession',
                'description': 'Select your profession',
                'completion': 20,
                'category': 'basic',
                'priority': 'high'
            })
        elif not profile.get('career_choices') or len([c for c in profile.get('career_choices', []) if c and str(c).strip()]) == 0:
            next_steps.append({
                'step': 'career_choices',
                'description': 'Choose your career interests',
                'completion': 30,
                'category': 'basic',
                'priority': 'high'
            })
        elif not profile.get('college_name') or not str(profile.get('college_name')).strip():
            next_steps.append({
                'step': 'college_name',
                'description': 'Add your college/university name',
                'completion': 40,
                'category': 'basic',
                'priority': 'high'
            })
        elif not profile.get('college_email') or not str(profile.get('college_email')).strip():
            next_steps.append({
                'step': 'college_email',
                'description': 'Add your college email',
                'completion': 55,
                'category': 'basic',
                'priority': 'high'
            })
        
        # Additional steps (45% total) - only show after basic profile is complete
        if completion_status >= 55:
            github_link = profile.get('github_link', '')
            linkedin_link = profile.get('linkedin_link', '')
            has_resume = profile.get('has_resume', False)
            
            if not github_link or not str(github_link).strip():
                next_steps.append({
                    'step': 'github_link',
                    'description': 'Add your GitHub profile link',
                    'completion': 70,
                    'category': 'additional',
                    'priority': 'medium'
                })
            
            if not linkedin_link or not str(linkedin_link).strip():
                next_steps.append({
                    'step': 'linkedin_link',
                    'description': 'Add your LinkedIn profile link',
                    'completion': 85,
                    'category': 'additional',
                    'priority': 'medium'
                })
            
            if not has_resume:
                next_steps.append({
                    'step': 'resume_upload',
                    'description': 'Upload your resume',
                    'completion': 100,
                    'category': 'additional',
                    'priority': 'medium'
                })
        
        return next_steps
    
    @staticmethod
    def get_completion_breakdown(profile: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed completion breakdown - FIXED"""
        completion_status = ProfileCompletionManager.calculate_completion_percentage(profile)
        
        # Individual component status
        name_complete = bool(profile.get('name') and str(profile.get('name')).strip())
        profession_complete = bool(profile.get('profession') and str(profile.get('profession')).strip())
        career_choices_complete = bool(profile.get('career_choices') and 
                                     len([c for c in profile.get('career_choices', []) if c and str(c).strip()]) > 0)
        college_name_complete = bool(profile.get('college_name') and str(profile.get('college_name')).strip())
        college_email_complete = bool(profile.get('college_email') and str(profile.get('college_email')).strip())
        github_linked = bool(profile.get('github_link') and str(profile.get('github_link')).strip())
        linkedin_linked = bool(profile.get('linkedin_link') and str(profile.get('linkedin_link')).strip())
        resume_uploaded = bool(profile.get('has_resume'))
        
        return {
            'total_completion': completion_status,
            'basic_profile': min(completion_status, 55),
            'basic_profile_complete': completion_status >= 55,
            'additional_completion': max(0, completion_status - 55) if completion_status > 55 else 0,
            'components': {
                'name': name_complete,
                'profession': profession_complete,
                'career_choices': career_choices_complete,
                'college_name': college_name_complete,
                'college_email': college_email_complete,
                'github_linked': github_linked,
                'linkedin_linked': linkedin_linked,
                'resume_uploaded': resume_uploaded
            },
            'component_percentages': {
                'name': ProfileCompletionManager.COMPLETION_STEPS['name'] if name_complete else 0,
                'profession': ProfileCompletionManager.COMPLETION_STEPS['profession'] if profession_complete else 0,
                'career_choices': ProfileCompletionManager.COMPLETION_STEPS['career_choices'] if career_choices_complete else 0,
                'college_name': ProfileCompletionManager.COMPLETION_STEPS['college_name'] if college_name_complete else 0,
                'college_email': ProfileCompletionManager.COMPLETION_STEPS['college_email'] if college_email_complete else 0,
                'github_link': ProfileCompletionManager.COMPLETION_STEPS['github_link'] if github_linked else 0,
                'linkedin_link': ProfileCompletionManager.COMPLETION_STEPS['linkedin_link'] if linkedin_linked else 0,
                'resume_uploaded': ProfileCompletionManager.COMPLETION_STEPS['resume_uploaded'] if resume_uploaded else 0
            },
            'percentages': ProfileCompletionManager.COMPLETION_STEPS
        }
    
    @staticmethod
    def validate_profile_data(profile: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean profile data for completion calculation"""
        cleaned_profile = {}
        
        # Clean and validate each field
        cleaned_profile['name'] = str(profile.get('name', '')).strip()
        cleaned_profile['profession'] = str(profile.get('profession', '')).strip()
        
        # Handle career choices
        career_choices = profile.get('career_choices', [])
        if isinstance(career_choices, list):
            cleaned_profile['career_choices'] = [str(choice).strip() for choice in career_choices if choice and str(choice).strip()]
        else:
            cleaned_profile['career_choices'] = []
        
        cleaned_profile['college_name'] = str(profile.get('college_name', '')).strip()
        cleaned_profile['college_email'] = str(profile.get('college_email', '')).strip()
        cleaned_profile['github_link'] = str(profile.get('github_link', '')).strip()
        cleaned_profile['linkedin_link'] = str(profile.get('linkedin_link', '')).strip()
        cleaned_profile['has_resume'] = bool(profile.get('has_resume', False))
        
        return cleaned_profile
    
    @staticmethod
    def get_milestones_info() -> Dict[str, Any]:
        """Get information about completion milestones"""
        return {
            'milestones': [
                {
                    'percentage': 10,
                    'description': 'Added name',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[10],
                    'category': 'basic'
                },
                {
                    'percentage': 20,
                    'description': 'Selected profession',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[20],
                    'category': 'basic'
                },
                {
                    'percentage': 30,
                    'description': 'Chose career interests',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[30],
                    'category': 'basic'
                },
                {
                    'percentage': 40,
                    'description': 'Added college name',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[40],
                    'category': 'basic'
                },
                {
                    'percentage': 55,
                    'description': 'Basic profile complete',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[55],
                    'category': 'basic'
                },
                {
                    'percentage': 70,
                    'description': 'Added GitHub or LinkedIn',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[70],
                    'category': 'additional'
                },
                {
                    'percentage': 85,
                    'description': 'Added social links or resume',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[85],
                    'category': 'additional'
                },
                {
                    'percentage': 100,
                    'description': 'Profile fully complete',
                    'xp_reward': ProfileCompletionManager.XP_REWARDS[100],
                    'category': 'complete'
                }
            ],
            'total_possible_xp': sum(ProfileCompletionManager.XP_REWARDS.values()),
            'basic_profile_xp': sum([ProfileCompletionManager.XP_REWARDS[m] for m in [10, 20, 30, 40, 55]]),
            'additional_profile_xp': sum([ProfileCompletionManager.XP_REWARDS[m] for m in [70, 85, 100]])
        }