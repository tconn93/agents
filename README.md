# Multi-Provider LLM Agent API

A conversational AI agent that provides a unified HTTP API for interacting with multiple LLM providers. Available in both Python and JavaScript implementations.

## Features

- **Multiple LLM Providers**: OpenAI, Anthropic Claude, Google Gemini, Groq, and xAI Grok
- **Unified API**: Single interface for all providers
- **Dual Implementation**: Choose between Python (FastAPI) or JavaScript (Express)
- **Tool Use Support**: Extensible tool system enabling agents to take actions
- **Coding Capabilities**: Built-in tools for file operations, project exploration, and command execution
- **Configurable System Prompts**: Load prompts from files or environment variables
- **Docker Support**: Containerized deployment for both implementations
- **Conversation History**: Maintains context across multiple interactions

## Available Tools

The agent comes with a powerful set of tools that can be enabled via the `ALLOWED_TOOLS` environment variable. These tools enable the AI agent to interact with the codebase and execute commands.

### Standard Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `web_search` | Mock web search functionality | Fetch information from the internet (mock implementation) |
| `calculator` | Mathematical expression evaluation | Solve math problems and equations |

### Basic Coding Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `explore_project` | Directory structure exploration | Understand project organization and file layout |
| `read_file` | Read file contents with security checks | View source code, configurations, and documentation |
| `write_file` | Write/create files with parent directory creation | Generate new files or modify existing ones |
| `bash_command` | Execute single bash commands with timeout | Run git commands, npm/pip installs, ls, etc. |
| `bash_script` | Execute multi-line bash scripts | Run complex scripts and automation tasks |

### Phase 1: Essential Code Navigation Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `search_code` | Search for patterns across files using regex | Find all usages of a function, variable, or pattern |
| `edit_file` | Replace text in a file efficiently | Make targeted edits without rewriting entire files |
| `find_files` | Find files by name pattern (glob or regex) | Locate specific files quickly |
| `git_status` | Show git repository status | Check staged/unstaged changes |
| `git_diff` | Show git diff for repo or specific file | Review changes before committing |
| `git_commit` | Create a git commit with message | Save changes to version control |
| `git_add` | Stage files for commit | Prepare files for committing |
| `git_log` | View commit history | See recent changes |
| `git_branch` | List, create, or switch branches | Manage git branches |

### Phase 2: High-Value Workflow Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `search_and_replace` | Find and replace across multiple files with dry-run | Refactor code, rename variables across codebase |
| `copy_file` | Copy files or directories | Duplicate files, create backups |
| `move_file` | Move or rename files/directories | Reorganize code structure |
| `delete_file` | Delete files/directories (requires confirmation) | Clean up unused files |
| `install_package` | Install packages (npm, pip, yarn) with auto-detection | Add dependencies to project |
| `run_tests` | Run test suites (pytest, jest, npm) with auto-detection | Verify code functionality |
| `http_request` | Make HTTP requests (GET, POST, PUT, DELETE) | Test APIs, fetch remote data |

### Phase 3: Advanced Development Tools

| Tool | Description | Use Case |
|------|-------------|----------|
| `lint_code` | Run code linters (eslint, pylint, flake8) | Check code quality and style |
| `format_code` | Auto-format code (prettier, black) | Maintain consistent code style |
| `list_directory` | List directory contents with details | Browse file system |
| `get_file_info` | Get file metadata (size, date, permissions, lines) | Inspect file properties |
| `build_project` | Run build commands with auto-detection | Compile and build projects |

### Browser Automation Tools (QA Testing)

