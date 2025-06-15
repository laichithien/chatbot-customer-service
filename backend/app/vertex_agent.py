import base64  # For decoding image/audio data
import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Part,
    Tool,
    FunctionDeclaration,
    Content,
)
from typing import List, Dict, Any, Optional

# Import configuration
from backend.app import config as app_config

# Initialize Vertex AI
try:
    vertexai.init(project=app_config.PROJECT_ID, location=app_config.LOCATION)
except Exception as e:
    print(
        f"Error initializing Vertex AI: {e}. Ensure Application Default Credentials are set up."
    )
    # Allow the application to continue so other parts can be tested if Vertex AI is not critical for them.
    # However, the agent will not work.

# --- Tool Definitions for Gemini (remain the same as before) ---

get_faq_answer_func = FunctionDeclaration(
    name="get_faq_answer",
    description="Searches and retrieves answers to frequently asked questions (FAQs) about Vexere services, policies, and general information. Use this tool when the user asks a question that is likely an FAQ (e.g., 'How do I cancel my ticket?', 'What payment methods are accepted?').",
    parameters={
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": "The user's question that needs an FAQ answer.",
            }
        },
        "required": ["question"],
    },
)

initiate_change_booking_time_flow_func = FunctionDeclaration(
    name="initiate_change_booking_time_flow",
    description="Starts the process for a user wanting to change their bus ticket booking time. Call this tool when the user expresses a clear intent to change their booking time or schedule (e.g., 'I want to change my ticket time', 'đổi giờ vé', 'reschedule my booking'). Do not ask for booking ID or new time yet; this tool just starts the flow.",
    parameters={"type": "object", "properties": {}},
)

provide_booking_id_for_change_func = FunctionDeclaration(
    name="provide_booking_id_for_change",
    description="Processes the booking ID provided by the user as part of the 'change booking time' flow. Call this tool after the user has supplied their booking ID in response to a prompt from the system.",
    parameters={
        "type": "object",
        "properties": {
            "booking_id": {
                "type": "string",
                "description": "The booking ID (e.g., VX12345, ABC987) provided by the user.",
            }
        },
        "required": ["booking_id"],
    },
)

confirm_booking_time_change_func = FunctionDeclaration(
    name="confirm_booking_time_change",
    description="Attempts to finalize the change of a booking to a new time by calling the Vexere system. This tool should be called only after the user has provided both their booking ID and the new desired time for their ticket (e.g., after the system has collected these details in previous turns).",
    parameters={
        "type": "object",
        "properties": {
            "booking_id": {
                "type": "string",
                "description": "The booking ID of the ticket to be changed, previously collected from the user.",
            },
            "new_time": {
                "type": "string",
                "description": "The new desired date and time for the booking, in 'YYYY-MM-DD HH:MM:SS' format (e.g., '2025-12-31 14:30:00'), previously collected from the user.",
            },
        },
        "required": ["booking_id", "new_time"],
    },
)

vexere_tool_config = Tool(
    function_declarations=[
        get_faq_answer_func,
        initiate_change_booking_time_flow_func,
        provide_booking_id_for_change_func,
        confirm_booking_time_change_func,
    ]
)

# --- Agent Logic ---


