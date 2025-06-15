from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import re
import json  # For serializing tool results for Gemini
from typing import List, Dict, Any, Callable, Coroutine

# Vertex AI and Google Cloud specific imports
from vertexai.generative_models import (
    Content,
    Part,
)  # Use these for constructing history

# Project-specific imports
from .models import (
    ChatMessageInput,
    ChatMessageOutput,
    ChangeBookingTimePayload,
    MockVexereApiResponse,
)
from . import tools
from .ai_agents_manager import ai_manager  # Import the central AI manager instance

app = FastAPI(title="Vexere Chatbot POC Backend - Centralized AI Agent")

# CORS Configuration
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:8080",
    "null",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Global Stores ---
conversation_histories: Dict[
    str, List[Content]  # History will be List[vertexai.generative_models.Content]
] = {}
active_tool_states: Dict[str, Dict[str, Any]] = {}


# --- Tool Mapping ---
AVAILABLE_TOOLS: Dict[str, Callable[..., Coroutine[Any, Any, Dict[str, Any]]]] = {
    "get_faq_answer": tools.get_faq_answer,
    "initiate_change_booking_time_flow": tools.initiate_change_booking_time_flow,
    "provide_booking_id_for_change": tools.provide_booking_id_for_change,
    "confirm_booking_time_change": tools.confirm_booking_time_change,
}


async def run_sync_tool(
    tool_func: Callable[..., Dict[str, Any]], *args, **kwargs
) -> Dict[str, Any]:
    return tool_func(*args, **kwargs)


# --- Mock Vexere API Endpoint ---
@app.post("/mock_vexere/change_booking", response_model=MockVexereApiResponse)
async def mock_change_booking_endpoint(payload: ChangeBookingTimePayload):
    print(f"[Mock Vexere API] Received change booking request: {payload}")
    if not payload.booking_id:
        return MockVexereApiResponse(success=False, message="Booking ID is required.")
    if not payload.new_time:
        return MockVexereApiResponse(success=False, message="New time is required.")
    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", payload.new_time):
        return MockVexereApiResponse(
            success=False,
            message="Invalid new_time format. Please use YYYY-MM-DD HH:MM:SS.",
        )
    if "FAIL" in payload.booking_id.upper():
        return MockVexereApiResponse(
            success=False,
            message=f"Failed to change booking for {payload.booking_id}. Reason: Ticket not eligible for change.",
        )
    return MockVexereApiResponse(
        success=True,
        message=f"Successfully changed booking {payload.booking_id} to new time: {payload.new_time}.",
        data={
            "booking_id": payload.booking_id,
            "new_time": payload.new_time,
            "status": "CONFIRMED",
        },
    )