Powered by [Playwright](https://playwright.dev/), these tools enable end-to-end testing and web automation. By default, the browser runs in headless mode (no visible window). To see the browser in action during testing, set `BROWSER_HEADLESS=false`.

| Tool | Description | Use Case |
|------|-------------|----------|
| `browser_navigate` | Navigate to a URL in headless browser | Open web pages for testing |
| `browser_screenshot` | Take screenshots of current page | Visual verification, bug reporting |
| `browser_click` | Click elements using CSS selectors | Interact with buttons, links |
| `browser_type` | Type text into input fields | Fill form inputs |
| `browser_get_text` | Extract text from elements | Verify page content |
| `browser_evaluate` | Execute JavaScript in browser context | Run custom scripts, get computed values |
| `browser_wait_for` | Wait for elements to appear/disappear | Handle dynamic content |
| `browser_fill_form` | Fill multiple form fields at once | Quick form submission |
| `browser_get_url` | Get current page URL | Verify navigation |
| `browser_go_back` | Navigate back in history | Test navigation flows |
| `browser_close` | Close browser and free resources | Clean up after testing |

**Installation Requirements:**
```bash
# Python
pip install playwright
playwright install chromium

# JavaScript
npm install playwright
npx playwright install chromium
```

### Security Features

All tools include built-in security measures:
- **File Access Control**: Prevents reading/writing sensitive files (`.env`, `.pem`, `.key`, credentials)
- **Command Filtering**: Blocks dangerous patterns (`rm -rf /`, `mkfs`, fork bombs)
- **Timeout Protection**: Commands and scripts have configurable timeouts
- **Output Limits**: Prevents overwhelming the LLM with excessive output
- **Path Validation**: Ensures file operations use safe, resolved paths

### Enabling Tools

Configure which tools are available using the `ALLOWED_TOOLS` environment variable:

```bash
# Enable specific tools (comma-separated)
export ALLOWED_TOOLS="web_search,calculator,read_file,write_file,bash_command"

# Enable all tools (omit the variable or leave empty)
export ALLOWED_TOOLS=""
```

Example for a full-featured coding agent with browser automation:
```bash
export ALLOWED_TOOLS="explore_project,read_file,write_file,edit_file,bash_command,bash_script,search_code,find_files,git_status,git_diff,git_add,git_commit,git_log,git_branch,search_and_replace,copy_file,move_file,delete_file,install_package,run_tests,http_request,lint_code,format_code,list_directory,get_file_info,build_project,browser_navigate,browser_screenshot,browser_click,browser_type,browser_get_text,browser_evaluate,browser_wait_for,browser_fill_form,browser_get_url,browser_go_back,browser_close,calculator"
```

Example for a read-only analysis agent:
```bash
export ALLOWED_TOOLS="explore_project,read_file,search_code,find_files,git_status,git_diff,git_log,list_directory,get_file_info"
```

Example for a QA testing agent:
```bash
export ALLOWED_TOOLS="read_file,find_files,run_tests,lint_code,format_code,git_status,git_diff,browser_navigate,browser_screenshot,browser_click,browser_type,browser_get_text,browser_evaluate,browser_wait_for,browser_fill_form,browser_get_url,browser_go_back,browser_close"
```

## Supported Providers

| Provider | Environment Variable | Example Models |
|----------|---------------------|----------------|
| OpenAI | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4-turbo` |
| Anthropic Claude | `ANTHROPIC_API_KEY` | `claude-3-opus-20240229`, `claude-3-sonnet-20240229` |
| Google Gemini | `GOOGLE_API_KEY` | `gemini-1.5-flash`, `gemini-1.5-pro` |
| Groq | `GROQ_API_KEY` | `llama3-8b-8192`, `mixtral-8x7b-32768` |
| xAI Grok | `XAI_API_KEY` | `grok-4`, `grok-2` |

## Quick Start

### Python Implementation

```bash
cd python
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment variables
export PROVIDER="groq"
export MODEL="llama3-8b-8192"
export GROQ_API_KEY="your-api-key"
export SYSTEM_PROMPT="../prompts/system_prompt.txt"

# Run the server
uvicorn agent:app --host 0.0.0.0 --port 8000
```

### JavaScript Implementation

```bash
cd js
npm install

# Configure environment variables
export PROVIDER="groq"
export MODEL="llama3-8b-8192"
export GROQ_API_KEY="your-api-key"
export SYSTEM_PROMPT="../prompts/system_prompt.txt"

# Run the server
npm start
```

## Configuration

Create a `.env` file in the `python/` or `js/` directory:

```env
PROVIDER=groq
MODEL=llama3-8b-8192
SYSTEM_PROMPT=../prompts/system_prompt.txt
ALLOWED_TOOLS=explore_project,read_file,write_file,bash_command,bash_script,calculator
GROQ_API_KEY=your-api-key-here
```

### Environment Variables

- **`PROVIDER`** (required): Provider name (`openai`, `claude`, `gemini`, `groq`, `xai`)
- **`MODEL`** (optional): Model identifier for the chosen provider
- **`SYSTEM_PROMPT`**: Either a file path to a prompt file or direct prompt text
- **`ALLOWED_TOOLS`** (optional): Comma-separated list of tools to enable (omit for all tools)
- **`BROWSER_HEADLESS`** (optional): Set to `false`, `0`, or `no` to run browser in headed mode (default: `true`)
- **`<PROVIDER>_API_KEY`** (required): API key for your chosen provider

## Docker Deployment

### Important: Prompts Directory Mounting

When running with Docker, you must mount the project's root `prompts` directory into the container. This allows the application to find the prompt file specified by the `SYSTEM_PROMPT` environment variable.

#### Python Docker

```bash
cd python

# Build the image (tag matches the one in the run command)
docker build -t llm-agent-python .

# Run with prompts mounted from project root
docker run -d -p 8000:8000 \
  -v $(pwd)/../prompts:/app/prompts \
  -e PROVIDER="groq" \
  -e MODEL="llama3-8b-8192" \
  -e SYSTEM_PROMPT="prompts/system_prompt.txt" \
  -e GROQ_API_KEY="your-api-key" \
  -e ALLOWED_TOOLS="calculator" \
  --name llm-agent-python \
  llm-agent-python
```

#### JavaScript Docker

```bash
cd js

# Build the image
docker build -t llm-agent-js .

# Run with prompts mounted from project root
docker run -d -p 8000:8000 \
  -v $(pwd)/../prompts:/app/prompts \
  -e PROVIDER="groq" \
  -e MODEL="llama3-8b-8192" \
  -e SYSTEM_PROMPT="prompts/system_prompt.txt" \
  -e GROQ_API_KEY="your-api-key" \
  --name llm-agent-js \
  llm-agent-js
```

**Note**: The `-v $(pwd)/../prompts:/app/prompts` flag mounts the project root's `prompts` directory into the container at `/app/prompts`. This allows you to update prompts without rebuilding the Docker image.

On Windows (PowerShell), use:
```powershell
-v ${PWD}/../prompts:/app/prompts
```

## API Usage

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "configured_provider": "groq",
  "configured_model": "llama3-8b-8192"
}
```

### Chat Endpoint

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello, how are you?"
  }'
