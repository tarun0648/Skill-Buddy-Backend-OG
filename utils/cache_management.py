# utils/cache_management.py
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from services.redis_cache_service import cache, CacheKeys, CacheTTL
import json

logger = logging.getLogger(__name__)

class CacheManager:
    """Utility class for advanced cache management operations"""
    
    def __init__(self):
        self.cache = cache
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        try:
            # Get basic cache info
            cache_info = self.cache.get_cache_info()
            
            # Get key patterns and counts
            key_patterns = {
                'user_profiles': f"{CacheKeys.USER_PROFILE}:*",
                'user_resumes': f"{CacheKeys.USER_RESUMES}:*",
                'user_stats': f"{CacheKeys.USER_STATS}:*",
                'user_settings': f"{CacheKeys.USER_SETTINGS}:*",
                'resume_content': f"{CacheKeys.RESUME_CONTENT}:*",
                'resume_analysis': f"{CacheKeys.RESUME_ANALYSIS}:*",
                'resume_questions': f"{CacheKeys.RESUME_QUESTIONS}:*",
                'resume_status': f"{CacheKeys.RESUME_STATUS}:*",
                'profile_analysis': f"{CacheKeys.PROFILE_ANALYSIS}:*",
                'profile_analysis_results': f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:*",
                'profile_analysis_suggestions': f"{CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS}:*",
                'portfolio_analysis': f"{CacheKeys.PORTFOLIO_ANALYSIS}:*",
                'portfolio_analysis_results': f"{CacheKeys.PORTFOLIO_ANALYSIS_RESULTS}:*",
                'portfolio_analysis_suggestions': f"{CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS}:*",
                'community_posts': f"{CacheKeys.COMMUNITY_POSTS}:*",
                'community_post': f"{CacheKeys.COMMUNITY_POST}:*",
                'community_replies': f"{CacheKeys.COMMUNITY_REPLIES}:*",
                'community_stats': f"{CacheKeys.COMMUNITY_STATS}:*",
                'github_profiles': f"{CacheKeys.GITHUB_PROFILE}:*",
                'linkedin_profiles': f"{CacheKeys.LINKEDIN_PROFILE}:*",
                'system_stats': f"{CacheKeys.SYSTEM_STATS}:*"
            }
            
            pattern_counts = {}
            total_keys = 0
            
            for pattern_name, pattern in key_patterns.items():
                keys = self.cache.get_keys_by_pattern(pattern)
                pattern_counts[pattern_name] = len(keys)
                total_keys += len(keys)
            
            # Calculate hit rate
            hit_rate = 0
            if cache_info.get('keyspace_hits', 0) + cache_info.get('keyspace_misses', 0) > 0:
                hit_rate = cache_info.get('keyspace_hits', 0) / (
                    cache_info.get('keyspace_hits', 0) + cache_info.get('keyspace_misses', 0)
                ) * 100
            
            return {
                'cache_info': cache_info,
                'pattern_counts': pattern_counts,
                'total_keys': total_keys,
                'hit_rate_percentage': round(hit_rate, 2),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting cache statistics: {e}")
            return {'error': str(e)}
    
    def get_user_cache_summary(self, user_id: str) -> Dict[str, Any]:
        """Get cache summary for a specific user"""
        try:
            user_patterns = {
                'profile': f"{CacheKeys.USER_PROFILE}:{user_id}*",
                'resumes': f"{CacheKeys.USER_RESUMES}:{user_id}*",
                'stats': f"{CacheKeys.USER_STATS}:{user_id}*",
                'settings': f"{CacheKeys.USER_SETTINGS}:{user_id}*",
                'resume_content': f"{CacheKeys.RESUME_CONTENT}:{user_id}*",
                'resume_analysis': f"{CacheKeys.RESUME_ANALYSIS}:{user_id}*",
                'resume_questions': f"{CacheKeys.RESUME_QUESTIONS}:{user_id}*",
                'resume_status': f"{CacheKeys.RESUME_STATUS}:{user_id}*",
                'profile_analysis': f"{CacheKeys.PROFILE_ANALYSIS}:{user_id}*",
                'profile_analysis_results': f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:{user_id}*",
                'profile_analysis_suggestions': f"{CacheKeys.PROFILE_ANALYSIS_SUGGESTIONS}:{user_id}*",
                'portfolio_analysis': f"{CacheKeys.PORTFOLIO_ANALYSIS}:{user_id}*",
                'portfolio_analysis_results': f"{CacheKeys.PORTFOLIO_ANALYSIS_RESULTS}:{user_id}*",
                'portfolio_analysis_suggestions': f"{CacheKeys.PORTFOLIO_ANALYSIS_SUGGESTIONS}:{user_id}*",
                'github_profile': f"{CacheKeys.GITHUB_PROFILE}:{user_id}*",
                'linkedin_profile': f"{CacheKeys.LINKEDIN_PROFILE}:{user_id}*"
            }
            
            user_cache_data = {}
            total_user_keys = 0
            
            for category, pattern in user_patterns.items():
                keys = self.cache.get_keys_by_pattern(pattern)
                user_cache_data[category] = {
                    'count': len(keys),
                    'keys': keys[:5]  # Show first 5 keys as examples
                }
                total_user_keys += len(keys)
            
            return {
                'user_id': user_id,
                'total_cache_entries': total_user_keys,
                'cache_breakdown': user_cache_data,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting user cache summary: {e}")
            return {'error': str(e)}
    
    def cleanup_expired_cache(self) -> Dict[str, Any]:
        """Clean up expired cache entries"""
        try:
            # Get all keys
            all_keys = self.cache.get_keys_by_pattern('*')
            
            expired_keys = []
            active_keys = []
            
            for key in all_keys:
                ttl = self.cache.get_ttl(key)
                if ttl == -2:  # Key doesn't exist
                    expired_keys.append(key)
                elif ttl == -1:  # Key exists but no expiration
                    active_keys.append(key)
                elif ttl > 0:  # Key exists with expiration
                    active_keys.append(key)
            
            # Remove expired keys
            for key in expired_keys:
                self.cache.delete(key)
            
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return {
                'cleaned_keys': len(expired_keys),
                'active_keys': len(active_keys),
                'total_keys_checked': len(all_keys),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error cleaning up expired cache: {e}")
            return {'error': str(e)}
    
    def warm_up_user_cache(self, user_id: str, user_model=None, resume_model=None) -> Dict[str, Any]:
        """Warm up cache for a specific user"""
        try:
            warmed_items = []
            
            # Warm up user profile
            if user_model:
                try:
                    user_data = user_model.get_user_by_id(user_id)
                    if user_data:
                        profile_key = self.cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id)
                        self.cache.set(profile_key, user_data, CacheTTL.USER_PROFILE)
                        warmed_items.append('user_profile')
                        
                        # Warm up profile completion
                        completion_key = self.cache.generate_cache_key(CacheKeys.USER_PROFILE, user_id, 'completion')
                        completion_data = user_model.calculate_profile_completion(user_data.get('profile', {}))
                        self.cache.set(completion_key, {'completion_percentage': completion_data}, CacheTTL.USER_PROFILE)
                        warmed_items.append('profile_completion')
                        
                        # Warm up user stats
                        stats_key = self.cache.generate_cache_key(CacheKeys.USER_STATS, user_id)
                        stats_data = user_model.get_user_statistics(user_id)
                        self.cache.set(stats_key, stats_data, CacheTTL.USER_STATS)
                        warmed_items.append('user_stats')
                        
                        # Warm up user settings
                        settings_key = self.cache.generate_cache_key(CacheKeys.USER_SETTINGS, user_id)
                        settings_data = user_data.get('settings', {})
                        self.cache.set(settings_key, {'settings': settings_data}, CacheTTL.USER_SETTINGS)
                        warmed_items.append('user_settings')
                        
                except Exception as e:
                    logger.warning(f"Failed to warm up user data: {e}")
            
            # Warm up resume data
            if resume_model:
                try:
                    resumes = resume_model.get_user_resume_summary(user_id)
                    if resumes:
                        resumes_key = self.cache.generate_cache_key(CacheKeys.USER_RESUMES, user_id, 'details:false', 'limit:50')
                        self.cache.set(resumes_key, {'resumes': resumes}, CacheTTL.USER_RESUMES)
                        warmed_items.append('user_resumes')
                        
                        # Warm up individual resume data
                        for resume in resumes[:5]:  # Warm up first 5 resumes
                            resume_id = resume.get('id')
                            if resume_id and resume.get('status') == 'completed':
                                # Warm up resume status
                                status_key = self.cache.generate_cache_key(CacheKeys.RESUME_STATUS, user_id, resume_id)
                                status_data = {
                                    'resume_id': resume_id,
                                    'status': resume.get('status'),
                                    'filename': resume.get('original_filename')
                                }
                                self.cache.set(status_key, status_data, CacheTTL.VERY_LONG)
                                warmed_items.append(f'resume_status_{resume_id}')
                                
                except Exception as e:
                    logger.warning(f"Failed to warm up resume data: {e}")
            
            logger.info(f"Warmed up {len(warmed_items)} cache items for user {user_id}")
            
            return {
                'user_id': user_id,
                'warmed_items': warmed_items,
                'total_warmed': len(warmed_items),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error warming up user cache: {e}")
            return {'error': str(e)}
    
    def optimize_cache_memory(self) -> Dict[str, Any]:
        """Optimize cache memory usage by cleaning up old entries"""
        try:
            # Get memory info before optimization
            initial_info = self.cache.get_cache_info()
            
            # Clean up old entries based on access patterns
            optimization_results = {
                'cleaned_patterns': [],
                'memory_freed': 0,
                'keys_removed': 0
            }
            
            # Define cleanup strategies for different key types
            cleanup_strategies = {
                # Clean up old resume processing status for completed resumes
                f"{CacheKeys.RESUME_STATUS}:*": {
                    'max_age_hours': 24,
                    'keep_recent': 50
                },
                # Clean up old community posts cache
                f"{CacheKeys.COMMUNITY_POSTS}:*": {
                    'max_age_hours': 2,
                    'keep_recent': 20
                },
                # Clean up old profile analysis results
                f"{CacheKeys.PROFILE_ANALYSIS_RESULTS}:*": {
                    'max_age_hours': 48,
                    'keep_recent': 100
                },
                # Clean up old portfolio analysis results
                f"{CacheKeys.PORTFOLIO_ANALYSIS_RESULTS}:*": {
                    'max_age_hours': 48,
                    'keep_recent': 100
                }
            }
            
            for pattern, strategy in cleanup_strategies.items():
                keys = self.cache.get_keys_by_pattern(pattern)
                
                # Sort keys by TTL (keys with lower TTL are older)
                key_ttls = []
                for key in keys:
                    ttl = self.cache.get_ttl(key)
                    if ttl > 0:
                        key_ttls.append((key, ttl))
                
                # Sort by TTL ascending (oldest first)
                key_ttls.sort(key=lambda x: x[1])
                
                # Remove old entries beyond keep_recent limit
                if len(key_ttls) > strategy['keep_recent']:
                    keys_to_remove = key_ttls[:-strategy['keep_recent']]
                    for key, ttl in keys_to_remove:
                        self.cache.delete(key)
                        optimization_results['keys_removed'] += 1
                
                optimization_results['cleaned_patterns'].append({
                    'pattern': pattern,
                    'total_keys': len(keys),
                    'removed_keys': len(keys_to_remove) if len(key_ttls) > strategy['keep_recent'] else 0
                })
            
            # Get memory info after optimization
            final_info = self.cache.get_cache_info()
            
            logger.info(f"Cache optimization completed, removed {optimization_results['keys_removed']} keys")
            
            return {
                'optimization_results': optimization_results,
                'memory_before': initial_info.get('used_memory', 'unknown'),
                'memory_after': final_info.get('used_memory', 'unknown'),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error optimizing cache memory: {e}")
            return {'error': str(e)}
    
    def get_cache_health_report(self) -> Dict[str, Any]:
        """Generate a comprehensive cache health report"""
        try:
            # Get basic statistics
            stats = self.get_cache_statistics()
            
            # Check for potential issues
            issues = []
            recommendations = []
            
            # Check hit rate
            hit_rate = stats.get('hit_rate_percentage', 0)
            if hit_rate < 50:
                issues.append('Low cache hit rate')
                recommendations.append('Consider increasing cache TTL or warming up cache more frequently')
            
            # Check memory usage
            cache_info = stats.get('cache_info', {})
            if cache_info.get('used_memory'):
                # This is a simplified check - you might want to implement more sophisticated memory monitoring
                issues.append('Monitor memory usage')
                recommendations.append('Consider implementing cache size limits or cleanup strategies')
            
            # Check key distribution
            pattern_counts = stats.get('pattern_counts', {})
            total_keys = stats.get('total_keys', 0)
            
            if total_keys > 10000:
                issues.append('High number of cache keys')
                recommendations.append('Consider implementing cache cleanup or key expiration strategies')
            
            # Check for imbalanced key distribution
            if pattern_counts:
                max_count = max(pattern_counts.values())
                if max_count > total_keys * 0.5:  # More than 50% of keys in one category
                    issues.append('Imbalanced key distribution')
                    recommendations.append('Review caching strategy for key distribution')
            
            health_score = 100
            if issues:
                health_score -= len(issues) * 10
            
            return {
                'health_score': max(0, health_score),
                'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
                'statistics': stats,
                'issues': issues,
                'recommendations': recommendations,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating cache health report: {e}")
            return {'error': str(e)}

# Initialize global cache manager
cache_manager = CacheManager()