# Multi-Provider LLM Agent API

A conversational AI agent that provides a unified HTTP API for interacting with multiple LLM providers. Available in both Python and JavaScript implementations.

## Features

- **Multiple LLM Providers**: OpenAI, Anthropic Claude, Google Gemini, Groq, and xAI Grok
- **Unified API**: Single interface for all providers
- **Dual Implementation**: Choose between Python (FastAPI) or JavaScript (Express)
- **Configurable System Prompts**: Load prompts from files or environment variables
- **Docker Support**: Containerized deployment for both implementations
- **Conversation History**: Maintains context across multiple interactions

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
GROQ_API_KEY=your-api-key-here
```

### Environment Variables

- **`PROVIDER`** (required): Provider name (`openai`, `claude`, `gemini`, `groq`, `xai`)
- **`MODEL`** (optional): Model identifier for the chosen provider
- **`SYSTEM_PROMPT`**: Either a file path to a prompt file or direct prompt text
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
  # Mount the shared prompts directory from the project root into the container
  -v $(pwd)/../prompts:/app/prompts \
  -e PROVIDER="groq" \
  -e MODEL="llama3-8b-8192" \
  -e SYSTEM_PROMPT="prompts/system_prompt.txt" \
  -e GROQ_API_KEY="your-api-key" \
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

## Project Structure

```
.
├── prompts/              # System prompts (shared)
│   └── system_prompt.txt
├── python/               # Python implementation
│   ├── agent.py          # FastAPI server
│   ├── llm.py            # LLM provider abstraction
│   ├── requirements.txt
│   ├── Dockerfile
│   └── prompts/          # Python-specific prompts (if needed)
├── js/                   # JavaScript implementation
│   ├── agent.js          # Express server
│   ├── llm.js            # LLM provider abstraction
│   ├── package.json
│   ├── Dockerfile
│   └── prompts/          # JS-specific prompts (if needed)
└── response/             # Documentation
```

## Development

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
