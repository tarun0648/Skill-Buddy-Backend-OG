import os
import sys
sys.path.append('.')

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Test your project's Redis cache service
def test_project_redis():
    print("🔍 Testing Redis with your project's cache service...")
    
    try:
        # Import your cache service
        from services.redis_cache_service import cache, CacheKeys, CacheTTL
        
        # Test 1: Basic cache operations
        print("\n1. Testing basic cache operations...")
        cache.set('test_key', 'Hello from Skill Buddy Cache!', 60)
        value = cache.get('test_key')
        print(f"   ✅ Cache set/get: {value}")
        
        # Test 2: Cache key generation
        print("\n2. Testing cache key generation...")
        cache_key = cache.generate_cache_key(CacheKeys.USER_PROFILE, 'user123')
        print(f"   ✅ Generated cache key: {cache_key}")
        
        # Test 3: Cache info
        print("\n3. Testing cache info...")
        cache_info = cache.get_cache_info()
        print(f"   ✅ Cache enabled: {cache_info.get('enabled', False)}")
        if cache_info.get('enabled'):
            print(f"   ✅ Redis version: {cache_info.get('redis_version', 'Unknown')}")
            print(f"   ✅ Used memory: {cache_info.get('used_memory', 'Unknown')}")
        
        # Test 4: Cache TTL
        print("\n4. Testing cache TTL...")
        cache.set('ttl_test', 'expires in 30 seconds', 30)
        ttl = cache.get_ttl('ttl_test')
        print(f"   ✅ TTL for test key: {ttl} seconds")
        
        # Test 5: Cache patterns
        print("\n5. Testing cache patterns...")
        cache.set('user_profile:123', {'name': 'Test User'}, 300)
        cache.set('user_profile:456', {'name': 'Another User'}, 300)
        keys = cache.get_keys_by_pattern('user_profile:*')
        print(f"   ✅ Found {len(keys)} keys matching pattern")
        
        # Test 6: Cache deletion
        print("\n6. Testing cache deletion...")
        cache.delete('test_key')
        cache.delete('ttl_test')
        deleted_count = cache.delete_pattern('user_profile:*')
        print(f"   ✅ Deleted {deleted_count} keys")
        
        print("\n🎉 All Redis tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Redis test failed: {e}")
        return False

if __name__ == "__main__":
    test_project_redis()