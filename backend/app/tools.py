import json
import os
from typing import List, Dict, Any, Optional
import re  # For simple time format validation
import httpx  # For making HTTP calls from tools

# Import configuration
from backend.app import config as app_config

# Load FAQ data
FAQ_DATA_PATH = os.path.join(os.path.dirname(__file__), "faq_data.json")
try:
    with open(FAQ_DATA_PATH, "r", encoding="utf-8") as f:
        faq_data: List[Dict[str, Any]] = json.load(f)
except FileNotFoundError:
    faq_data = []
    print(f"Warning: {FAQ_DATA_PATH} not found. FAQ tool will not work.")
except json.JSONDecodeError:
    faq_data = []
    print(f"Warning: Error decoding {FAQ_DATA_PATH}. FAQ tool will not work.")


def get_faq_answer(question: str) -> Dict[str, str]:
    """
    Searches for an FAQ answer based on keywords in the question.
    This is a simplified RAG simulation.
    Returns a dictionary with 'answer' or 'error'.
    Example for LLM:
    If the user asks "How do I cancel my ticket?", call this tool with question="How do I cancel my ticket?".
    The tool will return {"answer": "You can cancel..."} or {"error": "FAQ unavailable"}.
    """
    question_lower = question.lower()
    best_match_answer = None
    highest_match_count = 0

    if not faq_data:
        return {"error": "I'm sorry, my FAQ knowledge base is currently unavailable."}

    for item in faq_data:
        match_count = 0
        for keyword in item.get("keywords", []):
            if keyword.lower() in question_lower:
                match_count += 1

        if match_count > highest_match_count:
            highest_match_count = match_count
            best_match_answer = item.get("answer")

    if best_match_answer and highest_match_count > 0:
        return {"answer": best_match_answer}

    return {
        "answer": "I'm sorry, I couldn't find an answer to that specific question in my current knowledge base. Could you try rephrasing or asking something else?"
    }


def initiate_change_booking_time_flow() -> Dict[str, str]:
    """
    Initiates the flow for changing a booking time.
    Call this tool when the user expresses intent to change their booking time (e.g., "I want to change my ticket time", "đổi giờ vé").
    This tool signals that the conversation should proceed to ask for the booking ID.
    Returns: {"status": "flow_initiated", "next_action_prompt": "Please provide your booking ID."}
    The main application will use this to guide the LLM or directly prompt the user.
    """
    # The orchestrator (main.py) will manage state based on this tool being called.
    return {
        "status": "flow_initiated",
        "next_action_prompt": "Please provide your booking ID.",
    }


def provide_booking_id_for_change(booking_id: str) -> Dict[str, str]:
    """
    Processes the booking ID provided by the user during the 'change booking time' flow.
    Call this tool after the user has provided their booking ID in response to a prompt.
    Args:
        booking_id (str): The booking ID provided by the user (e.g., "VX12345").
    Returns:
        If booking_id is valid (non-empty string):
        {"status": "booking_id_received", "booking_id": "VX12345", "next_action_prompt": "What is the new date and time...?"}
        If booking_id is invalid:
        {"status": "error", "message": "Booking ID is invalid or missing."}
    """
    if (
        not booking_id
        or not isinstance(booking_id, str)
        or len(booking_id.strip()) == 0
    ):
        return {
            "status": "error",
            "message": "Booking ID is invalid or missing. Please provide a valid booking ID.",
        }

    # In a real scenario, you might validate the booking_id format here.
    return {
        "status": "booking_id_received",
        "booking_id": booking_id,
        "next_action_prompt": "What is the new date and time you'd like? (Please use YYYY-MM-DD HH:MM:SS format, e.g., 2025-12-31 14:30:00)",
    }


