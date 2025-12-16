# How to Build and Run the Application with Docker

This guide explains how to build a Docker image for the Python LLM agent and run it as a container. Containerizing the application ensures a consistent and isolated environment, making deployment simple and reliable.

## Prerequisites

- [Docker](https://www.docker.com/get-started) must be installed and running on your system.

## Overview

The project includes two key files for Dockerization in the `python/` directory:

- `Dockerfile`: A script that contains all the commands to assemble a container image. It installs dependencies, copies the application code, and sets the runtime command.
- `.dockerignore`: A file that lists files and directories to exclude from the image. This keeps the image lightweight and secure by omitting virtual environments, local `.env` files, and other unnecessary artifacts.

---

## Step 1: Build the Docker Image

First, you need to build the Docker image from the `Dockerfile`. This process packages your application and its dependencies into a single, portable image.

1.  Navigate to the `python` directory in your terminal:
    ```bash
    cd /path/to/your/project/python
    ```

2.  Run the `docker build` command:
    ```bash
    docker build -t llm-agent .
    ```
    - `docker build`: The command to build an image.
    - `-t llm-agent`: This "tags" (names) your image `llm-agent` for easy reference.
    - `.`: Specifies that the build context (the `Dockerfile` and application files) is the current directory.

## Step 2: Run the Docker Container

Once the image is built, you can run it as a container. The application is configured using environment variables, which must be passed to the container at runtime.

The following environment variables are required:

- `PROVIDER`: The name of the LLM provider (e.g., `groq`, `openai`, `xai`).
- `MODEL`: The specific model to use (e.g., `llama3-8b-8192`).
- `SYSTEM_PROMPT`: The path to the prompt file inside the container (e.g., `prompts/system_prompt.txt`).
- `<PROVIDER>_API_KEY`: The API key for your chosen provider (e.g., `GROQ_API_KEY`).

### Example `docker run` command:

This example runs the agent using the `groq` provider.

```bash
docker run -d -p 8000:8000 \
  -e PROVIDER="groq" \
  -e MODEL="llama3-8b-8192" \
  -e SYSTEM_PROMPT="prompts/system_prompt.txt" \
  -e GROQ_API_KEY="your-groq-api-key-here" \
  --name my-llm-agent \
  llm-agent
```

- `-d`: Runs the container in detached mode (in the background).
- `-p 8000:8000`: Maps port 8000 on your local machine to port 8000 inside the container.
- `-e`: Sets an environment variable.
- `--name my-llm-agent`: Assigns a convenient name to your running container.

## Step 3: Interact with the API

Your containerized LLM agent is now running and accessible!

- **Interactive Docs**: Open your browser to `http://localhost:8000/docs`.
- **Health Check**: Visit `http://localhost:8000/health` to see the configured provider and model.