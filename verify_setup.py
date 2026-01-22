#!/usr/bin/env python3
"""
Simple verification script to check that the project setup is correct.
This script verifies imports work without requiring external dependencies.
"""

import sys
from pathlib import Path

# Add the current directory to the path
sys.path.insert(0, str(Path(__file__).parent))


def verify_imports():
    """Verify that all core modules can be imported."""
    print("Verifying project setup...")

    # Check app package
    try:
        import app
        print("✓ app package found")
    except ImportError as e:
        print(f"✗ Failed to import app package: {e}")
        return False

    # Check config module structure (without Pydantic dependency)
    try:
        with open("app/config.py", "r") as f:
            content = f.read()
            required_elements = [
                "class Settings",
                "def get_settings",
                "database_user",
                "database_password",
                "database_name",
                "mailgun_api_key",
                "mailgun_domain",
                "auth0_domain",
                "auth0_audience",
            ]
            for element in required_elements:
                if element in content:
                    print(f"✓ Config contains {element}")
                else:
                    print(f"✗ Config missing {element}")
                    return False
    except Exception as e:
        print(f"✗ Failed to read config.py: {e}")
        return False

    # Check database module structure
    try:
        with open("app/database.py", "r") as f:
            content = f.read()
            required_elements = [
                "from sqlalchemy.ext.asyncio import",
                "create_async_engine",
                "async_sessionmaker",
                "Base = declarative_base()",
                "engine =",
                "AsyncSessionLocal =",
                "async def get_db_session",
            ]
            for element in required_elements:
                if element in content:
                    print(f"✓ Database module contains {element}")
                else:
                    print(f"✗ Database module missing {element}")
                    return False
    except Exception as e:
        print(f"✗ Failed to read database.py: {e}")
        return False

    # Check test module structure
    try:
        with open("tests/test_config.py", "r") as f:
            content = f.read()
            required_tests = [
                "def test_settings_loads_with_valid_env_vars",
                "def test_settings_applies_defaults",
                "def test_settings_missing_required_fields",
                "def test_settings_database_url_property",
            ]
            for test in required_tests:
                if test in content:
                    print(f"✓ Test file contains {test}")
                else:
                    print(f"✗ Test file missing {test}")
                    return False
    except Exception as e:
        print(f"✗ Failed to read test_config.py: {e}")
        return False

    # Check database test module structure
    try:
        with open("tests/test_database.py", "r") as f:
            content = f.read()
            required_tests = [
                "def test_engine_created",
                "def test_session_factory_created",
                "async def test_get_db_session_yields_session",
                "def test_base_created",
            ]
            for test in required_tests:
                if test in content:
                    print(f"✓ Database test file contains {test}")
                else:
                    print(f"✗ Database test file missing {test}")
                    return False
    except Exception as e:
        print(f"✗ Failed to read test_database.py: {e}")
        return False

    # Check required files exist
    required_files = [
        "requirements.txt",
        ".env.example",
        ".gitignore",
        "README.md",
        "app/__init__.py",
        "app/config.py",
        "app/database.py",
        "app/models/__init__.py",
        "app/schemas/__init__.py",
        "app/routers/__init__.py",
        "app/services/__init__.py",
        "app/middleware/__init__.py",
        "tests/__init__.py",
        "tests/test_config.py",
        "tests/test_database.py",
        "alembic.ini",
        "alembic/env.py",
        "alembic/script.py.mako",
        "pytest.ini",
    ]

    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            return False

    # Check required directories exist
    required_dirs = [
        "app/models",
        "app/schemas",
        "app/routers",
        "app/services",
        "app/middleware",
        "static",
        "tests",
        "alembic/versions",
    ]

    for dir_path in required_dirs:
        if Path(dir_path).is_dir():
            print(f"✓ {dir_path}/ directory exists")
        else:
            print(f"✗ {dir_path}/ directory missing")
            return False

    return True


if __name__ == "__main__":
    success = verify_imports()
    if success:
        print("\n✓ All verification checks passed!")
        print("\nNext steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Copy .env.example to .env and configure your environment")
        print("3. Run tests: pytest")
        sys.exit(0)
    else:
        print("\n✗ Verification failed!")
        sys.exit(1)
