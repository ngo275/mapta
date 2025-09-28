#!/usr/bin/env python3
print('Testing MAPTA imports...')

try:
    from function_tool import function_tool
    print('✓ function_tool import successful')
except ImportError as e:
    print(f'✗ function_tool import failed: {e}')

try:
    import main
    print('✓ main.py import successful')
except ImportError as e:
    print(f'✗ main.py import failed: {e}')
except Exception as e:
    print(f'✗ main.py import error: {e}')

print('Import test completed.')
