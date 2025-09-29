#!/usr/bin/env python3
"""
Test script to verify network connectivity to idea.aha.studio specifically.
"""

import logging
from local_sandbox_factory import create_local_sandbox, test_network_connectivity

def main():
    logging.basicConfig(level=logging.INFO)
    
    print("Testing network connectivity to idea.aha.studio...")
    
    sandbox = create_local_sandbox()
    if sandbox:
        result = test_network_connectivity(sandbox, 'https://idea.aha.studio')
        print(f'✓ Can reach idea.aha.studio: {result}')
        sandbox.kill()
        return result
    else:
        print('✗ Failed to create sandbox')
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
