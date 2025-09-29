# Local Sandbox Setup for MAPTA

This guide explains how to configure local sandboxes for MAPTA to enable network access for external target testing when running on Devin's machine.

## Overview

Since MAPTA runs on Devin's machine, we can use the local environment directly without needing cloud-based sandboxes. This approach is simpler, faster, and doesn't require external API keys.

## Configuration Steps

### 1. Set Environment Variable

Set the following environment variable to use the local sandbox factory:

```bash
export SANDBOX_FACTORY="local_sandbox_factory:create_local_sandbox"
```

### 2. Verify Setup

Test the configuration by running:

```bash
python local_sandbox_factory.py
```

This will:
- Create a local sandbox instance
- Test network connectivity to httpbin.org
- Test connectivity to vibehub.co
- Clean up the sandbox

Expected output:
```
Testing local sandbox factory...
✓ Sandbox created successfully
✓ Network connectivity working
✓ Can reach vibehub.co
✓ Sandbox terminated
```

### 3. Test with MAPTA

Run the test script to verify complete integration:

```bash
python test_local_setup.py
```

## Usage

Once configured, MAPTA will automatically use local sandboxes for security testing:

```bash
# Run MAPTA against external targets
python main.py
```

The system will now be able to analyze external targets like vibehub.co without "Limited analysis due to network restrictions" errors.

## How It Works

The local sandbox factory creates isolated working directories for each scan and executes commands using the local system's capabilities:

- **File Operations**: Files are written to temporary directories
- **Command Execution**: Commands run via subprocess with proper isolation
- **Network Access**: Full network access through the host system
- **Cleanup**: Temporary directories are cleaned up after use

## Advantages

1. **No External Dependencies**: No need for cloud services or API keys
2. **Full Network Access**: Direct access to all external targets
3. **Fast Execution**: No network latency for sandbox creation
4. **Simple Setup**: Just one environment variable needed
5. **Cost Effective**: No usage fees or quotas

## Security Considerations

- Commands run in isolated temporary directories
- Each scan gets its own working directory
- Temporary files are cleaned up after use
- Network access is the same as the host system

## Troubleshooting

### Common Issues

1. **"Failed to create local sandbox"**
   - Check that the system has write permissions for temporary directories
   - Verify that subprocess execution is allowed

2. **"Network connectivity test failed"**
   - Check internet connectivity on the host system
   - Verify that curl is installed and available
   - Check for firewall restrictions

3. **"SANDBOX_FACTORY not set correctly"**
   - Ensure the environment variable is set: `export SANDBOX_FACTORY="local_sandbox_factory:create_local_sandbox"`
   - Verify the local_sandbox_factory.py file is in the current directory

### Debugging

Enable detailed logging by setting:

```bash
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from local_sandbox_factory import create_local_sandbox
sandbox = create_local_sandbox()
"
```

## Integration Details

The local sandbox factory implements the same interface expected by MAPTA:

- `sandbox.files.write(path, content)` - Write files to sandbox working directory
- `sandbox.commands.run(cmd, timeout=..., user=...)` - Execute commands via subprocess
- `sandbox.set_timeout(ms)` - Configure default timeout for commands
- `sandbox.kill()` - Clean up temporary directories

This maintains full compatibility with MAPTA's existing architecture while providing direct local system access for network testing.