```

Response:
```json
{
  "response": "I'm doing well, thank you! How can I help you today?",
  "updated_history": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    },
    {
      "role": "assistant",
      "content": "I'm doing well, thank you! How can I help you today?"
    }
  ]
}
```

### Chat with History

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What did I just ask you?",
    "history": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      },
      {
        "role": "assistant",
        "content": "I'\''m doing well, thank you!"
      }
    ]
  }'
```

## API Documentation

Once the server is running, visit:
- **Python**: http://localhost:8000/docs (Interactive Swagger UI)
- **JavaScript**: Use the endpoints documented above

## Tool Usage Examples

Here are some example prompts that demonstrate the coding tools in action:

### Exploring a Project
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explore the current project structure"
  }'
```

The agent will use `explore_project` to show the directory tree.

### Reading and Analyzing Code
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Read the agent.py file and explain what it does"
  }'
```

The agent will use `read_file` to access the file and provide an explanation.

### Creating New Files
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a new file called test.py with a hello world function"
  }'
```

The agent will use `write_file` to create the new file with appropriate content.

### Running Commands
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check the git status and list all Python files in the current directory"
  }'
```

The agent will use `bash_command` to execute the necessary commands.

### Complex Automation
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a bash script that backs up all Python files to a backup directory"
  }'
```

The agent will use `bash_script` to create and execute a multi-line script.

## Advanced Workflows

### Full Development Workflow Example

Complete workflow from exploring a project to committing changes:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "1. Explore the project structure, 2. Find all Python files with TODO comments, 3. Read one of them, 4. Fix the TODO, 5. Run tests, 6. If tests pass, commit the changes"
  }'
```

The agent will orchestrate multiple tools:
1. `explore_project` - Understand project layout
2. `search_code` - Find TODO comments
3. `read_file` - Read specific file
4. `edit_file` - Fix the TODO
5. `run_tests` - Verify changes work
6. `git_add` + `git_commit` - Save changes

### Refactoring Workflow

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Rename all instances of `oldFunctionName` to `newFunctionName` across the codebase, show me what would change first"
  }'
```

The agent will:
1. `search_and_replace` with `dry_run=true` - Preview changes
2. Show results to user
3. If approved, `search_and_replace` with `dry_run=false` - Apply changes
4. `run_tests` - Verify nothing broke
5. `git_diff` - Show changes
6. Optionally commit

### Code Quality Workflow

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Check code quality: lint all files, format them if needed, then run tests"
  }'
```

The agent will:
1. `find_files` - Get all code files
2. `lint_code` - Check for issues
3. `format_code` - Auto-fix formatting
4. `run_tests` - Ensure still working
5. Report results

### API Development Workflow

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a new REST endpoint for user management, add tests, and verify it works"
  }'
```

The agent will:
1. `search_code` - Find similar endpoints for reference
2. `write_file` - Create new endpoint file
3. `write_file` - Create test file
4. `run_tests` - Run the tests
5. `http_request` - Test the endpoint manually
6. `git_add` + `git_commit` - Commit if successful

### Browser Testing Workflow

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Test the login form at http://localhost:3000/login with username test@example.com and password testpass123, verify we land on the dashboard"
  }'
```

The agent will:
1. `browser_navigate` - Open the login page
2. `browser_screenshot` - Take before screenshot
3. `browser_fill_form` - Fill username and password
4. `browser_click` - Click login button
5. `browser_wait_for` - Wait for dashboard to load
6. `browser_get_url` - Verify correct URL
7. `browser_get_text` - Verify dashboard content
8. `browser_screenshot` - Take after screenshot
9. `browser_close` - Clean up

