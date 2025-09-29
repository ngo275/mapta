#!/usr/bin/env python3
"""
Local Sandbox Factory for MAPTA

This module provides a factory function to create local sandbox instances
that implement the interface expected by MAPTA's sandbox system.

Since MAPTA runs on Devin's machine, we can use the local environment
directly without needing cloud-based sandboxes like E2B.

Usage:
    Set environment variable: SANDBOX_FACTORY="local_sandbox_factory:create_local_sandbox"
"""

import os
import subprocess
import tempfile
import logging
from typing import Optional, Union
from pathlib import Path


class LocalSandboxWrapper:
    """
    Local sandbox implementation that adapts local system to MAPTA's expected interface.
    
    MAPTA expects sandbox objects with:
    - .files.write(path, content) method
    - .commands.run(cmd, timeout=..., user=...) method  
    - .set_timeout(ms) method (optional)
    - .kill() method (optional)
    """
    
    def __init__(self, work_dir: str = None):
        """Initialize local sandbox with a working directory."""
        if work_dir is None:
            self.work_dir = tempfile.mkdtemp(prefix="mapta_sandbox_")
        else:
            self.work_dir = work_dir
            os.makedirs(work_dir, exist_ok=True)
        
        self.files = LocalFiles(self.work_dir)
        self.commands = LocalCommands(self.work_dir)
        self._default_timeout = 30
        
        logging.info(f"Local sandbox initialized with work_dir: {self.work_dir}")
    
    def set_timeout(self, timeout: int):
        """Set default timeout for commands (in milliseconds)."""
        self._default_timeout = timeout / 1000  # Convert to seconds
        self.commands.default_timeout = self._default_timeout
        logging.info(f"Sandbox timeout set to {timeout}ms ({self._default_timeout}s)")
    
    def kill(self):
        """Clean up the sandbox (remove temporary files)."""
        try:
            import shutil
            if os.path.exists(self.work_dir) and "mapta_sandbox_" in self.work_dir:
                shutil.rmtree(self.work_dir)
                logging.info(f"Local sandbox cleaned up: {self.work_dir}")
        except Exception as e:
            logging.warning(f"Error cleaning up sandbox: {e}")


class LocalFiles:
    """File operations for the local sandbox."""
    
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
    
    def write(self, path: str, content: str):
        """Write content to a file in the sandbox."""
        full_path = os.path.join(self.work_dir, path.lstrip('/'))
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        
        with open(full_path, 'w') as f:
            f.write(content)
        
        logging.debug(f"Wrote file: {full_path}")


class CommandResult:
    """Result of a command execution."""
    
    def __init__(self, exit_code: int, stdout: str, stderr: str):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


class LocalCommands:
    """Command execution for the local sandbox."""
    
    def __init__(self, work_dir: str):
        self.work_dir = work_dir
        self.default_timeout = 30
    
    def run(self, cmd: str, timeout: Optional[int] = None, user: Optional[str] = None) -> CommandResult:
        """Execute a command in the sandbox."""
        if timeout is None:
            timeout = self.default_timeout
        
        try:
            logging.info(f"Executing command: {cmd}")
            
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            logging.debug(f"Command exit code: {result.returncode}")
            if result.stdout:
                logging.debug(f"Command stdout: {result.stdout[:200]}...")
            if result.stderr:
                logging.debug(f"Command stderr: {result.stderr[:200]}...")
            
            return CommandResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr
            )
            
        except subprocess.TimeoutExpired:
            logging.error(f"Command timed out after {timeout}s: {cmd}")
            return CommandResult(
                exit_code=124,  # Standard timeout exit code
                stdout="",
                stderr=f"Command timed out after {timeout}s"
            )
        except Exception as e:
            logging.error(f"Command execution error: {e}")
            return CommandResult(
                exit_code=1,
                stdout="",
                stderr=str(e)
            )


def create_local_sandbox() -> Optional[LocalSandboxWrapper]:
    """
    Factory function to create a local sandbox instance.
    
    This function is called by MAPTA's create_sandbox_from_env() when
    SANDBOX_FACTORY is set to "local_sandbox_factory:create_local_sandbox".
    
    Returns:
        LocalSandboxWrapper: Local sandbox instance, or None if creation fails
    """
    try:
        logging.info("Creating local sandbox")
        sandbox = LocalSandboxWrapper()
        
        result = sandbox.commands.run("echo 'Local sandbox initialized'", timeout=10)
        if result.exit_code == 0:
            logging.info("Local sandbox created successfully")
            return sandbox
        else:
            logging.error(f"Local sandbox test failed: {result.stderr}")
            return None
            
    except Exception as e:
        logging.error(f"Failed to create local sandbox: {e}")
        return None


def test_network_connectivity(sandbox_wrapper: LocalSandboxWrapper, target_url: str = "https://httpbin.org/get") -> bool:
    """
    Test network connectivity from the sandbox to external targets.
    
    Args:
        sandbox_wrapper: Local sandbox wrapper instance
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
    
    print("Testing local sandbox factory...")
    sandbox = create_local_sandbox()
    
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