# --- Chat Endpoint ---
@app.post("/chat", response_model=ChatMessageOutput)
async def chat_handler(chat_input: ChatMessageInput):
    user_id = chat_input.user_id
    user_message_text = chat_input.message.strip()

    current_history = conversation_histories.get(user_id, [])
    current_tool_state = active_tool_states.get(user_id, {})
    bot_response_text = "I'm sorry, I encountered an issue processing your request."

    if not ai_manager.active_agent:
        bot_response_text = "Error: The AI Agent service is not available. Please check backend configuration."
        return ChatMessageOutput(
            bot_response=bot_response_text, session_state=current_tool_state
        )

    try:
        print(f"\n--- Turn for User: {user_id} ---")
        print(f"User message: {user_message_text}")

        # LLM Call 1: Get initial response or function call
        llm_response_data = await ai_manager.get_agent_response(
            chat_history=current_history,
            user_message=user_message_text,
            image_base64=chat_input.image_base64,
            image_mime_type=chat_input.image_mime_type,
            audio_base64=chat_input.audio_base64,
            audio_mime_type=chat_input.audio_mime_type,
        )

        # Add user's turn to history, including any multimodal parts
        user_turn_parts = []
        if user_message_text:
            user_turn_parts.append(Part.from_text(user_message_text))

        # For this POC, `main.py`'s history only stores the text of user messages.
        # `VertexAIAgent` sends the full message (text + image/audio, if any) to Gemini for the current turn.
        if chat_input.image_base64 and chat_input.image_mime_type:
            # Image data is processed by VertexAIAgent for the current call
            pass

        if chat_input.audio_base64 and chat_input.audio_mime_type:
            # Audio data is processed by VertexAIAgent for the current call
            pass

        if user_turn_parts:  # Ensure we have something to add
            current_history.append(Content(role="user", parts=user_turn_parts))
        # If only image/audio was sent with no text, current_history might not get a user text part here.
        # This is acceptable if VertexAIAgent correctly formed the multimodal input.

        if "error" in llm_response_data:
            bot_response_text = llm_response_data["error"]
            # Optionally add error to history if it's an LLM error, not a system one
            # current_history.append(Content(role="model", parts=[Part.from_text(f"LLM Error: {bot_response_text}")]))

        elif "function_call" in llm_response_data:
            fc_data = llm_response_data["function_call"]
            tool_name = fc_data["name"]
            tool_args = fc_data.get("args", {})
            raw_model_part_fc = llm_response_data.get(
                "raw_model_response_part"
            )  # Get the raw Part

            print(f"LLM requested Function Call: {tool_name} with args: {tool_args}")

            if raw_model_part_fc:
                current_history.append(Content(role="model", parts=[raw_model_part_fc]))
            else:  # Fallback if raw part isn't passed (should not happen with updated vertex_agent.py)
                current_history.append(
                    Content(
                        role="model",
                        parts=[
                            Part(function_call={"name": tool_name, "args": tool_args})
                        ],
                    )
                )

            tool_result_content: Dict[str, Any] = {
                "error": f"Tool {tool_name} execution failed."
            }
            if tool_name in AVAILABLE_TOOLS:
                actual_tool_function = AVAILABLE_TOOLS[tool_name]
                final_tool_args = dict(tool_args)

                if tool_name == "confirm_booking_time_change":
                    if (
                        "booking_id" not in final_tool_args
                        and "collected_booking_id" in current_tool_state
                    ):
                        final_tool_args["booking_id"] = current_tool_state[
                            "collected_booking_id"
                        ]

                try:
                    print(
                        f"Executing tool: {tool_name} with final args: {final_tool_args}"
                    )
                    if tool_name == "confirm_booking_time_change":
                        tool_result_content = await actual_tool_function(
                            **final_tool_args
                        )
                    else:  # Sync tools
                        tool_result_content = await run_sync_tool(
                            actual_tool_function, **final_tool_args
                        )
                    print(f"Tool {tool_name} result: {tool_result_content}")

                    if (
                        tool_name == "initiate_change_booking_time_flow"
                        and tool_result_content.get("status") == "flow_initiated"
                    ):
                        current_tool_state = {
                            "flow_name": "change_booking",
                            "stage": "awaiting_booking_id",
                        }
                    elif (
                        tool_name == "provide_booking_id_for_change"
                        and tool_result_content.get("status") == "booking_id_received"
                    ):
                        current_tool_state["collected_booking_id"] = (
                            tool_result_content.get("booking_id")
                        )
                        current_tool_state["stage"] = "awaiting_new_time"
                    elif tool_name == "confirm_booking_time_change":
                        current_tool_state = {}
                except Exception as e:
                    print(f"Error executing tool {tool_name}: {e}")
                    tool_result_content = {
                        "error": f"Error during {tool_name}: {str(e)}"
                    }

            function_response_part_for_history = Part.from_function_response(
                name=tool_name, response={"content": tool_result_content}
            )
            current_history.append(
                Content(role="function", parts=[function_response_part_for_history])
            )

            print(
                f"Sending tool result back to LLM. History length: {len(current_history)}"
            )
            # LLM Call 2: Get final response after tool execution
            final_llm_response_data = await ai_manager.get_agent_response(
                chat_history=current_history,  # History now includes the function response
                user_message="Based on the tool's output, what should I say to the user?",
            )

            if "error" in final_llm_response_data:
                bot_response_text = final_llm_response_data["error"]
            elif "text" in final_llm_response_data:
                bot_response_text = final_llm_response_data["text"]
                raw_model_part_text = final_llm_response_data.get(
                    "raw_model_response_part"
                )
                if raw_model_part_text:
                    current_history.append(
                        Content(role="model", parts=[raw_model_part_text])
                    )
                else:  # Fallback
                    current_history.append(
                        Content(role="model", parts=[Part.from_text(bot_response_text)])
                    )
            else:
                bot_response_text = "I've processed that action. How else can I help?"
                current_history.append(
                    Content(role="model", parts=[Part.from_text(bot_response_text)])
                )

        elif "text" in llm_response_data:
            bot_response_text = llm_response_data["text"]
            raw_model_part_text = llm_response_data.get("raw_model_response_part")
            if raw_model_part_text:
                current_history.append(
                    Content(role="model", parts=[raw_model_part_text])
                )
            else:  # Fallback
                current_history.append(
                    Content(role="model", parts=[Part.from_text(bot_response_text)])
                )

        else:
            bot_response_text = "The AI agent returned an unexpected response format."
            current_history.append(
                Content(role="model", parts=[Part.from_text(bot_response_text)])
            )

    except Exception as e:
        print(f"Critical error in chat_handler: {e}")
        bot_response_text = f"A system error occurred: {str(e)}"

    conversation_histories[user_id] = current_history
    active_tool_states[user_id] = current_tool_state

    print(f"Bot response to user {user_id}: {bot_response_text}")

    return ChatMessageOutput(
        bot_response=bot_response_text,
        session_state={
            "history_length": len(current_history),
            "active_tool_state_keys": list(current_tool_state.keys()),
        },
    )


@app.get("/")
async def root():
    return {"message": "Vexere Chatbot POC Backend (Centralized AI Agent) is running!"}


if __name__ == "__main__":
    import uvicorn

    print(
        "Starting Uvicorn server for Vexere Chatbot POC Backend (Centralized AI Agent)..."
    )
    print("Run: uvicorn backend.app.main:app --reload --port 8000 --app-dir .")
