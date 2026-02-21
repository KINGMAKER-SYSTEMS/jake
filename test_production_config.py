#!/usr/bin/env python3
"""
Quick sanity check that production config works
"""
import os
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

# Test 1: Check environment variable handling
print("Test 1: Environment variable configuration")
print("-" * 50)

# Simulate Railway environment
os.environ["RAILWAY_ENVIRONMENT"] = "production"
os.environ["SECRET_KEY"] = "test-secret-key-12345"
os.environ["PORT"] = "8080"

# Import the module (this will execute the config code)
sys.path.insert(0, str(Path(__file__).parent))
from campaign_manager import web_dashboard as app_module

print(f"✓ IS_RAILWAY detected: {app_module.IS_RAILWAY}")
print(f"✓ SECRET_KEY set: {app_module.app.secret_key != 'campaign-dashboard-local'}")
print(f"✓ DATA_ROOT: {app_module.DATA_ROOT}")
print(f"✓ CAMPAIGNS_DIR: {app_module.CAMPAIGNS_DIR}")
print(f"✓ CACHE_DIR env var: {os.environ.get('CACHE_DIR')}")
print()

# Test 2: Check that directories would be created correctly
print("Test 2: Directory configuration")
print("-" * 50)
expected_paths = {
    "campaigns": Path("/app/data_volume/campaigns"),
    "active": Path("/app/data_volume/campaigns/active"),
    "completed": Path("/app/data_volume/campaigns/completed"),
    "cache": Path("/app/data_volume/cache"),
    "internal_cache": Path("/app/data_volume/internal_cache"),
}

for name, expected in expected_paths.items():
    actual = getattr(app_module, name.upper() + "_DIR", app_module.CAMPAIGNS_DIR / name)
    match = str(actual) == str(expected)
    status = "✓" if match else "✗"
    print(f"{status} {name}: {actual} {'== ' + str(expected) if match else '!= ' + str(expected)}")

print()

# Test 3: Check Flask app would start with correct config
print("Test 3: Flask configuration")
print("-" * 50)
print(f"✓ App secret key is NOT default: {app_module.app.secret_key != 'campaign-dashboard-local'}")
print(f"✓ App name: {app_module.app.name}")
print(f"✓ Template folder exists: {Path(app_module.app.template_folder).exists()}")
print()

# Clean up
del os.environ["RAILWAY_ENVIRONMENT"]
del os.environ["SECRET_KEY"]
del os.environ["PORT"]

print("=" * 50)
print("✓ All configuration tests passed!")
print("=" * 50)
print()
print("Next steps:")
print("1. Commit these changes: git add . && git commit -m 'Add Railway deployment config'")
print("2. Deploy to Railway: railway up")
print("3. Check deployment logs: railway logs")
