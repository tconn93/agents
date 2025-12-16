# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set environment variables to improve Python's behavior in Docker
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first to leverage Docker's layer caching.
# This layer is only rebuilt if requirements.txt changes.
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container
COPY agent.py .
COPY llm.py .
COPY tools.py .
COPY prompts/ ./prompts/

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run the application when the container starts
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8000"]