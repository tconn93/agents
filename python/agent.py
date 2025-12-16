from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import logging
import os
import uvicorn
import uuid
from dotenv import load_dotenv

from llm import get_llm, LLM, PROVIDERS

load_dotenv()  # Load .env file if you have one

# --- Structured Logging Configuration ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Multi-Provider LLM Agent API",
    description="A conversational AI agent that supports multiple LLM providers.",
    version="1.1.0"
)

# --- Application Configuration ---

PROVIDER_NAME = os.getenv("PROVIDER")
MODEL_NAME = os.getenv("MODEL")

def load_system_prompt(prompt_env_var: Optional[str]) -> str:
    """Loads the system prompt from a file path or directly from the env var."""
    default_prompt = "You are a helpful AI assistant."
    if not prompt_env_var:
        return default_prompt
    
    # Check if the value is a path to an existing file
    if os.path.isfile(prompt_env_var):
        try:
            with open(prompt_env_var, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Could not read system prompt file '{prompt_env_var}'. Error: {e}. Using default.")
            return default_prompt
    return prompt_env_var # Use the value directly if it's not a file path

SYSTEM_PROMPT = load_system_prompt(os.getenv("SYSTEM_PROMPT"))

if not PROVIDER_NAME:
    raise ValueError("PROVIDER must be set in the environment or .env file.")

# Instantiate the LLM provider once at startup
try:
    llm_provider: LLM = get_llm(provider_name=PROVIDER_NAME, model=MODEL_NAME)
except ValueError as e:
    logger.critical("Failed to initialize LLM provider on startup.", exc_info=True)
    # Catch configuration errors on startup for immediate feedback
    raise e

# --- Pydantic Models ---

class Message(BaseModel):
    role: str  # "user", "assistant", or "system"
    content: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Message]] = None

class ChatResponse(BaseModel):
    response: str
    updated_history: List[Message]

# In-memory conversation storage (use Redis/DB for production)
conversations: Dict[str, List[Message]] = {}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    provided_history = request.history or []
    request_id = str(uuid.uuid4())

    logger.info(f"Received chat request.", extra={"request_id": request_id, "history_len": len(provided_history)})
    
    # Simple conversation ID for this example
    conv_id = "default"
    
    # Load existing history or start new
    full_history = conversations.get(conv_id, provided_history)
    
    # Build the message list for the LLM
    messages = []
    if SYSTEM_PROMPT:
        messages.append({"role": "system", "content": SYSTEM_PROMPT})
    messages.extend([msg.dict() for msg in full_history])
    messages.append({"role": "user", "content": user_message})
    
    logger.debug(f"Sending {len(messages)} messages to LLM.", extra={"request_id": request_id})
    try:
        # Call the chat_completion method on the pre-configured provider
        response_text = await llm_provider.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )

    except ValueError as e:
        logger.error(f"Validation error during LLM call.", extra={"request_id": request_id}, exc_info=True)
        # This can still catch validation errors from the provider's client library
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # This catches API errors from the provider's client
        logger.error(f"LLM API error.", extra={"request_id": request_id}, exc_info=True)
        raise HTTPException(status_code=500, detail=f"LLM API error: {str(e)}")
    
    # Update history
    full_history.append(Message(role="user", content=user_message))
    full_history.append(Message(role="assistant", content=response_text))
    
    # Save updated history
    conversations[conv_id] = full_history
    
    logger.info("Successfully processed chat request.", extra={"request_id": request_id})
    
    return ChatResponse(
        response=response_text,
        updated_history=full_history
    )

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "configured_provider": PROVIDER_NAME,
        "configured_model": llm_provider.model # Get the actual model name from the instance
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)