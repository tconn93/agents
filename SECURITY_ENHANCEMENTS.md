# Security Enhancements Plan

## Current Security Status

**⚠️ CRITICAL**: The agent currently has FULL access to the host's file system where the server is running.

### Current Access Level

The agent can:
- ✅ Read any file (except those matching security patterns like `.env`, `.key`, `.pem`)
- ✅ Write/create files anywhere the process has permissions
- ✅ Delete files (with confirmation flag)
- ✅ Execute bash commands on the host
- ✅ Navigate the entire directory structure
- ✅ Install packages
- ✅ Run tests and builds

### Security Implications

#### 🔴 HIGH RISK if running directly on host:
- Agent can access your home directory, documents, SSH keys, etc.
- Can execute arbitrary commands (with some filtering)
- Could accidentally or maliciously damage your system
- Access to environment variables and running processes

#### 🟡 MEDIUM RISK if running in Docker:
- Limited to container file system
- Cannot access host files unless volumes mounted
- Still has full control within container

#### 🟢 LOW RISK if properly sandboxed

---

## Recommended Security Enhancements

### Priority 1: Container Isolation (Implement First)

#### 1.1 Update Dockerfiles with Security Best Practices

**File: `python/Dockerfile`**
```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 agentuser && \
    mkdir -p /workspace && \
    chown agentuser:agentuser /workspace

# Set working directory
WORKDIR /app

# Copy and install dependencies as root
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps

# Copy application files
COPY --chown=agentuser:agentuser . .

# Switch to non-root user
USER agentuser

# Set workspace as default working directory
WORKDIR /workspace

# Run with limited permissions
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File: `js/Dockerfile`**
```dockerfile
FROM node:20-slim

# Install Playwright dependencies
RUN apt-get update && \
    apt-get install -y wget gnupg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 agentuser && \
    mkdir -p /workspace && \
    chown agentuser:agentuser /workspace

# Set working directory
WORKDIR /app

# Copy and install dependencies as root
COPY package*.json ./
RUN npm install && \
    npx playwright install chromium && \
    npx playwright install-deps chromium

# Copy application files
COPY --chown=agentuser:agentuser . .

# Switch to non-root user
USER agentuser

# Set workspace as default working directory
WORKDIR /workspace

CMD ["node", "agent.js"]
```

#### 1.2 Create Docker Compose Configuration

**File: `docker-compose.yml`**
```yaml
version: '3.8'

services:
  llm-agent-python:
    build: ./python
    container_name: llm-agent-python
    ports:
      - "8000:8000"
    environment:
      - PROVIDER=${PROVIDER:-groq}
      - MODEL=${MODEL:-llama3-8b-8192}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ALLOWED_TOOLS=${ALLOWED_TOOLS}
      - AGENT_WORKSPACE=/workspace
    volumes:
      # Only mount specific workspace, not entire host
      - ./workspace:/workspace:rw
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
      - SETGID
      - SETUID
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    restart: unless-stopped

  llm-agent-js:
    build: ./js
    container_name: llm-agent-js
    ports:
      - "8001:8000"
    environment:
      - PROVIDER=${PROVIDER:-groq}
      - MODEL=${MODEL:-llama3-8b-8192}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ALLOWED_TOOLS=${ALLOWED_TOOLS}
      - AGENT_WORKSPACE=/workspace
    volumes:
      - ./workspace:/workspace:rw
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - DAC_OVERRIDE
      - SETGID
      - SETUID
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    restart: unless-stopped
```

**File: `.env.example`**
```bash
# LLM Provider Configuration
PROVIDER=groq
MODEL=llama3-8b-8192

# API Keys (set these in .env file, never commit)
GROQ_API_KEY=your-groq-api-key-here
ANTHROPIC_API_KEY=your-anthropic-api-key-here
OPENAI_API_KEY=your-openai-api-key-here

# Tool Configuration
# Leave empty to enable all tools
# Or specify comma-separated list:
ALLOWED_TOOLS=explore_project,read_file,write_file,search_code,find_files,git_status,git_diff,run_tests

