# Example Configuration for Vertex AI
# Copy this file to config.py and fill in your actual values.
# DO NOT commit config.py to version control if it contains sensitive information.

PROJECT_ID = "your-gcp-project-id"
LOCATION = "your-gcp-region"  # e.g., "us-central1"
MODEL_NAME = "gemini-2.5-pro-preview-05-06"  # Or your desired model

# Base URL for the mock Vexere API
# This should point to where your main.py (which hosts the mock endpoint) is running.
MOCK_API_BASE_URL = "http://localhost:8000"

# Active LLM Provider Configuration
# Valid values: "VERTEX_AI", "OPENAI", "ANTHROPIC" (when other agents are implemented)
# For the POC, this should typically be "VERTEX_AI".
ACTIVE_LLM_PROVIDER = "VERTEX_AI"

# Add other configurations here as needed
