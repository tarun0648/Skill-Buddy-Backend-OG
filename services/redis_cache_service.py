# services/redis_cache_service.py
import redis
import json
import logging
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta
import os
from functools import wraps
import hashlib

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis caching service for the application"""
    
    def __init__(self):
        self.redis_client = None
        self.enabled = False
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Initialize Redis connection"""
        try:
            # Try to connect to Redis
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            
            # Parse Redis URL for different configurations
            if redis_url.startswith('redis://'):
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                # Default local configuration
                self.redis_client = redis.Redis(
                    host=os.environ.get('REDIS_HOST', 'localhost'),
                    port=int(os.environ.get('REDIS_PORT', 6379)),
                    db=int(os.environ.get('REDIS_DB', 0)),
                    password=os.environ.get('REDIS_PASSWORD'),
                    decode_responses=True
                )
            
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache initialized successfully")
            
        except Exception as e:
            logger.warning(f"Redis initialization failed: {e}. Caching will be disabled.")
            self.enabled = False
    
    def _serialize_data(self, data: Any) -> str:
        """Serialize data for Redis storage"""
        try:
            if isinstance(data, (dict, list)):
                return json.dumps(data, default=str)
            else:
                return str(data)
        except Exception as e:
            logger.error(f"Failed to serialize data: {e}")
            return str(data)
    
    def _deserialize_data(self, data: str) -> Any:
        """Deserialize data from Redis"""
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
        except Exception as e:
            logger.error(f"Failed to deserialize data: {e}")
            return data
    
    def generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from prefix and arguments"""
        key_parts = [prefix]
        
        # Add positional arguments
        for arg in args:
            key_parts.append(str(arg))
        
        # Add keyword arguments (sorted for consistency)
        for key, value in sorted(kwargs.items()):
            key_parts.append(f"{key}:{value}")
        
        cache_key = ":".join(key_parts)
        
        # If key is too long, hash it
        if len(cache_key) > 200:
            cache_key = f"{prefix}:{hashlib.md5(cache_key.encode()).hexdigest()}"
        
        return cache_key
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.enabled:
            return None
        
        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return self._deserialize_data(cached_data)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        """Set value in cache with expiration"""
        if not self.enabled:
            return False
        
        try:
            serialized_data = self._serialize_data(value)
            return self.redis_client.setex(key, expire, serialized_data)
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled:
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for pattern {pattern}: {e}")
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if not self.enabled:
            return False
        
        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """Get time-to-live for a key"""
        if not self.enabled:
            return -1
        
        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {e}")
            return -1
    
    def extend_ttl(self, key: str, expire: int) -> bool:
        """Extend TTL for an existing key"""
        if not self.enabled:
            return False
        
        try:
            return self.redis_client.expire(key, expire)
        except Exception as e:
            logger.error(f"Cache extend TTL error for key {key}: {e}")
            return False
    
    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment a numeric value"""
        if not self.enabled:
            return None
        
        try:
            return self.redis_client.incr(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get cache information and statistics"""
        if not self.enabled:
            return {'enabled': False, 'error': 'Redis not available'}
        
        try:
            info = self.redis_client.info()
            return {
                'enabled': True,
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', '0B'),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'redis_version': info.get('redis_version', 'unknown')
            }
        except Exception as e:
            logger.error(f"Cache info error: {e}")
            return {'enabled': False, 'error': str(e)}
    
    def clear_all(self) -> bool:
        """Clear all cache (use with caution)"""
        if not self.enabled:
            return False
        
        try:
            return self.redis_client.flushdb()
        except Exception as e:
            logger.error(f"Cache clear all error: {e}")
            return False
    
    def get_keys_by_pattern(self, pattern: str) -> List[str]:
        """Get all keys matching a pattern"""
        if not self.enabled:
            return []
        
        try:
            return self.redis_client.keys(pattern)
        except Exception as e:
            logger.error(f"Cache keys pattern error: {e}")
            return []


# Cache decorators
def cache_result(cache_key_prefix: str, expire: int = 3600, include_user_id: bool = True):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = RedisCache()
            
            if not cache.enabled:
                return func(*args, **kwargs)
            
            # Generate cache key
            key_parts = [cache_key_prefix]
            
            # Include user_id if requested and available
            if include_user_id and hasattr(args[0], 'user_id'):
                key_parts.append(args[0].user_id)
            
            cache_key = cache.generate_cache_key(*key_parts, *args[1:], **kwargs)
            
            # Try to get from cache first
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, expire)
                logger.info(f"Cache set for key: {cache_key}")
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """Decorator to invalidate cache patterns after function execution"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            cache = RedisCache()
            if cache.enabled:
                deleted_count = cache.delete_pattern(pattern)
                if deleted_count > 0:
                    logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
            
            return result
        
        return wrapper
    return decorator


# Cache key constants
class CacheKeys:
    """Cache key constants for different types of data"""
    
    USER_PROFILE = "user_profile"
    USER_RESUMES = "user_resumes"
    USER_STATS = "user_stats"
    USER_SETTINGS = "user_settings"
    
    RESUME_CONTENT = "resume_content"
    RESUME_ANALYSIS = "resume_analysis"
    RESUME_QUESTIONS = "resume_questions"
    RESUME_STATUS = "resume_status"
    
    PROFILE_ANALYSIS = "profile_analysis"
    PROFILE_ANALYSIS_RESULTS = "profile_analysis_results"
    PROFILE_ANALYSIS_SUGGESTIONS = "profile_analysis_suggestions"
    
    PORTFOLIO_ANALYSIS = "portfolio_analysis"
    PORTFOLIO_ANALYSIS_RESULTS = "portfolio_analysis_results"
    PORTFOLIO_ANALYSIS_SUGGESTIONS = "portfolio_analysis_suggestions"
    
    COMMUNITY_POSTS = "community_posts"
    COMMUNITY_POST = "community_post"
    COMMUNITY_REPLIES = "community_replies"
    COMMUNITY_STATS = "community_stats"
    
    GITHUB_PROFILE = "github_profile"
    LINKEDIN_PROFILE = "linkedin_profile"
    
    SYSTEM_STATS = "system_stats"


# Cache TTL constants (in seconds)
class CacheTTL:
    """Cache TTL constants for different types of data"""
    
    SHORT = 300      # 5 minutes
    MEDIUM = 1800    # 30 minutes
    LONG = 3600      # 1 hour
    VERY_LONG = 86400  # 24 hours
    
    # Specific TTLs
    USER_PROFILE = MEDIUM
    USER_RESUMES = LONG
    USER_STATS = LONG
    
    RESUME_CONTENT = VERY_LONG
    RESUME_ANALYSIS = VERY_LONG
    
    PROFILE_ANALYSIS = VERY_LONG
    PORTFOLIO_ANALYSIS = VERY_LONG
    
    COMMUNITY_POSTS = SHORT
    COMMUNITY_POST = MEDIUM
    
    GITHUB_PROFILE = LONG
    LINKEDIN_PROFILE = LONG
    
    SYSTEM_STATS = MEDIUM


# Initialize global cache instance
cache = RedisCache()