# Security Configuration
AGENT_WORKSPACE=/workspace
```

### Priority 2: Path Validation (Implement Second)

Add workspace path validation to all file operations.

#### 2.1 Python Implementation

**Add to: `python/tools.py`**
```python
import os
from pathlib import Path

# At the top of the file, after imports
ALLOWED_BASE_PATH = os.getenv("AGENT_WORKSPACE", os.getcwd())

def _validate_path(file_path: str) -> tuple[bool, str]:
    """
    Ensure path is within allowed workspace.
    Returns (is_valid, resolved_path_or_error_message)
    """
    try:
        resolved = Path(file_path).resolve()
        allowed = Path(ALLOWED_BASE_PATH).resolve()

        # Check if resolved path is within allowed base path
        resolved.relative_to(allowed)
        return True, str(resolved)
    except ValueError:
        return False, f"Error: Access denied. Path '{file_path}' is outside allowed workspace '{ALLOWED_BASE_PATH}'"
    except Exception as e:
        return False, f"Error: Invalid path - {e}"

# Update each file operation function to use validation
async def read_file(file_path: str, max_lines: int = 500) -> str:
    """Read file contents with security checks."""
    print(f"[Tool] Executing read_file on: '{file_path}'")

    # Validate path
    is_valid, result = _validate_path(file_path)
    if not is_valid:
        return result  # Return error message

    resolved_path = result
    # ... rest of existing function using resolved_path

async def write_file(file_path: str, content: str) -> str:
    """Write content to a file."""
    print(f"[Tool] Executing write_file to: '{file_path}'")

    # Validate path
    is_valid, result = _validate_path(file_path)
    if not is_valid:
        return result

    resolved_path = result
    # ... rest of existing function using resolved_path

# Apply same pattern to: edit_file, delete_file, copy_file, move_file, etc.
```

#### 2.2 JavaScript Implementation

**Add to: `js/tools.js`**
```javascript
import path from 'path';
import { fileURLToPath } from 'url';

// At the top of the file
const ALLOWED_BASE_PATH = process.env.AGENT_WORKSPACE || process.cwd();

function _validatePath(filePath) {
    /**
     * Ensure path is within allowed workspace.
     * Returns { valid: boolean, path: string|null, error: string|null }
     */
    try {
        const resolved = path.resolve(filePath);
        const allowed = path.resolve(ALLOWED_BASE_PATH);

        // Check if resolved path starts with allowed base path
        if (!resolved.startsWith(allowed)) {
            return {
                valid: false,
                path: null,
                error: `Error: Access denied. Path '${filePath}' is outside allowed workspace '${ALLOWED_BASE_PATH}'`
            };
        }

        return { valid: true, path: resolved, error: null };
    } catch (e) {
        return { valid: false, path: null, error: `Error: Invalid path - ${e.message}` };
    }
}

// Update file operations
async function read_file(filePath, maxLines = 500) {
    console.log(`[Tool] Executing read_file on: "${filePath}"`);

    const validation = _validatePath(filePath);
    if (!validation.valid) {
        return validation.error;
    }

    const resolvedPath = validation.path;
    // ... rest of existing function using resolvedPath
}

// Apply same pattern to: write_file, edit_file, delete_file, copy_file, move_file, etc.
```

### Priority 3: Command Whitelisting (Implement Third)

Replace command blacklisting with whitelisting for better security.

#### 3.1 Python Implementation

**Add to: `python/tools.py`**
```python
# Command whitelist configuration
ALLOWED_COMMANDS = {
    'git', 'npm', 'pip', 'python', 'python3', 'node', 'pytest', 'jest',
    'ls', 'cat', 'grep', 'find', 'echo', 'pwd', 'which', 'wc',
    'eslint', 'pylint', 'flake8', 'black', 'prettier',
    'make', 'cargo', 'yarn', 'pnpm'
}

def _validate_command(command: str) -> tuple[bool, str]:
    """
    Validate command against whitelist.
    Returns (is_valid, error_message_or_empty)
    """
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return False, "Error: Empty command"

    cmd_name = cmd_parts[0].split('/')[-1]  # Handle paths like /usr/bin/python

    if cmd_name not in ALLOWED_COMMANDS:
        return False, f"Error: Command '{cmd_name}' not in whitelist. Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"

    return True, ""

