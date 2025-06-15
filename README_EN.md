# AI Chatbot POC

This project is a Proof of Concept (POC) for an AI Chatbot, designed to explore AI-driven customer interaction capabilities.

## Project Demo Video

[Watch the project demo on Google Drive](https://drive.google.com/file/d/18DCeBR8PjrrkV49d4PGPJWCods91131I/view?usp=sharing)

## Related Documents

- [Design Document](DESIGN_DOCUMENT.md)
- [Code Review](CODE_REVIEW.md)

## Objective

The POC aims to demonstrate:

1.  A text-based chat interface.
2.  RAG-FAQ functionality (using a predefined set of FAQs).
3.  One After-Service flow: Changing booking time ("đổi giờ").
4.  A codebase structure that is ready to incorporate image and voice processing (though not implemented in detail).
5.  Basic instructions for running and testing.

## Tech Stack

- **Backend:** Python (FastAPI)
- **AI Core:** Google Vertex AI (Gemini 2.5 Pro Preview - model `gemini-2.5-pro-preview-05-06`)
- **Frontend:** HTML, CSS, JavaScript
- **FAQ Data:** JSON file (used by a local tool called by the AI)

## Backend Design and Flow

The backend is built using FastAPI and is structured into several modules to handle different aspects of the chatbot's functionality.

### Core Modules and Their Responsibilities

| File                       | Responsibility                                                                                                                                          | Key Interactions                                                                                                                                |
| :------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| `app/main.py`              | Main FastAPI application. Defines API endpoints (e.g., `/chat`), manages CORS, orchestrates the chat flow, handles conversation history and tool state. | Imports and uses `ai_manager` (from `ai_agents_manager.py`), `tools.py` functions, and `models.py` schemas.                                     |
| `app/ai_agents_manager.py` | Acts as a factory or manager for different LLM agent implementations. Allows switching LLM providers. Provides a unified interface to the active agent. | Instantiates `VertexAIAgent` (from `vertex_agent.py`). Called by `main.py` to get agent responses.                                              |
| `app/vertex_agent.py`      | Implements the specific logic for interacting with Google Vertex AI Gemini models. Defines tool schemas for the LLM. Handles API calls to Gemini.       | Uses `vertexai` SDK. Defines `FunctionDeclaration` for tools. Called by `AIAgentsManager`.                                                      |
| `app/tools.py`             | Contains the Python implementations of the tools (functions) that the LLM can request to call (e.g., FAQ lookup, booking changes).                      | Functions are called by `main.py` based on LLM requests. `get_faq_answer` uses `faq_data.json`. `confirm_booking_time_change` calls a mock API. |
| `app/models.py`            | Defines Pydantic data models (schemas) for API request and response validation and serialization (e.g., `ChatMessageInput`, `ChatMessageOutput`).       | Used by `main.py` for FastAPI endpoint request/response handling.                                                                               |
| `app/faq_data.json`        | A JSON file containing predefined frequently asked questions, answers, and keywords.                                                                    | Loaded and used by the `get_faq_answer` tool in `tools.py`.                                                                                     |

### Overall Chat Flow

The typical flow for a user interaction is as follows:

1.  **User Input:** The Frontend sends a user's message (along with `user_id` and optional `session_state`) to the `/chat` endpoint in `main.py`.
2.  **Request to AI Manager:** `main.py` retrieves the conversation history for the user and passes the history and new message to `ai_agents_manager.ai_manager.get_agent_response()`.
3.  **Agent Processing:** `AIAgentsManager` routes the request to the active agent, which is `vertex_agent.VertexAIAgent`.
4.  **LLM Call (1st Pass):** `VertexAIAgent` constructs a prompt for the Gemini model, including the conversation history, the user's message, and the configuration of available tools (defined in `vertex_agent.py`). It then calls the Gemini API.
5.  **LLM Response Analysis:**
    - **Direct Answer:** If Gemini provides a direct text answer, this is passed back through `VertexAIAgent` and `AIAgentsManager` to `main.py`.
    - **Function Call Request:** If Gemini determines a tool should be used, it responds with a "function call" request, specifying the tool name and arguments. This is also passed back to `main.py`.
6.  **Tool Execution (if requested):**
    - `main.py` identifies the requested tool and its arguments.
    - It looks up the corresponding Python function in `tools.py` and executes it.
    - The result from the tool function is captured.
    - `main.py` updates the conversation history with the user's message, the model's function call request, and the tool's execution result.
7.  **LLM Call (2nd Pass - if a tool was executed):**
    - `main.py` sends the updated history (now including the tool result) back to the Gemini model via `AIAgentsManager` and `VertexAIAgent`. A generic prompt like "Based on the tool's output, what should I say to the user?" is often used.
    - Gemini generates a natural language response based on the tool's output.
8.  **Response to User:** The final text response (either from step 5a or step 7) is sent back to the Frontend by `main.py`, along with any updated session state.
9.  **State Update:** `main.py` saves the updated conversation history and any relevant tool flow state for the user.

### Visual Flow (Mermaid Diagram)

![Backend Flow Diagram](backend_flow_diagram.png)

## Project Structure

```
vexere_chatbot_poc/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI application, chat endpoint, mock Vexere APIs
│   │   ├── ai_agents_manager.py # Manages different LLM agent implementations
│   │   ├── vertex_agent.py # Specific agent for Vertex AI Gemini
│   │   ├── tools.py        # Agent tools (FAQ, change booking)
│   │   ├── models.py       # Pydantic models for request/response
│   │   └── faq_data.json   # Mock FAQ data
│   ├── tests/              # Unit and integration tests (e.g., test_ai_agent.py)
│   ├── requirements.txt    # Python dependencies
│   └── .gitignore
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
├── gemini_api_caller.py    # Standalone script for testing direct Gemini API calls
└── README.md
```

## Setup and Running

### Prerequisites

- Python 3.8+
- `uv` (for installing Python packages: `pip install uv`)
- **Google Cloud SDK (gcloud CLI)** installed and configured.
- **Application Default Credentials (ADC)** set up for Google Cloud. You can typically do this by running:
  ```bash
  gcloud auth application-default login
  ```
- A Google Cloud Project with the **Vertex AI API enabled**.
  The Project ID (`singular-ray-456411-t7`), Location (`us-central1`), and Model Name (`gemini-2.5-pro-preview-05-06`) are configured in `backend/app/vertex_agent.py`.

### Backend

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd chatbot_customer_service_poc # Or your project root (example name)
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install dependencies using uv (from the project root):**

    ```bash
    uv pip install -r backend/requirements.txt
    ```

4.  **Run the FastAPI server (from the project root):**
    ```bash
    uvicorn backend.app.main:app --reload --port 8000 --app-dir .
    ```
    The backend server will be running at `http://localhost:8000`. Ensure your Google Cloud credentials are set up correctly for Vertex AI to function.

### Frontend

1.  Open the `frontend/index.html` file in your web browser.

## How to Use

1.  Once the backend is running and `frontend/index.html` is open in the browser, you can type messages into the chat interface.
2.  **Try asking an FAQ:**
    - "How do I cancel my ticket?"
    - "What payment methods are accepted?"
3.  **Try the "change booking time" flow:**
    - Type: "I want to change my booking time" or "đổi giờ vé"
    - The bot will ask for your booking ID. (e.g., `VX123`)
    - Then, it will ask for the new desired time. (e.g., `2025-12-25 14:30:00`)
    - The bot will then confirm if the mock change was successful.

## Notes on the POC

- **LLM Integration:** This POC integrates with Google Vertex AI using the Gemini model specified in `backend/app/vertex_agent.py`. The agent logic and orchestration handle interactions with the LLM, including tool/function calling.
- **RAG for FAQ:** The `get_faq_answer` tool is called by the LLM. This tool uses keyword matching on the `faq_data.json` file. A full RAG setup with a vector database is outside the scope of this POC but would be the next step for production.
- **State Management:**
  - Conversation history for Gemini (as `List[Content]`) is managed in `main.py`.
  - Explicit state for multi-turn tool flows (like `change_booking`) is managed using `active_tool_states` in `main.py`.
- **Error Handling:** Basic error handling is in place. Production systems would require more robust mechanisms.
- **Security:** Standard security considerations for APIs and LLM interactions would need to be addressed for production.
- **Image/Voice:** Placeholder functions in `tools.py` exist, but are not integrated into the LLM flow.
- **Testing:** `backend/tests/test_ai_agent.py` provides examples of integration tests for the AI agent flow. More comprehensive testing would be needed for production.
- **Cost:** Using Vertex AI will incur costs based on model usage. Be mindful of this.

# AI Chatbot POC (Original English Readme)

This file is the original English version of the README. The primary README.md is now in Vietnamese.