class VertexAIAgent:
    def __init__(self, model_name: str = app_config.MODEL_NAME):
        try:
            self.model = GenerativeModel(model_name)
            print(f"Vertex AI Agent initialized with model: {model_name}")
        except Exception as e:
            print(f"Failed to initialize GenerativeModel ({model_name}): {e}")
            self.model = None

    async def get_gemini_response(
        self,
        chat_history: List[Content],
        user_message: str,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        audio_base64: Optional[str] = None,
        audio_mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Sends the user message, history, and optional multimodal data to Gemini and gets a response.
        Handles potential function calls.
        The chat_history should be complete up to the point *before* this new user_message.
        If user_message is an internal prompt after a tool call, chat_history should already contain
        [..., user_prompt_that_led_to_tool_call, model_tool_call_request, function_tool_execution_result]
        """
        if not self.model:
            return {
                "error": "Gemini model not initialized. Please check Vertex AI setup."
            }

        messages_for_gemini = list(chat_history)

        # Construct parts for the current user message
        current_user_parts = []
        if (
            user_message
        ):  # Ensure user_message is not empty before adding as a text part
            current_user_parts.append(Part.from_text(user_message))

        if image_base64 and image_mime_type:
            try:
                image_bytes = base64.b64decode(image_base64)
                current_user_parts.append(
                    Part.from_data(data=image_bytes, mime_type=image_mime_type)
                )
                print("[VertexAIAgent] Added image part to current user message.")
            except Exception as e:
                print(f"[VertexAIAgent] Error decoding or adding image part: {e}")

        if audio_base64 and audio_mime_type:
            try:
                audio_bytes = base64.b64decode(audio_base64)
                current_user_parts.append(
                    Part.from_data(data=audio_bytes, mime_type=audio_mime_type)
                )
                print("[VertexAIAgent] Added audio part to current user message.")
            except Exception as e:
                print(f"[VertexAIAgent] Error decoding or adding audio part: {e}")

        # Only add a user message if there are parts to send
        if current_user_parts:
            messages_for_gemini.append(Content(role="user", parts=current_user_parts))
        elif (
            not messages_for_gemini
        ):  # If history is also empty and no current message parts
            print(
                "[VertexAIAgent] Error: No history and no content in current user message (no text, image, or audio)."
            )
            return {"error": "Cannot send an empty message to the model."}

        print(
            f"\n[VertexAIAgent] Sending to Gemini. Total Content objects: {len(messages_for_gemini)}"
        )
        if not messages_for_gemini:  # Should be caught by above, but as a safeguard
            return {"error": "No messages to send to Gemini."}

        try:
            response = self.model.generate_content(
                messages_for_gemini,
                tools=[vexere_tool_config],
            )

            print("[VertexAIAgent] Received response from Gemini.")

            if not response.candidates or not response.candidates[0].content.parts:
                print("[VertexAIAgent] Warning: Gemini response is empty or malformed.")
                return {
                    "text": "I'm sorry, I encountered an issue processing your request with the AI model."
                }

            model_response_part = response.candidates[0].content.parts[0]

            if model_response_part.function_call:
                function_call = model_response_part.function_call
                return {
                    "function_call": {
                        "name": function_call.name,
                        "args": {key: val for key, val in function_call.args.items()},
                    },
                    "raw_model_response_part": model_response_part,
                }
            elif model_response_part.text:
                return {
                    "text": model_response_part.text,
                    "raw_model_response_part": model_response_part,
                }
            else:
                print(
                    "[VertexAIAgent] Warning: Gemini response part has no text or function call."
                )
                return {
                    "text": "I received an unusual response from the AI model. Please try again."
                }

        except Exception as e:
            print(f"[VertexAIAgent] Error during Gemini API call: {e}")
            return {
                "error": f"An error occurred while communicating with the AI model: {str(e)}"
            }


if __name__ == "__main__":
    print("Testing Vertex AI Agent (requires ADC to be set up)...")
    agent = VertexAIAgent()

    async def run_test():
        if not agent.model:
            print("Agent model not initialized. Skipping test.")
            return

        print("\n--- Test 1: Simple FAQ Query ---")
        history1: List[Content] = []

        user_q1 = "How do I cancel my ticket?"
        print(f"User: {user_q1}")
        response1 = await agent.get_gemini_response(history1, user_q1)
        print(f"Agent: {response1}")

        history1.append(Content(role="user", parts=[Part.from_text(user_q1)]))
        if response1.get("raw_model_response_part"):
            history1.append(
                Content(role="model", parts=[response1["raw_model_response_part"]])
            )

        if response1.get("function_call"):
            fc1 = response1["function_call"]
            if fc1["name"] == "get_faq_answer":
                tool_result1 = {
                    "answer": "Mocked: You can cancel your ticket via the app."
                }
                print(f"Tool ({fc1['name']}): {tool_result1}")

                function_response_part1 = Part.from_function_response(
                    name=fc1["name"], response={"content": tool_result1}
                )
                history1.append(
                    Content(role="function", parts=[function_response_part1])
                )

                internal_prompt1 = "Summarize this for the user."
                print(f"User (internal): {internal_prompt1}")
                response2 = await agent.get_gemini_response(history1, internal_prompt1)
                print(f"Agent: {response2}")

    import asyncio

    asyncio.run(run_test())
