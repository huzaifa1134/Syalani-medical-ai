"""
Startup Checker - Verify all configurations before running the app
Run this first: python startup_checker.py
"""

import os
import sys
from pathlib import Path

def check_env_file():
    """Check if .env file exists and is readable"""
    print("🔍 Checking .env file...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found in project root!")
        print(f"   Looking for: {env_path.absolute()}")
        print("   Create .env file in the same directory as this script")
        return False
    
    print(f"✅ .env file found at: {env_path.absolute()}")
    
    # Read and validate required variables
    required_vars = [
        "MONGODB_URI",
        "GEMINI_API_KEY",
        "WABA_API_URL",
        "WABA_PHONE_NUMBER_ID",
        "WABA_ACCESS_TOKEN",
        "WABA_VERIFY_TOKEN",
        "GCP_PROJECT_ID",
        "GOOGLE_APPLICATION_CREDENTIALS"
    ]
    
    missing = []
    with open(env_path, 'r', encoding='utf-8') as f:
        content = f.read()
        for var in required_vars:
            if var not in content:
                missing.append(var)
    
    if missing:
        print(f"❌ Missing variables in .env: {', '.join(missing)}")
        return False
    
    print(f"✅ All required variables present in .env")
    return True


def check_config_file():
    """Check if config.py is correct"""
    print("\n🔍 Checking config.py...")
    
    config_path = Path("app/config.py")
    if not config_path.exists():
        print("❌ app/config.py not found!")
        return False
    
    print("✅ config.py found")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
        # Check for common errors
        errors = []
        
        if "pydantic-settings" in content:
            errors.append("Line 1: Use 'pydantic_settings' not 'pydantic-settings'")
        
        if 'MONGODB_COLLECTION: str = doctors' in content:
            errors.append("Missing quotes around 'doctors' in MONGODB_COLLECTION")
        
        if 'CONTEXT_TTL: INT' in content:
            errors.append("Use lowercase 'int' not 'INT' for CONTEXT_TTL")
        
        if 'env_file:' in content and '.env' not in content:
            errors.append("Config class env_file missing or incorrect")
        
        if errors:
            print("❌ Errors found in config.py:")
            for error in errors:
                print(f"   - {error}")
            return False
    
    print("✅ config.py looks good")
    return True


def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'pydantic_settings',
        'pymongo',
        'redis',
        'google-cloud-speech',
        'google-cloud-texttospeech',
        'google-generativeai',
        'httpx',
        'python-dotenv',
        'structlog'
    ]
    
    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing packages: {', '.join(missing)}")
        print(f"\n   Install with: pip install {' '.join(missing)}")
        return False
    
    print("✅ All required packages installed")
    return True


def check_google_credentials():
    """Check Google Cloud credentials file"""
    print("\n🔍 Checking Google Cloud credentials...")
    
    cred_path = Path("service-account-key.json")
    if not cred_path.exists():
        print("⚠️  service-account-key.json not found")
        print("   Google Cloud services (STT/TTS) will not work")
        print("   Get credentials from: https://console.cloud.google.com/")
        return False
    
    print("✅ Google credentials file found")
    return True


def test_config_loading():
    """Try to load the config"""
    print("\n🔍 Testing config loading...")
    
    try:
        from app.config import get_settings
        settings = get_settings()
        
        print("✅ Config loaded successfully!")
        print(f"\n📋 Configuration Summary:")
        print(f"   App Name: {settings.APP_NAME}")
        print(f"   Environment: {settings.ENV}")
        print(f"   Debug Mode: {settings.DEBUG}")
        print(f"   Port: {settings.PORT}")
        print(f"   MongoDB: {settings.MONGODB_URI[:30]}...")
        print(f"   WhatsApp Phone ID: {settings.WABA_PHONE_NUMBER_ID}")
        print(f"   WhatsApp API URL: {settings.WABA_API_URL}")
        print(f"   Verify Token: {settings.WABA_VERIFY_TOKEN}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to load config: {e}")
        return False


def check_redis():
    """Check Redis connection"""
    print("\n🔍 Checking Redis...")
    
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0)
        r.ping()
        print("✅ Redis is running")
        return True
    except Exception as e:
        print("⚠️  Redis not available (optional for testing)")
        print(f"   Error: {e}")
        print("   To skip Redis, comment out Redis connections in main.py")
        return False


def check_mongodb():
    """Check MongoDB connection"""
    print("\n🔍 Checking MongoDB...")
    
    try:
        from app.config import get_settings
        from pymongo import MongoClient
        
        settings = get_settings()
        client = MongoClient(settings.MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("✅ MongoDB connection successful")
        client.close()
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("   Check MongoDB Atlas IP whitelist")
        return False


def main():
    print("=" * 60)
    print("🚀 WhatsApp AI - Startup Configuration Checker")
    print("=" * 60)
    
    checks = [
        check_env_file(),
        check_config_file(),
        check_dependencies(),
        check_google_credentials(),
        test_config_loading(),
    ]
    
    # Optional checks
    print("\n" + "=" * 60)
    print("Optional Checks (can skip for basic testing)")
    print("=" * 60)
    check_redis()
    check_mongodb()
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ All critical checks passed!")
        print("\nYou can now run:")
        print("   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    else:
        print("❌ Some checks failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("1. Create/fix .env file in project root")
        print("2. Fix config.py syntax errors")
        print("3. Install missing packages: pip install -r requirements.txt")
    print("=" * 60)


if __name__ == "__main__":
    main()