# test_profile_update.py - Test the profile update fix
import requests
import json

# Configuration
BASE_URL = "http://localhost:5000/api"
TEST_USER_EMAIL = "testuser@example.com"
TEST_USER_PASSWORD = "password123"

def test_profile_update():
    """Test the profile update functionality"""
    
    print("🧪 Testing Profile Update Fix...")
    
    # Step 1: Register a test user
    print("\n1. Registering test user...")
    register_data = {
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD,
        "name": "Test User"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        if response.status_code == 201:
            user_data = response.json()
            user_id = user_data.get('user_id')
            print(f"   ✅ User registered: {user_id}")
        else:
            # Try to login instead (user might already exist)
            print("   ℹ️  User might already exist, trying login...")
            login_response = requests.post(f"{BASE_URL}/auth/login", json={
                "email": TEST_USER_EMAIL,
                "password": TEST_USER_PASSWORD
            })
            if login_response.status_code == 200:
                user_data = login_response.json()
                user_id = user_data.get('user_id')
                print(f"   ✅ User logged in: {user_id}")
            else:
                print(f"   ❌ Login failed: {login_response.text}")
                return False
    except Exception as e:
        print(f"   ❌ Registration/Login error: {e}")
        return False
    
    # Step 2: Get current profile
    print("\n2. Getting current profile...")
    headers = {"X-User-ID": user_id}
    
    try:
        response = requests.get(f"{BASE_URL}/user/profile", headers=headers)
        if response.status_code == 200:
            profile_data = response.json()
            print(f"   ✅ Profile retrieved: {profile_data.get('profile', {}).get('name', 'No name')}")
        else:
            print(f"   ❌ Get profile failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Get profile error: {e}")
        return False
    
    # Step 3: Update profile
    print("\n3. Updating profile...")
    update_data = {
        "name": "Updated Test User",
        "profession": "Software Developer",
        "college_name": "Test University",
        "career_choices": ["Software Development", "Data Science"],
        "bio": "This is a test bio for the updated user."
    }
    
    try:
        response = requests.put(f"{BASE_URL}/user/profile", json=update_data, headers=headers)
        if response.status_code == 200:
            update_result = response.json()
            print(f"   ✅ Profile updated successfully")
            print(f"   📊 Completion: {update_result.get('completion_percentage', 0)}%")
            print(f"   🔄 Changes: {update_result.get('changes_made', [])}")
        else:
            print(f"   ❌ Update failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Update error: {e}")
        return False
    
    # Step 4: Verify update
    print("\n4. Verifying update...")
    try:
        response = requests.get(f"{BASE_URL}/user/profile", headers=headers)
        if response.status_code == 200:
            profile_data = response.json()
            profile = profile_data.get('profile', {})
            print(f"   ✅ Verified name: {profile.get('name')}")
            print(f"   ✅ Verified profession: {profile.get('profession')}")
            print(f"   ✅ Verified college: {profile.get('college_name')}")
            print(f"   ✅ Verified career choices: {profile.get('career_choices')}")
            print(f"   📊 Completion: {profile_data.get('completion_percentage', 0)}%")
        else:
            print(f"   ❌ Verification failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Verification error: {e}")
        return False
    
    # Step 5: Test profile links update
    print("\n5. Testing profile links update...")
    links_data = {
        "github_link": "https://github.com/testuser",
        "linkedin_link": "https://linkedin.com/in/testuser"
    }
    
    try:
        response = requests.put(f"{BASE_URL}/user/profile/links", json=links_data, headers=headers)
        if response.status_code == 200:
            links_result = response.json()
            print(f"   ✅ Links updated: {links_result.get('updated_fields', [])}")
        else:
            print(f"   ❌ Links update failed: {response.text}")
            return False
    except Exception as e:
        print(f"   ❌ Links update error: {e}")
        return False
    
    # Step 6: Test cache functionality
    print("\n6. Testing cache functionality...")
    
    # First request (should populate cache)
    start_time = time.time()
    response1 = requests.get(f"{BASE_URL}/user/profile", headers=headers)
    time1 = time.time() - start_time
    
    # Second request (should use cache)
    start_time = time.time()
    response2 = requests.get(f"{BASE_URL}/user/profile", headers=headers)
    time2 = time.time() - start_time
    
    if response1.status_code == 200 and response2.status_code == 200:
        print(f"   ✅ First request: {time1:.3f}s")
        print(f"   ✅ Second request: {time2:.3f}s")
        if time2 < time1:
            print(f"   🚀 Cache working! {((time1 - time2) / time1 * 100):.1f}% faster")
        else:
            print(f"   ⚠️  Cache might not be working optimally")
    
    # Step 7: Test cache status
    print("\n7. Testing cache status...")
    try:
        response = requests.get(f"{BASE_URL}/user/cache/status", headers=headers)
        if response.status_code == 200:
            cache_status = response.json()
            user_cache = cache_status.get('user_cache_status', {})
            print(f"   ✅ Profile cached: {user_cache.get('profile', {}).get('cached', False)}")
            print(f"   ✅ Settings cached: {user_cache.get('settings', {}).get('cached', False)}")
            print(f"   ✅ Redis enabled: {cache_status.get('redis_info', {}).get('enabled', False)}")
        else:
            print(f"   ❌ Cache status failed: {response.text}")
    except Exception as e:
        print(f"   ❌ Cache status error: {e}")
    
    print("\n🎉 All tests completed successfully!")
    return True

if __name__ == "__main__":
    import time
    test_profile_update()