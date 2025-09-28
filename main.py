import os
import json
import asyncio
from typing import Any, Dict, Optional, List
from openai import AsyncOpenAI
from datetime import datetime, timezone
import threading
import logging
import importlib

from function_tool import function_tool
import json as json_module
import httpx
import aiohttp
# from core.config import SLACK_WEBHOOK_URL, SLACK_CHANNEL

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "#security-alerts")


# --- Setup ---
client = AsyncOpenAI()


# Global sandbox configuration (sanitized for open release)
# Provide a factory via env var SANDBOX_FACTORY="your_module:create_sandbox" that returns a sandbox instance
SANDBOX_FACTORY = os.getenv("SANDBOX_FACTORY")

# Thread-local storage for sandbox instances
_thread_local = threading.local()

def get_current_sandbox():
    """Get the sandbox instance for the current thread/scan."""
    return getattr(_thread_local, 'sandbox', None)

def set_current_sandbox(sandbox):
    """Set the sandbox instance for the current thread/scan."""
    _thread_local.sandbox = sandbox

def create_sandbox_from_env():
    """Create a sandbox instance using a user-provided factory specified in SANDBOX_FACTORY.

    SANDBOX_FACTORY should be in the form "module_path:function_name" and must return an
    object exposing .files.write(path, content), .commands.run(cmd, timeout=..., user=...),
    and optional .set_timeout(ms) and .kill().

    Returns None if not configured.
    """
    factory_path = SANDBOX_FACTORY
    if not factory_path:
        logging.info("Sandbox factory not configured; running without a sandbox.")
        return None
    try:
        module_name, func_name = factory_path.rsplit(":", 1)
        module = importlib.import_module(module_name)
        factory = getattr(module, func_name)
        sandbox = factory()
        # Optionally extend timeout if provider supports it
        if hasattr(sandbox, "set_timeout"):
            try:
                sandbox.set_timeout(timeout=12000)
            except TypeError:
                # Some providers may use milliseconds
                sandbox.set_timeout(12000)
        return sandbox
    except Exception as exc:
        logging.warning(f"Failed to create sandbox from SANDBOX_FACTORY: {exc}")
        return None

