# This file defines the tools that the LLM agent can use.

import asyncio
from math import sqrt

async def web_search(query: str) -> str:
    """
    A mock web search tool. In a real application, this would call a search API.
    """
    print(f"[Tool] Executing web_search with query: '{query}'")
    # In a real implementation, you would use an API like Google Search, Brave, etc.
    await asyncio.sleep(0.5) # Simulate network latency
    if "weather in london" in query.lower():
        return "The weather in London is cloudy with a high of 15°C."
    return f"Search results for '{query}' are not available in this mock implementation."

async def calculator(expression: str) -> str:
    """
    A calculator tool that can evaluate mathematical expressions.
    """
    print(f"[Tool] Executing calculator with expression: '{expression}'")
    try:
        # WARNING: Using eval is a security risk in a real production environment.
        # It's used here for simplicity. A safer library like 'numexpr' is recommended.
        # We'll add a simple whitelist of allowed functions for basic safety.
        allowed_names = {
            "sqrt": sqrt,
            "pi": 3.141592653589793,
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {e}"

# --- Tool Manifest ---
# This dictionary maps tool names to their implementation and definition for the LLM.

TOOLS = {
    "web_search": {
        "execute": web_search,
        # The definition must match the schema expected by the LLM provider.
        # This includes a 'type' and a nested 'function' object.
        "definition": {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Fetches real-time information from the internet using a search query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "The search query to execute."},
                    },
                    "required": ["query"],
                },
            },
        },
    },
    "calculator": {
        "execute": calculator,
        "definition": {
            "type": "function",
            "function": {
                "name": "calculator",
                "description": "Solves mathematical expressions and equations. Can handle advanced math.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string", "description": "The mathematical expression to evaluate (e.g., 'sqrt(529)', '12 * 4')."},
                    },
                    "required": ["expression"],
                },
            },
        },
    },
}

def get_tool_definitions():
    """Returns the definitions of all available tools."""
    return [tool["definition"] for tool in TOOLS.values()]