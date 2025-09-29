#!/usr/bin/env python3
"""
E2B Sandbox Factory for MAPTA

This module provides a factory function to create E2B sandbox instances
that implement the interface expected by MAPTA's sandbox system.

Usage:
    Set environment variable: SANDBOX_FACTORY="e2b_sandbox_factory:create_e2b_sandbox"
    Set E2B API key: E2B_API_KEY="your_api_key_here"
"""

import os
import logging
from typing import Optional

try:
    from e2b import Sandbox
except ImportError:
    Sandbox = None
    logging.warning("E2B package not installed. Run: pip install e2b")


class E2BSandboxWrapper:
    """
    Wrapper class to adapt E2B Sandbox to MAPTA's expected interface.
    
    MAPTA expects sandbox objects with:
    - .files.write(path, content) method
    - .commands.run(cmd, timeout=..., user=...) method  
    - .set_timeout(ms) method (optional)
    - .kill() method (optional)
    """
    
    def __init__(self, sandbox):
        self._sandbox = sandbox
        self.files = self._sandbox.files
        self.commands = self._sandbox.commands
    
    def set_timeout(self, timeout: int):
        """Set timeout for the sandbox (E2B handles this internally)"""
        self._default_timeout = timeout
        logging.info(f"Sandbox timeout preference set to {timeout}ms")
    
    def kill(self):
        """Terminate the sandbox instance"""
        try:
            self._sandbox.close()
            logging.info("E2B sandbox terminated successfully")
        except Exception as e:
            logging.warning(f"Error terminating E2B sandbox: {e}")


def create_e2b_sandbox() -> Optional[E2BSandboxWrapper]:
    """
    Factory function to create an E2B sandbox instance.
    
    This function is called by MAPTA's create_sandbox_from_env() when
    SANDBOX_FACTORY is set to "e2b_sandbox_factory:create_e2b_sandbox".
    
    Returns:
        E2BSandboxWrapper: Wrapped E2B sandbox instance, or None if creation fails
    """
    if Sandbox is None:
        logging.error("E2B package not available. Install with: pip install e2b")
        return None
    
    api_key = os.getenv("E2B_API_KEY")
    if not api_key:
        logging.error("E2B_API_KEY environment variable not set")
        return None
    
    template = os.getenv("E2B_TEMPLATE", "base")
    
    try:
        logging.info(f"Creating E2B sandbox with template: {template}")
        sandbox = Sandbox.create(template=template, api_key=api_key)
        
        result = sandbox.commands.run("echo 'E2B sandbox initialized'", timeout=10)
        if result.exit_code == 0:
            logging.info("E2B sandbox created successfully")
            return E2BSandboxWrapper(sandbox)
        else:
            logging.error(f"E2B sandbox test failed: {result.stderr}")
            sandbox.close()
            return None
            
    except Exception as e:
        logging.error(f"Failed to create E2B sandbox: {e}")
        return None


def test_network_connectivity(sandbox_wrapper: E2BSandboxWrapper, target_url: str = "https://httpbin.org/get") -> bool:
    """
    Test network connectivity from the sandbox to external targets.
    
    Args:
        sandbox_wrapper: E2B sandbox wrapper instance
        target_url: URL to test connectivity against
        
    Returns:
        bool: True if network connectivity works, False otherwise
    """
    try:
        logging.info(f"Testing network connectivity to {target_url}")
        result = sandbox_wrapper.commands.run(f"curl -s --max-time 10 {target_url}", timeout=15)
        
        if result.exit_code == 0:
            logging.info("Network connectivity test successful")
            return True
        else:
            logging.warning(f"Network connectivity test failed: {result.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"Network connectivity test error: {e}")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("Testing E2B sandbox factory...")
    sandbox = create_e2b_sandbox()
    
    if sandbox:
        print("✓ Sandbox created successfully")
        
        if test_network_connectivity(sandbox, "https://httpbin.org/get"):
            print("✓ Network connectivity working")
        else:
            print("✗ Network connectivity failed")
            
        if test_network_connectivity(sandbox, "https://vibehub.co"):
            print("✓ Can reach vibehub.co")
        else:
            print("✗ Cannot reach vibehub.co")
            
        sandbox.kill()
        print("✓ Sandbox terminated")
    else:
        print("✗ Failed to create sandbox")
        print("Make sure E2B_API_KEY is set and e2b package is installed")
