# MAPTA - AI-Powered Penetration Testing Tool

MAPTA is an AI-powered penetration testing tool that automates security vulnerability assessment and CTF challenge solving.

## Quick Setup

### 1. Environment Configuration

Run the setup script to configure MAPTA for local execution with full network access:

```bash
./setup_environment.sh
```

This will:
- Create a `.env` file with proper configuration
- Set `SANDBOX_FACTORY` to use local sandboxes (no E2B required)
- Test network connectivity to ensure egress works
- Verify the complete setup

### 2. Manual Setup (Alternative)

If you prefer manual configuration:

```bash
# Set environment variables
export SANDBOX_FACTORY="local_sandbox_factory:create_local_sandbox"
export OPENAI_API_KEY="your_openai_api_key"

# Test the configuration
python test_local_setup.py
```

### 3. Run MAPTA

```bash
python main.py
```

## Network Access

MAPTA is configured to use local sandboxes that provide full network access for security testing. This resolves any "Limited analysis due to network restrictions" errors and enables testing of external targets like `https://idea.aha.studio/`.

## Requirements

- Python 3.12+
- OpenAI API key
- Network connectivity for target testing

## Files

- `.env` - Environment configuration
- `setup_environment.sh` - Automated setup script
- `local_sandbox_factory.py` - Local sandbox implementation
- `test_local_setup.py` - Configuration verification
- `LOCAL_SETUP.md` - Detailed setup documentation

## Troubleshooting

If you encounter network issues:

1. Verify SANDBOX_FACTORY is set: `echo $SANDBOX_FACTORY`
2. Run the test script: `python test_local_setup.py`
3. Check the setup script: `./setup_environment.sh`

For detailed troubleshooting, see `LOCAL_SETUP.md`.
