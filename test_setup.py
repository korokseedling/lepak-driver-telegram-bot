#!/usr/bin/env python3
"""
Test script to verify Claptrap Chore Bot setup
Run this before starting the bot to check all components
"""

import os
import sys
import json
from dotenv import load_dotenv

def test_environment_variables():
    """Test if all required environment variables are set"""
    print("🔧 Testing environment variables...")

    load_dotenv()

    required_vars = ['TELEGRAM_TOKEN', 'OPENROUTER_API_KEY']
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * (len(value) - 8) + value[-8:] if len(value) > 8 else '*' * len(value)}")

    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False

    print("✅ All environment variables found")
    return True

def test_config_files():
    """Test if all required configuration files exist"""
    print("\n📁 Testing configuration files...")

    required_files = [
        'model_config.json',
        'system_prompt.md',
        'requirements.txt'
    ]

    missing_files = []

    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}")
        else:
            missing_files.append(file)
            print(f"❌ {file}")

    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False

    print("✅ All configuration files found")
    return True

def test_config_json():
    """Test if model_config.json is valid"""
    print("\n⚙️ Testing model configuration...")

    try:
        with open('model_config.json', 'r') as f:
            config = json.load(f)

        # Check required sections
        required_sections = ['model_settings', 'tools']
        for section in required_sections:
            if section in config:
                print(f"✅ {section} section found")
            else:
                print(f"❌ {section} section missing")
                return False

        # Check tool count
        tools = config.get('tools', [])
        print(f"✅ {len(tools)} tool functions configured")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in model_config.json: {e}")
        return False
    except FileNotFoundError:
        print("❌ model_config.json not found")
        return False

def test_imports():
    """Test if all required Python packages can be imported"""
    print("\n📦 Testing Python imports...")

    required_packages = [
        ('telegram', 'python-telegram-bot'),
        ('openai', 'openai'),
        ('dotenv', 'python-dotenv')
    ]

    missing_packages = []

    for package, pip_name in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(pip_name)
            print(f"❌ {package} (install with: pip install {pip_name})")

    if missing_packages:
        print(f"❌ Missing packages. Install with: pip install {' '.join(missing_packages)}")
        return False

    print("✅ All required packages available")
    return True

def test_chore_modules():
    """Test if chore tracking modules can be imported and used"""
    print("\n🧹 Testing chore tracking modules...")

    try:
        import chore_manager
        import chore_functions
        print("✅ chore_manager and chore_functions imported")

        expected_functions = {'add_chore', 'list_outstanding_chores', 'complete_chore', 'update_chore'}
        registered = set(chore_functions.TOOL_FUNCTIONS.keys())
        if registered != expected_functions:
            print(f"❌ TOOL_FUNCTIONS mismatch. Expected {expected_functions}, got {registered}")
            return False
        print(f"✅ {len(registered)} chore tool functions registered")

        return True

    except ImportError as e:
        print(f"❌ Cannot import chore modules: {e}")
        return False
    except Exception as e:
        print(f"❌ Error initializing chore modules: {e}")
        return False

def main():
    """Run all tests"""
    print("🤖 Claptrap Chore Bot Setup Test")
    print("=" * 40)

    tests = [
        test_environment_variables,
        test_config_files,
        test_config_json,
        test_imports,
        test_chore_modules
    ]

    results = []
    for test in tests:
        result = test()
        results.append(result)

    print("\n" + "=" * 40)
    print("📋 Test Summary")
    print("=" * 40)

    passed = sum(results)
    total = len(results)

    if passed == total:
        print(f"✅ All {total} tests passed! Bot is ready to run.")
        print("\n🚀 Start the bot with: python bot.py")
        return 0
    else:
        print(f"❌ {total - passed} out of {total} tests failed.")
        print("\n🔧 Fix the issues above before running the bot.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