async def confirm_booking_time_change(booking_id: str, new_time: str) -> Dict[str, Any]:
    """
    Attempts to confirm the booking time change by calling the mock Vexere API.
    Call this tool after the user has provided both the booking ID and the new desired time.
    Args:
        booking_id (str): The booking ID for the ticket to be changed (e.g., "VX12345").
        new_time (str): The new desired time in 'YYYY-MM-DD HH:MM:SS' format (e.g., "2025-12-31 14:30:00").
    Returns:
        A dictionary with the result of the API call, e.g.,
        {"success": True, "message": "Successfully changed booking...", "data": {"status": "CONFIRMED"}} or
        {"success": False, "message": "Failed to change booking..."}
    """
    if not booking_id:
        return {
            "success": False,
            "message": "Booking ID was not provided for confirmation.",
        }
    if not new_time:
        return {
            "success": False,
            "message": "New time was not provided for confirmation.",
        }

    # Validate time format
    if not re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", new_time):
        return {
            "success": False,
            "message": "Invalid new_time format. Please use YYYY-MM-DD HH:MM:SS.",
        }

    api_url = f"{app_config.MOCK_API_BASE_URL}/mock_vexere/change_booking"
    payload = {"booking_id": booking_id, "new_time": new_time}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=payload)
            response.raise_for_status()
            api_result = response.json()
            print(
                f"[Tool: confirm_booking_time_change] Received response from mock API: {api_result}"
            )
            return api_result
        except httpx.RequestError as e:
            print(f"Error calling mock Vexere API: {e}")
            return {
                "success": False,
                "message": f"Network error when trying to change booking: {str(e)}",
            }
        except httpx.HTTPStatusError as e:
            print(
                f"HTTP error from mock Vexere API: {e.response.status_code} - {e.response.text}"
            )
            try:
                error_details = e.response.json()
                return {
                    "success": False,
                    "message": f"Failed to change booking: {error_details.get('message', e.response.text)}",
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "message": f"Failed to change booking: {e.response.status_code} - Error message not in JSON format.",
                }
        except Exception as e:
            print(f"Unexpected error during API call: {e}")
            return {
                "success": False,
                "message": f"An unexpected error occurred while attempting to change booking: {str(e)}",
            }


# Placeholder functions for future Image & Voice processing capabilities
def process_image_input(image_data: bytes) -> str:
    """
    Placeholder for image processing (e.g., OCR).
    In a real scenario, this would call an OCR service.
    This tool is not yet fully implemented for the LLM.
    """
    # Simulate OCR extraction
    return "[Simulated OCR Text from Image: User wants to change booking for ticket #IMG123]"


def process_voice_input(voice_data: bytes) -> str:
    """
    Placeholder for voice processing (Speech-to-Text).
    In a real scenario, this would call an STT service.
    This tool is not yet fully implemented for the LLM.
    """
    # Simulate STT
    return "User said: I want to change my flight time."


if __name__ == "__main__":
    # Test FAQ
    print("Testing FAQ:")
    print(f"Q: How to cancel ticket? A: {get_faq_answer('How to cancel ticket?')}")
    print(
        f"Q: What are payment options? A: {get_faq_answer('What are payment options?')}"
    )
    print(f"Q: Unknown question? A: {get_faq_answer('What is the color of the sky?')}")

    # Test time format validation (as if it were part of a tool)
    print("\nTesting time format validation (simulated within a tool):")
    valid_time = "2025-10-20 10:00:00"
    invalid_time_format = "20-10-2025 10:00"

    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", valid_time):
        print(f"'{valid_time}' is valid.")
    else:
        print(f"'{valid_time}' is invalid.")

    if re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", invalid_time_format):
        print(f"'{invalid_time_format}' is valid.")
    else:
        print(f"'{invalid_time_format}' is invalid.")

    # Example of how confirm_booking_time_change might be tested (requires running mock API)
    # import asyncio
    # async def test_confirm():
    #     result = await confirm_booking_time_change("VX123", "2025-12-01 10:00:00")
    #     print(f"Test confirm_booking_time_change: {result}")
    # asyncio.run(test_confirm())
