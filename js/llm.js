import OpenAI from 'openai';
import Anthropic from '@anthropic-ai/sdk';
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai';
import Groq from 'groq-sdk';

/**
 * Abstract Base Class for a Large Language Model provider.
 * It defines the interface for interacting with different LLM APIs.
 */
class LLM {
    constructor(apiKey, model) {
        if (this.constructor === LLM) {
            throw new Error("LLM is an abstract class and cannot be instantiated directly.");
        }
        this.apiKey = apiKey;
        this.model = model;
    }

    async chatCompletion(options) {
        throw new Error("Method 'chatCompletion()' must be implemented.");
    }
}

export class OpenAIProvider extends LLM {
    constructor(apiKey = null, model = 'gpt-4o') {
        const resolvedApiKey = apiKey || process.env.OPENAI_API_KEY;
        if (!resolvedApiKey) {
            throw new Error("OPENAI_API_KEY must be provided or set as an environment variable.");
        }
        super(resolvedApiKey, model);
        this.client = new OpenAI({ apiKey: this.apiKey });
    }

    async chatCompletion({ messages, temperature, maxTokens, ...kwargs }) {
        console.log(`Calling OpenAI API with model: ${this.model}`);
        const completion = await this.client.chat.completions.create({
            model: this.model,
            messages,
            temperature,
            max_tokens: maxTokens,
            ...kwargs,
        });
        // Normalize the response to match the Gemini/Claude format.
        return {
            choices: [{ message: { role: 'assistant', content: completion.choices[0].message.content } }]
        };
    }
}

export class XAIProvider extends LLM {
    constructor(apiKey = null, model = 'grok-4') {
        const resolvedApiKey = apiKey || process.env.XAI_API_KEY;
        if (!resolvedApiKey) {
            throw new Error("XAI_API_KEY must be provided or set as an environment variable.");
        }
        super(resolvedApiKey, model);
        this.client = new OpenAI({
            apiKey: this.apiKey,
            baseURL: 'https://api.x.ai/v1',
        });
    }

    async chatCompletion({ messages, temperature, maxTokens, ...kwargs }) {
        console.log(`Calling xAI (Grok) API with model: ${this.model}`);
        const completion = await this.client.chat.completions.create({
            model: this.model,
            messages,
            temperature,
            max_tokens: maxTokens,
            ...kwargs,
        });
        // Normalize the response to match the Gemini/Claude format.
        return completion;
    }
}

export class GroqProvider extends LLM {
    constructor(apiKey = null, model = 'llama3-8b-8192') {
        const resolvedApiKey = apiKey || process.env.GROQ_API_KEY;
        if (!resolvedApiKey) {
            throw new Error("GROQ_API_KEY must be provided or set as an environment variable.");
        }
        super(resolvedApiKey, model);
        this.client = new Groq({ apiKey: this.apiKey });
    }

    async chatCompletion({ messages, temperature, maxTokens, ...kwargs }) {
        console.log(`Calling Groq API with model: ${this.model}`);
        const completion = await this.client.chat.completions.create({
            model: this.model,
            messages,
            temperature,
            max_tokens: maxTokens,
            ...kwargs,
        });
        // Normalize the response to match the Gemini/Claude format.
        return {
            choices: [{ message: { role: 'assistant', content: completion.choices[0].message.content } }]
        };
    }
}

export class ClaudeProvider extends LLM {
    constructor(apiKey = null, model = 'claude-3-opus-20240229') {
        const resolvedApiKey = apiKey || process.env.ANTHROPIC_API_KEY;
        if (!resolvedApiKey) {
            throw new Error("ANTHROPIC_API_KEY must be provided or set as an environment variable.");
        }
        super(resolvedApiKey, model);
        this.client = new Anthropic({ apiKey: this.apiKey });
    }

    async chatCompletion({ messages, temperature, maxTokens, ...kwargs }) {
        console.log(`Calling Anthropic (Claude) API with model: ${this.model}`);
        let systemPrompt = '';
        if (messages.length > 0 && messages[0].role === 'system') {
            systemPrompt = messages.shift().content;
        }

        const completion = await this.client.messages.create({
            model: this.model,
            system: systemPrompt,
            messages: messages,
            temperature,
            max_tokens: maxTokens,
            ...kwargs,
        });
        // Anthropic's response structure is different. We normalize it to look like OpenAI's.
        return {
            choices: [{ message: { role: 'assistant', content: completion.content[0].text } }]
        };
    }
}

export class GeminiProvider extends LLM {
    constructor(apiKey = null, model = 'gemini-1.5-flash') {
        const resolvedApiKey = apiKey || process.env.GOOGLE_API_KEY;
        if (!resolvedApiKey) {
            throw new Error("GOOGLE_API_KEY must be provided or set as an environment variable.");
        }
        super(resolvedApiKey, model);
        this.genAI = new GoogleGenerativeAI(this.apiKey);
    }

    async chatCompletion({ messages, temperature, maxTokens, ...kwargs }) {
        console.log(`Calling Google (Gemini) API with model: ${this.model}`);
        let systemPrompt = '';
        if (messages.length > 0 && messages[0].role === 'system') {
            systemPrompt = messages.shift().content;
        }

        const model = this.genAI.getGenerativeModel({
            model: this.model,
            systemInstruction: systemPrompt,
        });

        // Gemini requires a specific format for history.
        // For simplicity, we'll just use the last user message.
        // A more robust implementation would convert the full history.
        const userPrompt = messages[messages.length - 1].content;

        const result = await model.generateContent(userPrompt, {
            temperature,
            maxOutputTokens: maxTokens,
        });
        const response = await result.response;
        // Gemini's response structure is different. We normalize it to look like OpenAI's.
        return {
            choices: [{ message: { role: 'assistant', content: response.text() } }]
        };
    }
}

const PROVIDERS = {
    openai: OpenAIProvider,
    xai: XAIProvider,
    groq: GroqProvider,
    claude: ClaudeProvider,
    gemini: GeminiProvider,
};

export function getLlm(providerName, options = {}) {
    const ProviderClass = PROVIDERS[providerName.toLowerCase()];
    if (!ProviderClass) {
        throw new Error(`Unknown LLM provider: '${providerName}'. Available: ${Object.keys(PROVIDERS).join(', ')}`);
    }
    return new ProviderClass(options.apiKey, options.model);
}