async def bash_command(command: str, timeout: int = 30) -> str:
    """Execute a bash command with security restrictions."""
    print(f"[Tool] Executing bash_command: '{command}'")

    # Validate command
    is_valid, error = _validate_command(command)
    if not is_valid:
        return error

    # ... rest of existing function
```

#### 3.2 JavaScript Implementation

**Add to: `js/tools.js`**
```javascript
// Command whitelist configuration
const ALLOWED_COMMANDS = new Set([
    'git', 'npm', 'pip', 'python', 'python3', 'node', 'pytest', 'jest',
    'ls', 'cat', 'grep', 'find', 'echo', 'pwd', 'which', 'wc',
    'eslint', 'pylint', 'flake8', 'black', 'prettier',
    'make', 'cargo', 'yarn', 'pnpm'
]);

function _validateCommand(command) {
    /**
     * Validate command against whitelist.
     * Returns { valid: boolean, error: string|null }
     */
    const cmdParts = command.trim().split(/\s+/);
    if (cmdParts.length === 0) {
        return { valid: false, error: "Error: Empty command" };
    }

    const cmdName = cmdParts[0].split('/').pop(); // Handle paths

    if (!ALLOWED_COMMANDS.has(cmdName)) {
        const allowed = Array.from(ALLOWED_COMMANDS).sort().join(', ');
        return {
            valid: false,
            error: `Error: Command '${cmdName}' not in whitelist. Allowed: ${allowed}`
        };
    }

    return { valid: true, error: null };
}

async function bash_command(command, timeout = 30) {
    console.log(`[Tool] Executing bash_command: "${command}"`);

    const validation = _validateCommand(command);
    if (!validation.valid) {
        return validation.error;
    }

    // ... rest of existing function
}
```

### Priority 4: Audit Logging (Implement Fourth)

Add comprehensive logging for all sensitive operations.

#### 4.1 Python Implementation

**Create: `python/audit_logger.py`**
```python
import logging
import json
from datetime import datetime
from pathlib import Path

# Configure audit logger
audit_logger = logging.getLogger('agent_audit')
audit_logger.setLevel(logging.INFO)

# Create audit log file handler
audit_log_path = Path('logs/audit.log')
audit_log_path.parent.mkdir(exist_ok=True)

file_handler = logging.FileHandler(audit_log_path)
file_handler.setLevel(logging.INFO)

# JSON formatter for structured logs
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'action': record.msg,
            'details': getattr(record, 'details', {}),
            'user': getattr(record, 'user', 'unknown'),
            'ip': getattr(record, 'ip', 'unknown')
        }
        return json.dumps(log_data)

file_handler.setFormatter(JSONFormatter())
audit_logger.addHandler(file_handler)

def log_file_operation(operation: str, file_path: str, success: bool, details: dict = None):
    """Log file operations for audit trail."""
    audit_logger.info(
        f"{operation}",
        extra={
            'details': {
                'operation': operation,
                'file_path': file_path,
                'success': success,
                **(details or {})
            }
        }
    )

def log_command_execution(command: str, success: bool, output: str = None):
    """Log command executions for audit trail."""
    audit_logger.info(
        "command_execution",
        extra={
            'details': {
                'command': command,
                'success': success,
                'output_length': len(output) if output else 0
            }
        }
    )
```

**Update: `python/tools.py`**
```python
from audit_logger import log_file_operation, log_command_execution

async def read_file(file_path: str, max_lines: int = 500) -> str:
    """Read file contents with security checks and audit logging."""
    print(f"[Tool] Executing read_file on: '{file_path}'")

    try:
        # ... existing validation and read logic ...

        log_file_operation('read_file', file_path, True, {'lines_read': len(lines)})
        return f"Contents of {file_path}:\n\n{content}"
    except Exception as e:
        log_file_operation('read_file', file_path, False, {'error': str(e)})
        return f"Error reading file: {e}"

async def bash_command(command: str, timeout: int = 30) -> str:
    """Execute bash command with audit logging."""
    print(f"[Tool] Executing bash_command: '{command}'")

    try:
        # ... existing validation and execution logic ...

        log_command_execution(command, result.returncode == 0, result.stdout)
        return output
    except Exception as e:
        log_command_execution(command, False, str(e))
        return f"Error executing command: {e}"
