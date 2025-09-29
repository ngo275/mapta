# E2B Sandbox Setup for MAPTA

This guide explains how to configure E2B sandboxes for MAPTA to enable network access for external target testing.

## Prerequisites

1. **E2B Account**: Sign up at [e2b.dev](https://e2b.dev)
2. **API Key**: Get your API key from the E2B dashboard
3. **Python Dependencies**: Install via `pip install -r requirements.txt`

## Configuration Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install the E2B Python SDK (>=0.15.0) along with other required packages.

### 2. Set Environment Variables

Set the following environment variables:

```bash
# Required: E2B API key from your dashboard
export E2B_API_KEY="your_api_key_here"

# Required: Configure MAPTA to use E2B sandbox factory
export SANDBOX_FACTORY="e2b_sandbox_factory:create_e2b_sandbox"

# Optional: Specify E2B template (defaults to 'base')
export E2B_TEMPLATE="base"
```

### 3. Verify Setup

Test the configuration by running:

```bash
python e2b_sandbox_factory.py
```

This will:
- Create an E2B sandbox instance
- Test network connectivity to httpbin.org
- Test connectivity to vibehub.co
- Clean up the sandbox

Expected output:
```
Testing E2B sandbox factory...
✓ Sandbox created successfully
✓ Network connectivity working
✓ Can reach vibehub.co
✓ Sandbox terminated
```

## Usage

Once configured, MAPTA will automatically use E2B sandboxes for security testing:

```bash
# Run MAPTA against external targets
python main.py
```

The system will now be able to analyze external targets like vibehub.co without "Limited analysis due to network restrictions" errors.

## Troubleshooting

### Common Issues

1. **"E2B package not available"**
   - Solution: Run `pip install e2b>=0.15.0`

2. **"E2B_API_KEY environment variable not set"**
   - Solution: Set your API key: `export E2B_API_KEY="your_key"`

3. **"Failed to create E2B sandbox"**
   - Check your API key is valid
   - Verify you have E2B credits/quota available
   - Check network connectivity to E2B services

4. **"Network connectivity test failed"**
   - Verify the E2B template supports outbound connections
   - Check if target URLs are accessible from E2B infrastructure
   - Consider firewall or proxy issues

### Template Configuration

The default 'base' template should work for most use cases. If you need custom tools or configurations:

1. Create a custom template in the E2B dashboard
2. Set `E2B_TEMPLATE` environment variable to your template name
3. Ensure the template includes necessary security testing tools

### Debugging

Enable detailed logging by setting:

```bash
export PYTHONPATH=.
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from e2b_sandbox_factory import create_e2b_sandbox
sandbox = create_e2b_sandbox()
"
```

## Security Considerations

- Keep your E2B API key secure and never commit it to version control
- Use environment variables or secure secret management
- E2B sandboxes are isolated environments, but follow responsible disclosure practices
- Only test targets you have explicit authorization to test

## Integration Details

The E2B sandbox factory implements the interface expected by MAPTA:

- `sandbox.files.write(path, content)` - Write files to sandbox
- `sandbox.commands.run(cmd, timeout=..., user=...)` - Execute commands
- `sandbox.set_timeout(ms)` - Configure timeout preferences
- `sandbox.kill()` - Terminate sandbox instance

This maintains compatibility with MAPTA's existing architecture while enabling external network access through E2B's cloud infrastructure.
