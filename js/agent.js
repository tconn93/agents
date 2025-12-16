import express from 'express';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { getLlm } from './llm.js';

// --- Configuration ---
dotenv.config();

const app = express();
const port = process.env.PORT || 8000;

const PROVIDER_NAME = process.env.PROVIDER;
const MODEL_NAME = process.env.MODEL;

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

// --- Middleware and In-memory Storage ---
app.use(express.json());
const conversations = {}; // In-memory conversation storage

// --- API Endpoints ---

app.post("/chat", async (req, res) => {
    const { message: userMessage, history: providedHistory = [] } = req.body;

    if (!userMessage) {
        return res.status(400).json({ error: "The 'message' field is required." });
    }

    const convId = "default"; // Simple conversation ID for this example
    const fullHistory = conversations[convId] || providedHistory;

    const messages = [];
    if (SYSTEM_PROMPT) {
        messages.push({ role: "system", content: SYSTEM_PROMPT });
    }
    messages.push(...fullHistory, { role: "user", content: userMessage });

    try {
        const responseText = await llmProvider.chatCompletion(
            messages,
            0.7, // temperature
            1024  // max_tokens
        );

        // Update and save history
        fullHistory.push({ role: "user", content: userMessage });
        fullHistory.push({ role: "assistant", content: responseText });
        conversations[convId] = fullHistory;

        res.json({
            response: responseText,
            updated_history: fullHistory,
        });
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