# Usage tracking
class UsageTracker:
    def __init__(self):
        self.main_agent_usage = []
        self.sandbox_agent_usage = []
        self.start_time = datetime.now(timezone.utc)
    
    def log_main_agent_usage(self, usage_data, target_url=""):
        """Log usage data from main agent responses."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_url": target_url,
            "agent_type": "main_agent",
            "usage": usage_data
        }
        self.main_agent_usage.append(entry)
        logging.info(f"Main Agent Usage - Target: {target_url}, Usage: {usage_data}")
    
    def log_sandbox_agent_usage(self, usage_data, target_url=""):
        """Log usage data from sandbox agent responses."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target_url": target_url,
            "agent_type": "sandbox_agent", 
            "usage": usage_data
        }
        self.sandbox_agent_usage.append(entry)
        logging.info(f"Sandbox Agent Usage - Target: {target_url}, Usage: {usage_data}")
    
    def get_summary(self):
        """Get usage summary for all agents."""
        return {
            "scan_duration": str(datetime.now(timezone.utc) - self.start_time),
            "main_agent_calls": len(self.main_agent_usage),
            "sandbox_agent_calls": len(self.sandbox_agent_usage),
            "total_calls": len(self.main_agent_usage) + len(self.sandbox_agent_usage),
            "main_agent_usage": self.main_agent_usage,
            "sandbox_agent_usage": self.sandbox_agent_usage
        }
    
    def save_to_file(self, filename_prefix=""):
        """Save usage data to JSON file."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}usage_log_{timestamp}.json"
        
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(self.get_summary(), f, indent=2, default=str)
        
        logging.info(f"Usage data saved to {filename}")
        return filename

# Thread-local storage for usage trackers
def get_current_usage_tracker():
    """Get the usage tracker for the current thread/scan."""
    return getattr(_thread_local, 'usage_tracker', None)

def set_current_usage_tracker(tracker):
    """Set the usage tracker for the current thread/scan."""
    _thread_local.usage_tracker = tracker


# Create tasks for parallel execution
async def execute_function_call(function_call):
    function_call_arguments = json.loads(function_call.arguments)

    # Execute the function logic
    result = await execute_tool(function_call.name, function_call_arguments)

    return {
        "type": "function_call_output",
        "call_id": function_call.call_id,
        "output": result,
    }



# In-memory store: email -> JWT token (for mail.tm API)
email_token_store = {}



@function_tool
async def get_registered_emails():
    """
    Return the list of email accounts in case you need to use them to receive emails such as account activation emails, credentials, etc.
    """
    return json_module.dumps(list(email_token_store.keys()))



@function_tool
async def list_account_messages(email: str, limit: int = 50):
    """
    List recent messages for the given email account.
    Returns JSON list: [{id, subject, from, intro, seen, createdAt}]
    
    Args:
        email: The email account to fetch messages for
        limit: Maximum number of messages to return (default: 50)
    """
    jwt = email_token_store.get(email)
    if not jwt:
        return f"No JWT token stored for {email}. Call set_email_jwt_token(email, jwt_token) first."

    headers = {"Authorization": f"Bearer {jwt}"}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get("https://api.mail.tm/messages", headers=headers)
            if resp.status_code != 200:
                return f"Failed to fetch messages. Status: {resp.status_code}, Response: {resp.text}"
            data = resp.json()
            messages = data.get("hydra:member", [])
            items = []
            for m in messages[:limit]:
                sender = m.get("from") or {}
                items.append(
                    {
                        "id": m.get("id"),
                        "subject": m.get("subject"),
                        "from": sender.get("address") or sender.get("name") or "",
                        "intro": m.get("intro", ""),
                        "seen": m.get("seen", False),
                        "createdAt": m.get("createdAt", ""),
                    }
                )
            return json_module.dumps(items)
    except Exception as e:
        return f"Request failed: {e}"



@function_tool
async def get_message_by_id(email: str, message_id: str):
    """
    Fetch a specific message by id for the given email account using its stored JWT.
    Returns JSON: {id, subject, from, text, html}
    
    Args:
        email: The email account to fetch the message from
        message_id: The ID of the message to fetch
    """
    jwt = email_token_store.get(email)
    if not jwt:
        return f"No JWT token stored for {email}. Call set_email_jwt_token(email, jwt_token) first."

    headers = {"Authorization": f"Bearer {jwt}"}
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"https://api.mail.tm/messages/{message_id}", headers=headers
            )
            if resp.status_code != 200:
                return f"Failed to fetch message. Status: {resp.status_code}, Response: {resp.text}"
            msg = resp.json()
            sender = msg.get("from") or {}
            result = {
                "id": msg.get("id"),
                "subject": msg.get("subject"),
                "from": sender.get("address") or sender.get("name") or "",
                "text": msg.get("text", ""),
                "html": msg.get("html", ""),
            }
            return json_module.dumps(result)
    except Exception as e:
        return f"Request failed: {e}"


@function_tool(name_override="send_slack_alert")
async def send_slack_security_alert(
    vulnerability_type: str,
    severity: str,
    target_url: str,
    description: str,
    evidence: Optional[str] = None,
    recommendation: Optional[str] = None,
    thread_ts: Optional[str] = None
):
    """
    Send a security vulnerability alert to Slack channel.
    
    Args:
        vulnerability_type: Type of vulnerability (e.g., "XSS", "SQL Injection", "IDOR")
        severity: Severity level ("Critical", "High", "Medium", "Low", "Info")
        target_url: The affected URL or endpoint
        description: Detailed description of the vulnerability
        evidence: Optional proof-of-concept or evidence details
        recommendation: Optional remediation recommendation
        thread_ts: Optional thread timestamp to reply to existing thread
    """
    
    # Severity color mapping
    severity_colors = {
        "Critical": "#FF0000",  # Red
        "High": "#FF6600",      # Orange
        "Medium": "#FFB84D",    # Yellow-Orange
        "Low": "#FFCC00",       # Yellow
        "Info": "#0099FF"       # Blue
    }
    
    # Severity emoji mapping
    severity_emojis = {
        "Critical": "🚨",
        "High": "⚠️",
        "Medium": "⚡",
        "Low": "📝",
        "Info": "ℹ️"
    }
    
    color = severity_colors.get(severity, "#808080")
    emoji = severity_emojis.get(severity, "📌")
    
    # Build Slack message with blocks for rich formatting
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} {vulnerability_type} Vulnerability Detected",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*Severity:*\n{severity}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"*Target:*\n<{target_url}|{target_url}>"
                }
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Description:*\n{description}"
            }
        }
    ]
    
    # Add evidence if provided
    if evidence:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Evidence/PoC:*\n```{evidence[:500]}```"  # Limit evidence length
            }
        })
    
    # Add recommendation if provided
    if recommendation:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Recommendation:*\n{recommendation}"
            }
        })
    
    # Add timestamp
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Detected at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
            }
        ]
    })
    
    # Fallback text for notifications
    fallback_text = f"{emoji} {severity} {vulnerability_type} vulnerability found at {target_url}"
    
    # Send via webhook
    if SLACK_WEBHOOK_URL:
        payload = {
            "channel": SLACK_CHANNEL,
            "username": "Security Scanner Bot",
            "icon_emoji": ":shield:",
            "text": fallback_text,
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "fallback": fallback_text
                }
            ]
        }
        
        if thread_ts:
            payload["thread_ts"] = thread_ts
        
        async with aiohttp.ClientSession() as session:
            async with session.post(SLACK_WEBHOOK_URL, json=payload) as response:
                if response.status == 200:
                    return json_module.dumps({"success": True, "message": "Alert sent to Slack successfully"})
                else:
                    error_text = await response.text()
                    return json_module.dumps({"success": False, "error": f"Failed to send to Slack: {error_text}"})
    else:
        return json_module.dumps({
            "success": False, 
            "error": "No Slack webhook configured. Set SLACK_WEBHOOK_URL in .env file"
        })


@function_tool(name_override="send_slack_summary")
async def send_slack_scan_summary(
    target_url: str,
    total_findings: int,
    critical_count: int = 0,
    high_count: int = 0,
    medium_count: int = 0,
    low_count: int = 0,
    scan_duration: Optional[str] = None
):
    """
    Send a summary of the security scan to Slack.
    
    Args:
        target_url: The target that was scanned
        total_findings: Total number of vulnerabilities found
        critical_count: Number of critical severity findings
        high_count: Number of high severity findings
        medium_count: Number of medium severity findings
        low_count: Number of low severity findings
        scan_duration: Optional duration of the scan
    """
    
    # Determine overall status
    if critical_count > 0:
        status_emoji = "🔴"
        status_text = "Critical Issues Found"
        color = "#FF0000"
    elif high_count > 0:
        status_emoji = "🟠"
        status_text = "High Risk Issues Found"
        color = "#FF6600"
    elif medium_count > 0:
        status_emoji = "🟡"
        status_text = "Medium Risk Issues Found"
        color = "#FFB84D"
    elif low_count > 0:
        status_emoji = "🟢"
        status_text = "Low Risk Issues Found"
        color = "#00FF00"
    else:
        status_emoji = "✅"
        status_text = "No Issues Found"
        color = "#00FF00"
    
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{status_emoji} Security Scan Summary",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Target:* <{target_url}|{target_url}>\n*Status:* {status_text}\n*Total Findings:* {total_findings}"
            }
        }
    ]
    
    # Add findings breakdown if any exist
    if total_findings > 0:
        findings_text = []
        if critical_count > 0:
            findings_text.append(f"🚨 Critical: {critical_count}")
        if high_count > 0:
            findings_text.append(f"⚠️ High: {high_count}")
        if medium_count > 0:
            findings_text.append(f"⚡ Medium: {medium_count}")
        if low_count > 0:
            findings_text.append(f"📝 Low: {low_count}")
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Findings Breakdown:*\n" + "\n".join(findings_text)
            }
        })
    
    # Add scan duration if provided
    if scan_duration:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Scan Duration: {scan_duration} | Completed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
    
    fallback_text = f"{status_emoji} Security scan completed for {target_url}: {total_findings} findings"
    
    # Send via webhook
    if SLACK_WEBHOOK_URL:
        payload = {
            "channel": SLACK_CHANNEL,
            "username": "Security Scanner Bot",
            "icon_emoji": ":shield:",
            "text": fallback_text,
            "blocks": blocks,
            "attachments": [
                {
                    "color": color,
                    "fallback": fallback_text
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(SLACK_WEBHOOK_URL, json=payload) as response:
                if response.status == 200:
                    return json_module.dumps({"success": True, "message": "Summary sent to Slack successfully"})
                else:
                    error_text = await response.text()
                    return json_module.dumps({"success": False, "error": f"Failed to send to Slack: {error_text}"})
    else:
        return json_module.dumps({
            "success": False,
            "error": "No Slack webhook configured. Set SLACK_WEBHOOK_URL in .env file"
        })


@function_tool(name_override="sandbox_agent")
async def run_sandbox_agent(instruction: str, max_rounds: int = 100):
    """
    Nested agent loop that uses only sandbox execution tools to fulfill the provided instruction.
    Returns the final textual response when the model stops requesting tools or when max_rounds is hit.
    
    Args:
        instruction: The instruction for the sandbox agent to execute
        max_rounds: Maximum number of execution rounds (default: 100)
    """
    sandbox_system_prompt = os.getenv(
        "SANDBOX_SYSTEM_PROMPT",
        (
            "You are an agent that autonomously interacts with an isolated sandbox using two tools: "
            "`sandbox_run_command` (bash) and `sandbox_run_python` (Python). Keep responses within 30,000 "
            "characters; chunk large outputs. Think step-by-step before taking actions."
        ),
    )

    sandbox_input_list = [
        {
            "role": "developer",
            "content": [
                {"type": "input_text", "text": sandbox_system_prompt},
            ],
        },
        {"role": "user", "content": instruction},
    ]

    # Restrict to the low-level sandbox tools to avoid recursive nesting
    sandbox_tools = [
        t for t in tools if t.get("name") in ("sandbox_run_command", "sandbox_run_python")
    ]

    # print(f"[debug] Sandbox input list: {sandbox_input_list}")

    rounds_completed = 0
    while True:
        response = await client.responses.create(
            model="gpt-5",
            tools=sandbox_tools,
            input=sandbox_input_list,
            reasoning={ "effort": "high" },
            extra_body={
                    "metadata": {
                        "name": "sandbox_agent",
                    }
                }
        )

        # Log sandbox agent usage
        usage_tracker = get_current_usage_tracker()
        if usage_tracker and hasattr(response, 'usage'):
            usage_tracker.log_sandbox_agent_usage(response.usage, getattr(_thread_local, 'current_target_url', ''))

        function_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        # print(f"[debug] Function calls: {function_calls}")

        if not function_calls:
            output_text = ""
            for item in response.output:
                if item.type == "message" and hasattr(item, 'content'):
                    for content_item in item.content:
                        if hasattr(content_item, 'text'):
                            output_text += content_item.text
            # print(output_text)
            return output_text or ""

        # Record model tool requests and execute them in parallel
        sandbox_input_list.extend(response.output)
        tasks = [
            execute_function_call(function_call) for function_call in function_calls
        ]
        results = await asyncio.gather(*tasks)

        sandbox_input_list.extend(results)
        rounds_completed += 1

        if max_rounds and rounds_completed >= max_rounds:
            return f"[sandbox_agent] Reached max rounds limit: {max_rounds}"
        
@function_tool(name_override="validator_agent")
async def run_validator_agent(instruction: str, max_rounds: int = 50):
    """
    Agent loop specialized for validating Proofs-of-Concept (PoCs) in the sandbox.
    Use only sandbox tools, keep outputs concise, and return a clear verdict.

    Args:
        instruction: Validation instruction that includes the PoC and expected outcome
        max_rounds: Maximum number of execution rounds (default: 50)
    """
    validator_system_prompt = os.getenv(
        "VALIDATOR_SYSTEM_PROMPT",
        (
            "You validate security PoCs inside an isolated sandbox using two tools: "
            "`sandbox_run_command` (bash) and `sandbox_run_python` (Python). Your goal is to: "
            "(1) Reproduce the PoC minimally and safely, (2) Capture evidence (stdout, file diffs, HTTP responses), "
            "(3) Decide if the PoC reliably demonstrates a real vulnerability with impact, (4) Provide a concise verdict. "
            "Always think step-by-step before actions. Keep outputs within 30,000 characters and chunk large outputs. "
            "Avoid destructive actions unless explicitly required for validation."
        ),
    )

    validator_input_list = [
        {
            "role": "developer",
            "content": [
                {"type": "input_text", "text": validator_system_prompt},
            ],
        },
        {"role": "user", "content": instruction},
    ]

    validator_tools = [
        t for t in tools if t.get("name") in ("sandbox_run_command", "sandbox_run_python")
    ]

    rounds_completed = 0
    while True:
        response = await client.responses.create(
            model="gpt-5",
            tools=validator_tools,
            input=validator_input_list,
            reasoning={ "effort": "high" },
            extra_body={
                    "metadata": {
                        "name": "validator_agent",
                    }
                }
        )

        # Reuse sandbox usage tracker for validator agent
        usage_tracker = get_current_usage_tracker()
        if usage_tracker and hasattr(response, 'usage'):
            usage_tracker.log_sandbox_agent_usage(response.usage, getattr(_thread_local, 'current_target_url', ''))

        function_calls = [
            item for item in response.output if item.type == "function_call"
        ]

        if not function_calls:
            output_text = ""
            for item in response.output:
                if item.type == "message" and hasattr(item, 'content'):
                    for content_item in item.content:
                        if hasattr(content_item, 'text'):
                            output_text += content_item.text
            return output_text or ""

        validator_input_list.extend(response.output)
        tasks = [
            execute_function_call(function_call) for function_call in function_calls
        ]
        results = await asyncio.gather(*tasks)

        validator_input_list.extend(results)
        rounds_completed += 1

        if max_rounds and rounds_completed >= max_rounds:
            return f"[validator_agent] Reached max rounds limit: {max_rounds}"
        
@function_tool
async def sandbox_run_python(python_code: str, timeout: int = 120):
    """
    Run Python code inside a Docker sandbox and return stdout/stderr/exit code. If the output exceeds 30000 characters, output will be truncated before being returned to you.

    Args:
        python_code: Python code to execute (e.g., "print('Hello World')").
        timeout: Max seconds to wait before timing out the code execution.

    Returns:
        A string containing exit code, stdout, and stderr.
    """

    print(f"Running Python code: {python_code[:100]}...")
    try:
        # Get the current sandbox instance
        sbx = get_current_sandbox()
        if sbx is None:
            return "Error: No sandbox instance available for this scan"
            
        import uuid
        # Generate a random script name
        script_name = f"temp_script_{uuid.uuid4().hex[:8]}.py"
        script_path = f"/home/user/{script_name}"
        
        # Write Python code to a temporary file with random name
        sbx.files.write(script_path, python_code)
        
        # Execute the Python script using configured sandbox
        result = sbx.commands.run(f"source .venv/bin/activate && python3 {script_path}", timeout=timeout, user="root")

        stdout_raw = (
            result.stdout
            if hasattr(result, "stdout") and result.stdout is not None
            else ""
        )
        stderr_raw = (
            result.stderr
            if hasattr(result, "stderr") and result.stderr is not None
            else ""
        )
        exit_code = result.exit_code if hasattr(result, "exit_code") else "unknown"

        output = f"Exit code: {exit_code}\n\nSTDOUT\n{stdout_raw}\n\nSTDERR\n{stderr_raw}"

        # Truncate output if it exceeds 30000 characters
        if len(output) > 30000:
            output = (
                output[:30000]
                + "\n...[OUTPUT TRUNCATED - EXCEEDED 30000 CHARACTERS]"
            )

        return output
    except Exception as e:
        return f"Failed to run Python code in sandbox: {e}"


@function_tool
async def sandbox_run_command(command: str, timeout: int = 120):
    """
    Run a shell command inside an ephemeral sandbox and return stdout/stderr/exit code.

    Arguments:
        command: Shell command to execute (e.g., "ls -la").
        timeout: Max seconds to wait before timing out the command.

    Returns:
        A string containing exit code, stdout, and stderr.
    """

    print(f"Running command: {command}")
    try:
        # Get the current sandbox instance
        sbx = get_current_sandbox()
        if sbx is None:
            return "Error: No sandbox instance available for this scan"
            
        # Use the current sandbox instance
        result = sbx.commands.run(command, timeout=timeout, user="root")

        def clip_to_max_lines(text: str, max_lines: int = 100) -> str:
            if not text:
                return ""
            lines = text.splitlines()
            if len(lines) <= max_lines:
                return "\n".join(lines)
            visible = "\n".join(lines[:max_lines])
            remaining = len(lines) - max_lines
            return f"{visible}\n...[TRUNCATED {remaining} more lines]"

        stdout_raw = (
            result.stdout
            if hasattr(result, "stdout") and result.stdout is not None
            else ""
        )
        stderr_raw = (
            result.stderr
            if hasattr(result, "stderr") and result.stderr is not None
            else ""
        )
        # stdout = clip_to_max_lines(stdout_raw, 50)
        # stderr = clip_to_max_lines(stderr_raw, 50)
        exit_code = result.exit_code if hasattr(result, "exit_code") else "unknown"

        return f"Exit code: {exit_code}\n\nSTDOUT\n{stdout_raw}\n\nSTDERR\n{stderr_raw}"
    except Exception as e:
        return f"Failed to run command in sandbox: {e}"

# Collect all function tools that were decorated
_function_tools = {
    "sandbox_run_command": sandbox_run_command,
    "sandbox_run_python": sandbox_run_python,
    "sandbox_agent": run_sandbox_agent,
    "validator_agent": run_validator_agent,
    "get_message_by_id": get_message_by_id,
    "list_account_messages": list_account_messages,
    "get_registered_emails": get_registered_emails,
    "send_slack_alert": send_slack_security_alert,
    "send_slack_summary": send_slack_scan_summary,
}

async def execute_tool(name: str, arguments: Dict[str, Any]) -> str:
    try:
        if name in _function_tools:
            func_tool = _function_tools[name]
            if name == "sandbox_agent":
                # Handle legacy 'input' parameter or new 'instruction' parameter
                instruction = arguments.get("instruction", arguments.get("input", ""))
                max_rounds = arguments.get("max_rounds", 100)
                out = await func_tool(instruction, max_rounds)
            else:
                out = await func_tool(**arguments)
        else:
            out = {"error": f"Unknown tool: {name}", "args": arguments}
    except Exception as e:
        out = {"error": str(e), "args": arguments}
    return json.dumps(out)


def generate_tools_from_function_tools():
    """Auto-generate tools list from decorated functions."""
    tools = []
    
    for _, func_tool in _function_tools.items():
        # Each function tool should have the FunctionTool attributes
        if hasattr(func_tool, 'name') and hasattr(func_tool, 'description') and hasattr(func_tool, 'params_json_schema'):
            tool_def = {
                "type": "function",
                "name": func_tool.name,
                "description": func_tool.description,
                "parameters": func_tool.params_json_schema,
                "strict": getattr(func_tool, 'strict_json_schema', True),
            }
            tools.append(tool_def)
    
    return tools

# Generate tools automatically from decorated functions
tools = generate_tools_from_function_tools()


user_prompt = """i need you to come up with detailed poc for the workflow code injection vulnerability

