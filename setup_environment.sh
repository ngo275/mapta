#!/bin/bash

echo "Setting up MAPTA environment..."

if [ ! -f ".env" ]; then
    echo "Creating .env file..."
    cp .env.example .env 2>/dev/null || {
        echo "# MAPTA Environment Configuration" > .env
        echo "OPENAI_API_KEY=\${OPENAI_API_KEY}" >> .env
        echo "SANDBOX_FACTORY=local_sandbox_factory:create_local_sandbox" >> .env
    }
fi

if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

if [ "$SANDBOX_FACTORY" = "local_sandbox_factory:create_local_sandbox" ]; then
    echo "✓ SANDBOX_FACTORY configured correctly"
else
    echo "Setting SANDBOX_FACTORY for local sandbox..."
    export SANDBOX_FACTORY="local_sandbox_factory:create_local_sandbox"
fi

echo "Testing local sandbox configuration..."
python test_local_setup.py

if [ $? -eq 0 ]; then
    echo "✅ MAPTA environment setup complete!"
    echo "Network egress restrictions have been resolved."
    echo "You can now run: python main.py"
else
    echo "❌ Setup failed. Please check the configuration."
    exit 1
fi
