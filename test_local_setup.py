#!/usr/bin/env python3
"""
Test script to verify local sandbox setup and network connectivity.

This script tests the complete local sandbox integration to ensure MAPTA can
access external targets without network restrictions.
"""

import os
import sys
import logging

sys.path.append('.')

from main import create_sandbox_from_env
from local_sandbox_factory import test_network_connectivity

def test_sandbox_creation():
    """Test that sandbox can be created successfully."""
    print("Testing sandbox creation...")
    
    sandbox = create_sandbox_from_env()
    if sandbox is None:
        print("✗ Failed to create sandbox")
        print("Check that SANDBOX_FACTORY is set correctly")
        return False
    
    print("✓ Sandbox created successfully")
    return sandbox

def test_basic_commands(sandbox):
    """Test basic command execution in sandbox."""
    print("Testing basic command execution...")
    
    try:
        result = sandbox.commands.run("echo 'Hello from local sandbox'", timeout=10)
        if result.exit_code == 0:
            print("✓ Basic command execution working")
            return True
        else:
            print(f"✗ Command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Command execution error: {e}")
        return False

def test_network_access(sandbox):
    """Test network access to external targets."""
    print("Testing network access...")
    
    if not test_network_connectivity(sandbox, "https://httpbin.org/get"):
        print("✗ Basic network connectivity failed")
        return False
    
    print("✓ Basic network connectivity working")
    
    if not test_network_connectivity(sandbox, "https://vibehub.co"):
        print("✗ Cannot reach vibehub.co")
        return False
    
    print("✓ Can reach vibehub.co")
    return True

def test_mapta_integration():
    """Test MAPTA's sandbox integration."""
    print("Testing MAPTA integration...")
    
    sandbox_factory = os.getenv("SANDBOX_FACTORY")
    if sandbox_factory != "local_sandbox_factory:create_local_sandbox":
        print(f"✗ SANDBOX_FACTORY not set correctly: {sandbox_factory}")
        print("Expected: local_sandbox_factory:create_local_sandbox")
        return False
    
    print("✓ SANDBOX_FACTORY configured correctly")
    return True

def main():
    """Run all tests to verify local sandbox setup."""
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("MAPTA Local Sandbox Setup Verification")
    print("=" * 50)
    
    if not test_mapta_integration():
        print("\n❌ Environment configuration failed")
        print("Please check LOCAL_SETUP.md for configuration instructions")
        return False
    
    sandbox = test_sandbox_creation()
    if not sandbox:
        print("\n❌ Sandbox creation failed")
        return False
    
    try:
        if not test_basic_commands(sandbox):
            print("\n❌ Basic command execution failed")
            return False
        
        if not test_network_access(sandbox):
            print("\n❌ Network access failed")
            return False
        
        print("\n" + "=" * 50)
        print("✅ All tests passed!")
        print("MAPTA is now configured for external target testing")
        print("Network restrictions should be resolved")
        print("=" * 50)
        
        return True
        
    finally:
        if hasattr(sandbox, 'kill'):
            sandbox.kill()
            print("✓ Sandbox cleaned up")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