### E2E Testing Workflow

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Run an end-to-end test of the checkout flow: add product to cart, proceed to checkout, fill shipping info, and verify order confirmation"
  }'
```

The agent will orchestrate multiple browser actions:
1. `browser_navigate` - Open product page
2. `browser_click` - Add to cart
3. `browser_click` - Go to checkout
4. `browser_fill_form` - Fill shipping details
5. `browser_click` - Submit order
6. `browser_wait_for` - Wait for confirmation
7. `browser_get_text` - Verify order number
8. `browser_screenshot` - Capture proof
9. Report success/failure

### Visual Regression Testing

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Take screenshots of all main pages (home, about, products, contact) for visual regression testing"
  }'
```

The agent will:
1. `browser_navigate` to each page
2. `browser_screenshot` for each with descriptive names
3. Report all screenshot paths

## Tool Combinations

### Common Tool Patterns

**Search → Read → Edit → Test → Commit**
```
search_code → read_file → edit_file → run_tests → git_add → git_commit
```

**Find → Copy → Modify → Test**
```
find_files → copy_file → edit_file → run_tests
```

**Build → Test → Deploy**
```
install_package → build_project → run_tests → bash_command (deploy)
```

**Quality Check → Fix → Verify**
```
lint_code → format_code → run_tests → git_diff
```

## Tool Auto-Detection Features

Many tools automatically detect project settings:

- **`install_package`**: Detects npm, pip, or yarn based on project files
- **`run_tests`**: Detects pytest, jest, or npm test
- **`lint_code`**: Detects eslint, pylint, or flake8
- **`format_code`**: Detects prettier or black based on file type
- **`build_project`**: Detects npm, make, or python build commands

This makes the agent smarter and reduces the need for explicit configuration.

## Project Structure

```
.
├── prompts/              # System prompts (shared)
│   └── system_prompt.txt
├── python/               # Python implementation
│   ├── agent.py          # FastAPI server
│   ├── llm.py            # LLM provider abstraction
│   ├── tools.py          # Tool definitions and implementations
│   ├── requirements.txt
│   ├── Dockerfile
│   └── prompts/          # Python-specific prompts (if needed)
├── js/                   # JavaScript implementation
│   ├── agent.js          # Express server
│   ├── llm.js            # LLM provider abstraction
│   ├── tools.js          # Tool definitions and implementations
│   ├── package.json
│   ├── Dockerfile
│   └── prompts/          # JS-specific prompts (if needed)
└── response/             # Documentation
```

## Development

### Adding a New Tool

To create a custom tool for the agent:

#### Python (`python/tools.py`)

1. Create an async function that implements your tool:
```python
async def my_custom_tool(param1: str, param2: int = 10) -> str:
    """Tool implementation"""
    print(f"[Tool] Executing my_custom_tool")
    # Your tool logic here
    return "Tool result"
```

2. Add the tool to the `TOOLS` dictionary:
```python
"my_custom_tool": {
    "execute": my_custom_tool,
    "definition": {
        "type": "function",
        "function": {
            "name": "my_custom_tool",
            "description": "Description of what the tool does",
            "parameters": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Parameter description"},
                    "param2": {"type": "integer", "description": "Optional parameter"},
                },
                "required": ["param1"],
            },
        },
    },
},
```

#### JavaScript (`js/tools.js`)

1. Create an async function:
```javascript
async function my_custom_tool(param1, param2 = 10) {
    console.log(`[Tool] Executing my_custom_tool`);
    // Your tool logic here
    return "Tool result";
}
```

2. Add to the `TOOLS` object:
```javascript
my_custom_tool: {
    execute: my_custom_tool,
    definition: {
        type: "function",
        function: {
            name: "my_custom_tool",
            description: "Description of what the tool does",
            parameters: {
                type: "object",
                properties: {
                    param1: { type: "string", description: "Parameter description" },
                    param2: { type: "integer", description: "Optional parameter" },
                },
                required: ["param1"],
            },
        },
    },
},
```

### Adding a New Provider

1. Create a new provider class in `llm.py` or `llm.js` that extends the `LLM` base class
2. Implement the `chat_completion()` (Python) or `chatCompletion()` (JavaScript) method
3. Add API key resolution in the constructor
4. Register the provider in the `PROVIDERS` dictionary/object
5. Handle system prompt extraction if needed

See existing provider implementations for examples.

## Limitations

- **Conversation Storage**: Currently uses in-memory storage with a single default conversation ID. For production, implement persistent storage (Redis, database)
- **Gemini History**: The Gemini provider implementation has limited conversation history support

## License

This project is provided as-is for educational and development purposes.
