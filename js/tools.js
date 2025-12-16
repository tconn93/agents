/**
 * This file defines the tools that the LLM agent can use.
 * Each tool has a `definition` for the LLM and an `execute` function for the agent.
 */

import { evaluate } from 'mathjs';

/**
 * A mock web search tool. In a real application, this would call a search API.
 * @param {string} query The search query.
 * @returns {Promise<string>} A mock search result.
 */
async function web_search(query) {
    console.log(`[Tool] Executing web_search with query: "${query}"`);
    // In a real implementation, you would use an API like Google Search, Brave, etc.
    if (query.toLowerCase().includes("weather in london")) {
        return "The weather in London is cloudy with a high of 15°C.";
    }
    return `Search results for "${query}" are not available in this mock implementation.`;
}

/**
 * A calculator tool using the mathjs library.
 * @param {string} expression The mathematical expression to evaluate.
 * @returns {Promise<string>} The result of the calculation.
 */
async function calculator(expression) {
    console.log(`[Tool] Executing calculator with expression: "${expression}"`);
    try {
        const result = evaluate(expression);
        return result.toString();
    } catch (e) {
        return `Error evaluating expression: ${e.message}`;
    }
}

// --- Tool Manifest ---
// This object maps tool names to their implementation and definition for the LLM.
export const TOOLS = {
    web_search: {
        // The `execute` function is what our agent will run.
        execute: web_search,
        // The `definition` must match the schema expected by the LLM provider.
        // This includes a 'type' and a nested 'function' object.
        definition: {
            "type": "function",
            "function": {
                name: "web_search",
                description: "Fetches real-time information from the internet using a search query.",
                parameters: {
                    type: "object",
                    properties: {
                        query: { type: "string", description: "The search query to execute." },
                    },
                    required: ["query"],
                },
            },
        },
    },
    calculator: {
        execute: calculator,
        definition: {
            "type": "function",
            "function": {
                name: "calculator",
                description: "Solves mathematical expressions and equations. Can handle advanced math.",
                parameters: {
                    type: "object",
                    properties: {
                        expression: { type: "string", description: "The mathematical expression to evaluate (e.g., 'sqrt(529)', '12 * 4')." },
                    },
                    required: ["expression"],
                },
            },
        },
    },
};

/**
 * Returns the definitions of all available tools.
 * @returns {Array<Object>} A list of tool definitions for the LLM.
 */
export function getToolDefinitions() {
    return Object.values(TOOLS).map(tool => tool.definition);
}