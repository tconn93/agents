import os
import json
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

from llm import get_llm
from tools import get_filtered_tools, get_tool_definitions

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---

PROVIDER_NAME = os.getenv("PROVIDER")
MODEL_NAME = os.getenv("MODEL")

ALLOWED_TOOLS_CSV = os.getenv("ALLOWED_TOOLS")
ALLOWED_TOOLS_LIST = ALLOWED_TOOLS_CSV.split(',') if ALLOWED_TOOLS_CSV else None
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", 5))


def load_system_prompt(prompt_env_var: str) -> str:
    default_prompt = "You are a helpful AI assistant."
    if not prompt_env_var:
        return default_prompt
    if os.path.exists(prompt_env_var):
        try:
            with open(prompt_env_var, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Warning: Could not read system prompt file '{prompt_env_var}'. Error: {e}. Using default.")
            return default_prompt
    return prompt_env_var

SYSTEM_PROMPT = load_system_prompt(os.getenv("SYSTEM_PROMPT"))

if not PROVIDER_NAME:
    raise ValueError("PROVIDER must be set in the environment or .env file.")

# --- FastAPI App and Models ---

app = FastAPI(
    title="Multi-Provider LLM Agent API",
    description="A conversational AI agent with tool-use capabilities.",
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = Field(default_factory=list)

class ChatResponse(BaseModel):
    response: str
    updated_history: List[ChatMessage]

# --- LLM Initialization and Storage ---

llm_provider = get_llm(PROVIDER_NAME, model=MODEL_NAME)
print(f"Successfully initialized LLM provider: {PROVIDER_NAME} with model: {llm_provider.model}")

# Filter tools based on environment configuration
AVAILABLE_TOOLS = get_filtered_tools(ALLOWED_TOOLS_LIST)
print(f"Agent initialized with tools: {list(AVAILABLE_TOOLS.keys())}")

conversations: Dict[str, List[Dict[str, Any]]] = {} # In-memory storage

# --- API Endpoints ---

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *[msg.dict() for msg in request.history],
        {"role": "user", "content": request.message},
    ]

    try:
        for _ in range(MAX_TOOL_CALLS):
            response = await llm_provider.chat_completion(
                messages=messages,
                tools=get_tool_definitions(AVAILABLE_TOOLS),
                temperature=0.7,
                max_tokens=1024,
            )
            print(response)
            response_message = response['choices'][0]['message']
            if response_message['content']:
                messages.append(response_message) # Add LLM response to history

            if response_message.get("tool_calls"):
                print(f"[Agent] LLM requested tool call(s): {response_message['tool_calls']}")
                tool_calls = response_message["tool_calls"]
                tool_tasks = []
                for tool_call in tool_calls:
                    tool_name = tool_call['function']['name']
                    if tool_name not in AVAILABLE_TOOLS:
                        # This is a safeguard in case the LLM hallucinates a tool name
                        raise HTTPException(status_code=400, detail=f"Attempted to use unavailable tool: {tool_name}")
                    tool_to_call = AVAILABLE_TOOLS[tool_name]['execute']
                    tool_args = json.loads(tool_call['function']['arguments'])
                    tool_tasks.append(tool_to_call(**tool_args))
                
                tool_outputs = await asyncio.gather(*tool_tasks)

                for i, tool_call in enumerate(tool_calls):
                    messages.append({
                        "tool_call_id": tool_call['id'],
                        "role": "tool",
                        "name": tool_call['function']['name'],
                        "content": tool_outputs[i],
                    })
            else:
                final_response = response_message['content']
                updated_history = [msg for msg in messages if msg['role'] != 'system']
                conversations["default"] = updated_history
                return ChatResponse(response=final_response, updated_history=updated_history)

        raise HTTPException(status_code=500, detail="Exceeded maximum number of tool calls.")

    except Exception as e:
        print(f"LLM API error: {e}")
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "configured_provider": PROVIDER_NAME,
        "configured_model": llm_provider.model,
    }

if __name__ == "__main__":
    import uvicorn
    # This allows you to run the app directly with `python agent.py`
    uvicorn.run(app, host="0.0.0.0", port=8000)