```

#### 4.2 JavaScript Implementation

**Create: `js/auditLogger.js`**
```javascript
import fs from 'fs';
import path from 'path';

const AUDIT_LOG_PATH = 'logs/audit.log';

// Ensure log directory exists
const logDir = path.dirname(AUDIT_LOG_PATH);
if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
}

function writeAuditLog(logEntry) {
    const logLine = JSON.stringify({
        timestamp: new Date().toISOString(),
        ...logEntry
    }) + '\n';

    fs.appendFileSync(AUDIT_LOG_PATH, logLine);
}

export function logFileOperation(operation, filePath, success, details = {}) {
    writeAuditLog({
        level: 'INFO',
        action: operation,
        details: {
            operation,
            file_path: filePath,
            success,
            ...details
        }
    });
}

export function logCommandExecution(command, success, output = null) {
    writeAuditLog({
        level: 'INFO',
        action: 'command_execution',
        details: {
            command,
            success,
            output_length: output ? output.length : 0
        }
    });
}
```

**Update: `js/tools.js`**
```javascript
import { logFileOperation, logCommandExecution } from './auditLogger.js';

async function read_file(filePath, maxLines = 500) {
    console.log(`[Tool] Executing read_file on: "${filePath}"`);

    try {
        // ... existing validation and read logic ...

        logFileOperation('read_file', filePath, true, { lines_read: lines.length });
        return `Contents of ${filePath}:\n\n${content}`;
    } catch (e) {
        logFileOperation('read_file', filePath, false, { error: e.message });
        return `Error reading file: ${e.message}`;
    }
}
```

### Priority 5: Security Monitoring Script

**Create: `security-check.sh`**
```bash
#!/bin/bash

echo "🔍 Security Audit for LLM Agent"
echo "================================"
echo ""

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "✅ Running in Docker container"
else
    echo "⚠️  WARNING: Running on host system (HIGH RISK)"
fi
echo ""

# Check user
if [ "$(id -u)" -eq 0 ]; then
    echo "❌ Running as root (DANGEROUS)"
else
    echo "✅ Running as non-root user: $(whoami) (UID: $(id -u))"
fi
echo ""

# Check allowed tools
if [ -z "$ALLOWED_TOOLS" ]; then
    echo "⚠️  ALLOWED_TOOLS not set (all tools enabled)"
else
    echo "✅ ALLOWED_TOOLS configured: $ALLOWED_TOOLS"
fi
echo ""

# Check workspace restriction
if [ -z "$AGENT_WORKSPACE" ]; then
    echo "⚠️  AGENT_WORKSPACE not set (no path restrictions)"
else
    echo "✅ AGENT_WORKSPACE: $AGENT_WORKSPACE"
fi
echo ""

# Check sensitive file access
echo "Checking access to sensitive files:"
if [ -r "$HOME/.ssh/id_rsa" ]; then
    echo "  ❌ Can read SSH private key (DANGEROUS)"
else
    echo "  ✅ Cannot read SSH private key"
fi

if [ -r "$HOME/.aws/credentials" ]; then
    echo "  ❌ Can read AWS credentials (DANGEROUS)"
else
    echo "  ✅ Cannot read AWS credentials"
fi

if [ -r "/etc/passwd" ]; then
    echo "  ⚠️  Can read /etc/passwd (expected in containers)"
else
    echo "  ✅ Cannot read /etc/passwd"
fi
echo ""

# Check capabilities
echo "Security capabilities:"
if command -v capsh &> /dev/null; then
    capsh --print | grep -i "current:"
else
    echo "  ℹ️  capsh not available (cannot check capabilities)"
fi
echo ""

# Check read-only filesystem
if touch /test-write 2>/dev/null; then
    rm -f /test-write
    echo "⚠️  Filesystem is writable at root level"
else
    echo "✅ Root filesystem is read-only"
fi
echo ""