"""


def read_targets_from_file(file_path: str) -> List[str]:
    """
    Read target URLs from a text file, one per line.
    Ignores empty lines and lines starting with #.
    """
    targets = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    targets.append(line)
        return targets
    except FileNotFoundError:
        print(f"Error: Target file '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error reading target file: {e}")
        return []

async def run_continuously(max_rounds: int = 100, user_prompt: str = "", system_prompt: str = "", target_url: str = "", sandbox_instance=None):
    """
    Keep prompting the model and executing any requested tool calls in parallel
    until the model stops requesting tools or the optional max_rounds is reached.

    max_rounds: 0 means unlimited; otherwise, loop up to max_rounds tool-execution rounds.
    target_url: The target URL being scanned (used for metadata)
    sandbox_instance: Specific sandbox instance to use for this scan
    """
    # Create sandbox instance if not provided
    if sandbox_instance is None:
        sandbox_instance = create_sandbox_from_env()
    
    # Set the sandbox for this thread/scan
    set_current_sandbox(sandbox_instance)
    
    # Set target URL for usage tracking
    _thread_local.current_target_url = target_url
    
    rounds_completed = 0

    input_list = [
    {"role": "developer", "content": [{"type": "input_text", "text": system_prompt}]},
    {
        "role": "user",
        "content": user_prompt,
    }]

    main_agent_tools = [t for t in tools if t.get("name") in ("sandbox_agent", "validator_agent", "get_message_by_id", "list_account_messages", "get_registered_emails", "send_slack_alert", "send_slack_summary")]

    # Extract site name from URL for metadata
    site_name = target_url.replace("https://", "").replace("http://", "").split('/')[0] if target_url else "unknown"

    try:
        while True:
            # 1) Ask the model what to do next
            response = await client.responses.create(
                model="gpt-5",
                tools=main_agent_tools,
                input=input_list,
                reasoning={ "effort": "high" },
                extra_body={
                    "metadata": {
                        "name": "security_scan",
                        "site_name": site_name,
                        "target_url": target_url,
                    }
                }
            )

            # Log main agent usage
            usage_tracker = get_current_usage_tracker()
            if usage_tracker and hasattr(response, 'usage'):
                usage_tracker.log_main_agent_usage(response.usage, target_url)

            # 2) Check for function calls
            function_calls = [
                item for item in response.output if item.type == "function_call"
            ] 

            # If there are no tool calls, print whatever the model returned and stop
            if not function_calls:
                output_text = ""
                for item in response.output:
                    if item.type == "message" and hasattr(item, 'content'):
                        for content_item in item.content:
                            if hasattr(content_item, 'text'):
                                output_text += content_item.text
                        break
                print(output_text)
                print(response.id)
                return output_text

            # 3) Record the function calls in the conversation and execute them in parallel
            input_list.extend(response.output)
            print(f"[debug] Executing {len(function_calls)} function calls in parallel...")

            tasks = [
                execute_function_call(function_call) for function_call in function_calls
            ]
            results = await asyncio.gather(*tasks)

            # 4) Add tool results for the next round
            input_list.extend(results)
            rounds_completed += 1

            # 5) Safety valve for infinite loops
            if max_rounds and rounds_completed >= max_rounds:
                print(f"[debug] Reached max rounds limit: {max_rounds}")
                break
    finally:
        # Kill the sandbox when scan is done
        if sandbox_instance and hasattr(sandbox_instance, "kill"):
            sandbox_instance.kill()

async def run_single_target_scan(target_url: str, system_prompt: str, base_user_prompt: str, max_rounds: int = 100):
    """
    Run a security scan for a single target URL.
    Returns the scan result and saves it to a file.
    Each scan gets its own isolated sandbox instance.
    """
    print(f"Starting scan for: {target_url}")
    
    # Create a dedicated sandbox instance for this scan (if configured)
    sandbox_instance = create_sandbox_from_env()
    
    # Create usage tracker for this scan
    usage_tracker = UsageTracker()
    set_current_usage_tracker(usage_tracker)
    
    # Format the user prompt with the target URL
    user_prompt = base_user_prompt.format(target_url=target_url)
    
    try:
        # Run the scan with dedicated sandbox
        result = await run_continuously(
            user_prompt=user_prompt, 
            system_prompt=system_prompt, 
            target_url=target_url,
            max_rounds=max_rounds,
            sandbox_instance=sandbox_instance
        )
        
        # Generate filename from target URL
        filename = target_url.replace("https://", "").replace("http://", "").replace("/", "_") + ".md"
        
        # Save result to file
        with open(filename, "w", encoding='utf-8') as f:
            f.write(str(result) if result is not None else "")
        
        # Save usage data
        site_name = target_url.replace("https://", "").replace("http://", "").split('/')[0]
        usage_filename = usage_tracker.save_to_file(f"{site_name}_")
        
        print(f"Scan completed for {target_url} - Results saved to {filename}")
        print(f"Usage data saved to {usage_filename}")
        
        return {
            "target": target_url,
            "filename": filename,
            "usage_filename": usage_filename,
            "status": "completed",
            "result": result,
            "usage_summary": usage_tracker.get_summary()
        }
        
    except Exception as e:
        print(f"Error scanning {target_url}: {e}")
        return {
            "target": target_url,
            "filename": None,
            "status": "error",
            "error": str(e)
        }

async def run_parallel_scans(targets: List[str], system_prompt: str, base_user_prompt: str, max_rounds: int = 100):
    """
    Run security scans for multiple targets in parallel.
    """
    print(f"Starting parallel scans for {len(targets)} targets...")
    
    # Create tasks for all targets
    tasks = [
        run_single_target_scan(target, system_prompt, base_user_prompt, max_rounds)
        for target in targets
    ]
    
    # Run all scans in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    completed = 0
    errors = 0
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Task failed with exception: {result}")
            errors += 1
        elif isinstance(result, dict) and result.get("status") == "completed":
            completed += 1
        else:
            errors += 1
    
    print(f"\nScan Summary:")
    print(f"Total targets: {len(targets)}")
    print(f"Completed successfully: {completed}")
    print(f"Failed: {errors}")
    
    # Create overall usage summary
    total_main_calls = 0
    total_sandbox_calls = 0
    usage_files = []
    
    for result in results:
        if isinstance(result, dict) and result.get("status") == "completed":
            summary = result.get("usage_summary", {})
            total_main_calls += summary.get("main_agent_calls", 0)
            total_sandbox_calls += summary.get("sandbox_agent_calls", 0)
            if "usage_filename" in result:
                usage_files.append(result["usage_filename"])
    
    print(f"\nUsage Summary:")
    print(f"Total Main Agent API calls: {total_main_calls}")
    print(f"Total Sandbox Agent API calls: {total_sandbox_calls}")
    print(f"Total API calls: {total_main_calls + total_sandbox_calls}")
    print(f"Usage files created: {len(usage_files)}")
    for uf in usage_files:
        print(f"  - {uf}")
    
    return results


if __name__ == "__main__":
    import sys
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('scan_usage.log'),
            logging.StreamHandler()
        ]
    )
    
    system_prompt = os.getenv("SYSTEM_PROMPT", "SYSTEM_PROMPT_REDACTED")

    # Check if targets.txt file exists in current directory
    targets_file = "targets.txt"
    
    if os.path.exists(targets_file):
        print(f"Found targets file: {targets_file}")
        
        # Read targets from file
        targets = read_targets_from_file(targets_file)
        
        if not targets:
            print("No valid targets found in targets.txt file. Falling back to single target mode.")
        else:
            print(f"Found {len(targets)} targets to scan")
            
            # Base user prompt template (will be formatted with target_url)
            base_user_prompt = "I need you to do a full vulnerability scan of {target_url}, you must critically analyse the code and identify every single vulnerability, for identified vulnerabilities a PoC must be provided, focus on critical vulnerabilities, i m only insterested in real world vulnerabilities, not theoretical ones"
            
            # Run parallel scans
            results = asyncio.run(run_parallel_scans(targets, system_prompt, base_user_prompt))
            
            print("\nAll scans completed!")
            sys.exit(0)
    