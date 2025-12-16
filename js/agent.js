import express from 'express';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { getLlm } from './llm.js';
import { getFilteredTools, getToolDefinitions } from './tools.js';

// --- Configuration ---
dotenv.config();

const app = express();
const port = process.env.PORT || 8000;

const PROVIDER_NAME = process.env.PROVIDER;
const MODEL_NAME = process.env.MODEL;

const ALLOWED_TOOLS_CSV = process.env.ALLOWED_TOOLS;
const ALLOWED_TOOLS_LIST = ALLOWED_TOOLS_CSV ? ALLOWED_TOOLS_CSV.split(',') : null;

function loadSystemPrompt(promptEnvVar) {
    const defaultPrompt = "You are a helpful AI assistant.";
    if (!promptEnvVar) {
        return defaultPrompt;
    }
    if (fs.existsSync(promptEnvVar)) {
        try {
            return fs.readFileSync(promptEnvVar, 'utf-8').trim();
        } catch (e) {
            console.warn(`Could not read system prompt file '${promptEnvVar}'. Error: ${e}. Using default.`);
            return defaultPrompt;
        }
    }
    return promptEnvVar;
}

const SYSTEM_PROMPT = loadSystemPrompt(process.env.SYSTEM_PROMPT);

if (!PROVIDER_NAME) {
    throw new Error("PROVIDER must be set in the environment or .env file.");
}

// --- LLM Provider Initialization ---
let llmProvider;
try {
    llmProvider = getLlm(PROVIDER_NAME, { model: MODEL_NAME });
    console.log(`Successfully initialized LLM provider: ${PROVIDER_NAME} with model: ${llmProvider.model}`);
} catch (e) {
    console.error("Failed to initialize LLM provider on startup.", e);
    process.exit(1);
}

// Filter tools based on environment configuration
const AVAILABLE_TOOLS = getFilteredTools(ALLOWED_TOOLS_LIST);
console.log(`Agent initialized with tools: ${Object.keys(AVAILABLE_TOOLS)}`);

// --- Middleware and In-memory Storage ---
app.use(express.json());
const conversations = {}; // In-memory conversation storage

// --- API Endpoints ---

app.post("/chat", async (req, res) => {
    const { message: userMessage, history: providedHistory = [] } = req.body;
    const MAX_TOOL_CALLS = 5; // Safety to prevent infinite loops

    if (!userMessage) {
        return res.status(400).json({ error: "The 'message' field is required." });
    }

    // Start building the message history for the LLM
    const messages = [
        { role: "system", content: SYSTEM_PROMPT },
        ...providedHistory,
        { role: "user", content: userMessage }
    ];

    try {
        let toolCallCount = 0;
        while (toolCallCount < MAX_TOOL_CALLS) {
            const response = await llmProvider.chatCompletion({
                messages,
                tools: getToolDefinitions(AVAILABLE_TOOLS), // Provide the list of allowed tools to the LLM
                temperature: 0.7,
                max_tokens: 1024,
            });

            const responseMessage = response.choices[0].message;

            // Check if the LLM wants to call a tool
            if (responseMessage.tool_calls && responseMessage.tool_calls.length > 0) {
                console.log("[Agent] LLM requested tool call(s):", responseMessage.tool_calls);
                messages.push(responseMessage); // Add LLM's tool request to history

                // Execute all requested tools in parallel
                const toolPromises = responseMessage.tool_calls.map(async (toolCall) => {
                    const toolName = toolCall.function.name;
                    const tool = AVAILABLE_TOOLS[toolName];

                    if (!tool) {
                        // This is a safeguard in case the LLM hallucinates a tool name
                        console.warn(`LLM attempted to use unavailable tool: ${toolName}`);
                    }

                    if (!tool) {
                        return {
                            tool_call_id: toolCall.id,
                            role: "tool",
                            name: toolName,
                            content: `Error: Tool "${toolName}" not found.`,
                        };
                    }

                    const args = JSON.parse(toolCall.function.arguments);
                    const toolResult = await tool.execute(...Object.values(args));

                    return {
                        tool_call_id: toolCall.id,
                        role: "tool",
                        name: toolName,
                        content: toolResult,
                    };
                });

                const toolResults = await Promise.all(toolPromises);
                messages.push(...toolResults); // Add tool results to history
                toolCallCount++; // Continue the loop to let the LLM synthesize the results

            } else {
                // No tool call, so this is the final answer
                const responseText = responseMessage.content;
                
                // Update and save history
                const updatedHistory = [...providedHistory, { role: "user", content: userMessage }, { role: "assistant", content: responseText }];
                conversations["default"] = updatedHistory; // Using a simple default conversation ID

                return res.json({
                    response: responseText,
                    updated_history: updatedHistory,
                });
            }
        }
        // If the loop exits, we've hit the tool call limit
        res.status(500).json({ error: "Exceeded maximum number of tool calls." });

    } catch (e) {
        console.error("LLM API error:", e);
        res.status(500).json({ error: `LLM API error: ${e.message}` });
    }
});

app.get("/health", (req, res) => {
    res.json({
        status: "healthy",
        configured_provider: PROVIDER_NAME,
        configured_model: llmProvider.model,
    });
});

// --- Server Start ---
app.listen(port, () => {
    console.log(`Server is running on http://localhost:${port}`);
});