echo "================================"
echo "Security check complete!"
```

Make executable:
```bash
chmod +x security-check.sh
```

---

## Deployment Strategies by Use Case

### 1. Local Development (Medium Security)
```bash
# Use Docker with workspace mount
docker-compose up llm-agent-python

# Or run security check first
./security-check.sh
```

### 2. Team Development (High Security)
```bash
# Use dedicated VM or container
# Mount only specific project directories
# Enable audit logging
# Restrict tools to read-only plus git operations
export ALLOWED_TOOLS="read_file,search_code,find_files,git_status,git_diff,git_log"
```

### 3. Production/CI (Maximum Security)
```bash
# Use ephemeral containers
# No host mounts except read-only code
# Whitelist minimal tools
# Full audit logging
# Network isolation
docker run --rm \
  --network none \
  --read-only \
  --tmpfs /tmp \
  -v $(pwd)/code:/workspace:ro \
  llm-agent
```

---

## Implementation Checklist

### Phase 1: Basic Security (Do This Week)
- [ ] Create `docker-compose.yml` with security options
- [ ] Update Dockerfiles to use non-root user
- [ ] Create `workspace/` directory for isolated operations
- [ ] Add `.env.example` with security settings
- [ ] Test with `./security-check.sh`

### Phase 2: Path Validation (Next Week)
- [ ] Implement `_validate_path()` in Python
- [ ] Implement `_validatePath()` in JavaScript
- [ ] Update all file operation tools
- [ ] Test path traversal attempts
- [ ] Document in README

### Phase 3: Command Whitelisting (Following Week)
- [ ] Define command whitelist
- [ ] Implement `_validate_command()` in Python
- [ ] Implement `_validateCommand()` in JavaScript
- [ ] Update bash_command and bash_script tools
- [ ] Test with various commands

### Phase 4: Audit Logging (Month 2)
- [ ] Create audit logger module
- [ ] Add logging to all file operations
- [ ] Add logging to all command executions
- [ ] Create log rotation policy
- [ ] Create log monitoring dashboard

### Phase 5: Advanced Security (Ongoing)
- [ ] Add rate limiting
- [ ] Implement session management
- [ ] Add authentication/authorization
- [ ] Create security incident response plan
- [ ] Regular security audits

---

## Testing Security Measures

### Test Path Validation
```bash
# Should FAIL (outside workspace)
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Read the file /etc/passwd"}'

# Should SUCCEED (inside workspace)
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Read the file ./test.txt"}'
```

### Test Command Whitelist
```bash
# Should FAIL (dangerous command)
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Run command: rm -rf /"}'

# Should SUCCEED (whitelisted)
curl -X POST http://localhost:8000/chat \
  -d '{"message": "Run command: git status"}'
```

### Test Audit Logs
```bash
# Check that operations are logged
tail -f logs/audit.log

# Should see JSON entries for each operation
```

---

## Emergency Response Plan

### If Security Breach Detected:

1. **Immediate Actions**
   ```bash
   # Stop all agent containers
   docker-compose down

   # Check audit logs
   cat logs/audit.log | grep -i "error\|fail\|suspicious"

   # Review recent file operations
   find workspace/ -mmin -60 -ls
   ```

2. **Investigation**
   - Review audit logs for unauthorized access
   - Check for modified files
   - Verify no sensitive data exposed
   - Document the incident

3. **Recovery**
   - Restore from backup if needed
   - Update security configurations
   - Patch vulnerabilities
   - Rotate API keys

4. **Prevention**
   - Implement additional security measures
   - Review and update whitelists
   - Enhance monitoring
   - Train team on security practices

---

## Additional Resources

- [OWASP Docker Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Docker_Security_Cheat_Sheet.html)
- [CIS Docker Benchmark](https://www.cisecurity.org/benchmark/docker)
- [Playwright Security Best Practices](https://playwright.dev/docs/ci#security)
- [Python Security Best Practices](https://python.readthedocs.io/en/latest/library/security.html)

---

## Questions & Support

For security concerns or questions:
1. Review this document
2. Check audit logs: `logs/audit.log`
3. Run security check: `./security-check.sh`
4. Create a GitHub issue with `[SECURITY]` tag

**Remember**: Security is an ongoing process, not a one-time implementation.
