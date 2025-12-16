# Use an official Node.js runtime as a parent image
FROM node:20-slim

# Set the working directory in the container
WORKDIR /app

# Copy package.json and install dependencies first to leverage Docker's layer caching.
# This layer is only rebuilt if package.json changes.
COPY package.json .
RUN npm install --production

# Copy the rest of the application's code into the container.
# This includes the prompt file which the agent can load at runtime.
COPY agent.js .
COPY llm.js .
COPY tools.js . 
COPY prompts/ ./prompts/

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Define the command to run the application when the container starts
CMD ["npm", "start"]