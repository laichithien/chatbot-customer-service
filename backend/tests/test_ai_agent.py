import unittest
import asyncio
from typing import List, Dict, Any

# Ensure the app directory is in the Python path for imports
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai_agents_manager import ai_manager  # Use the global instance
from vertexai.generative_models import (
    Content,
    Part,
)  # Use these for constructing history


class TestAIAgentResponses(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        if not ai_manager.active_agent or (
            hasattr(ai_manager.active_agent, "model")
            and not ai_manager.active_agent.model
        ):
            self.skipTest(
                f"Vertex AI Agent ({ai_manager.provider_name}) not available or model not initialized. Skipping tests."
            )

    async def test_simple_text_response(self):
        print("\nRunning test_simple_text_response...")
        history: List[Content] = []
        user_message = "Hello, how are you today?"
        response = await ai_manager.get_agent_response(
            chat_history=history, user_message=user_message
        )
        print(f"  LLM Response: {response}")
        self.assertIsNotNone(response, "Agent response should not be None.")
        self.assertIn(
            "text", response, "Response should contain a 'text' key for direct answers."
        )
        self.assertNotIn(
            "function_call",
            response,
            "Response should not be a function call for a simple greeting.",
        )
        self.assertNotIn(
            "error",
            response,
            f"Response should not contain an error: {response.get('error')}",
        )
        self.assertTrue(
            len(response.get("text", "")) > 0, "Text response should not be empty."
        )

    async def test_faq_tool_usage_and_response_generation(self):
        print("\nRunning test_faq_tool_usage_and_response_generation...")
        history_turn1: List[Content] = []
        user_message_turn1 = "How do I change my Vexere ticket?"

        print("  Turn 1: User asks FAQ...")
        response_turn1 = await ai_manager.get_agent_response(
            chat_history=history_turn1, user_message=user_message_turn1
        )
        print(f"  LLM Response (Turn 1): {response_turn1}")

        self.assertIn(
            "function_call",
            response_turn1,
            "LLM should request a function call for an FAQ.",
        )
        fc_data_turn1 = response_turn1["function_call"]
        self.assertEqual(
            fc_data_turn1["name"],
            "get_faq_answer",
            "LLM should call 'get_faq_answer' tool.",
        )
        self.assertIn(
            "question",
            fc_data_turn1["args"],
            "Tool arguments should contain 'question'.",
        )

        history_turn2: List[Content] = [
            Content(role="user", parts=[Part.from_text(user_message_turn1)]),
            Content(
                role="model", parts=[Part.from_dict({"function_call": fc_data_turn1})]
            ),
        ]

        mock_faq_tool_result = {
            "answer": "To change your Vexere ticket, you can go to 'My Bookings'. (Test answer)"
        }
        function_response_part = Part.from_function_response(
            name="get_faq_answer", response={"content": mock_faq_tool_result}
        )
        history_turn2.append(Content(role="function", parts=[function_response_part]))

        print("  Turn 2: Sending mocked tool result back to LLM...")
        user_message_turn2 = "Okay, based on that FAQ answer, please inform the user."
        response_turn2 = await ai_manager.get_agent_response(
            chat_history=history_turn2, user_message=user_message_turn2
        )
        print(f"  LLM Response (Turn 2): {response_turn2}")

        self.assertIn(
            "text",
            response_turn2,
            "LLM should provide a text response after tool execution.",
        )
        self.assertNotIn(
            "function_call",
            response_turn2,
            "LLM should not call another function immediately after FAQ result.",
        )
        self.assertNotIn(
            "error",
            response_turn2,
            f"Response should not be an error: {response_turn2.get('error')}",
        )
        self.assertTrue(
            len(response_turn2.get("text", "")) > 0,
            "Final text response should not be empty.",
        )
        self.assertIn(
            "My Bookings",
            response_turn2.get("text", ""),
            "Final response should incorporate the tool's answer content.",
        )

    async def test_initiate_change_booking_flow(self):
        print("\nRunning test_initiate_change_booking_flow...")
        history: List[Content] = []
        user_message = "I need to change the time of my bus ticket."
        response = await ai_manager.get_agent_response(
            chat_history=history, user_message=user_message
        )
        print(f"  LLM Response: {response}")
        self.assertIn("function_call", response, "LLM should request a function call.")
        fc_data = response["function_call"]
        self.assertEqual(fc_data["name"], "initiate_change_booking_time_flow")
        self.assertTrue(
            not fc_data.get("args") or len(fc_data.get("args", {})) == 0,
            "initiate_change_booking_time_flow should have no args.",
        )

    async def test_provide_booking_id_after_initiation(self):
        print("\nRunning test_provide_booking_id_after_initiation...")
        history: List[Content] = [
            Content(role="user", parts=[Part.from_text("I want to change my ticket")]),
            Content(
                role="model",
                parts=[
                    Part.from_dict(
                        {
                            "function_call": {
                                "name": "initiate_change_booking_time_flow",
                                "args": {},
                            }
                        }
                    )
                ],
            ),
            Content(
                role="function",
                parts=[
                    Part.from_function_response(
                        name="initiate_change_booking_time_flow",
                        response={
                            "content": {
                                "status": "flow_initiated",
                                "next_action_prompt": "Please provide your booking ID.",
                            }
                        },
                    )
                ],
            ),
            Content(
                role="model",
                parts=[
                    Part.from_text(
                        "Okay, I can help with that. What is your booking ID?"
                    )
                ],
            ),
        ]
        user_message = "My booking ID is VX7890"
        print("  Sending user message with booking ID...")
        response = await ai_manager.get_agent_response(
            chat_history=history, user_message=user_message
        )
        print(f"  LLM Response: {response}")
        self.assertIn(
            "function_call",
            response,
            "LLM should request a function call to process booking ID.",
        )
        fc_data = response["function_call"]
        self.assertEqual(fc_data["name"], "provide_booking_id_for_change")
        self.assertIn(
            "booking_id", fc_data["args"], "Tool arguments should contain 'booking_id'."
        )
        self.assertEqual(
            fc_data["args"]["booking_id"],
            "VX7890",
            "LLM should extract the booking ID correctly.",
        )

    async def test_confirm_booking_change_tool_usage(self):
        print("\nRunning test_confirm_booking_change_tool_usage...")
        history: List[Content] = [
            Content(
                role="user", parts=[Part.from_text("I want to change my ticket time.")]
            ),
            Content(
                role="model",
                parts=[
                    Part.from_dict(
                        {
                            "function_call": {
                                "name": "initiate_change_booking_time_flow",
                                "args": {},
                            }
                        }
                    )
                ],
            ),
            Content(
                role="function",
                parts=[
                    Part.from_function_response(
                        name="initiate_change_booking_time_flow",
                        response={"content": {"status": "flow_initiated"}},
                    )
                ],
            ),
            Content(
                role="model", parts=[Part.from_text("Sure, what's your booking ID?")]
            ),
            Content(role="user", parts=[Part.from_text("It's VX123")]),
            Content(
                role="model",
                parts=[
                    Part.from_dict(
                        {
                            "function_call": {
                                "name": "provide_booking_id_for_change",
                                "args": {"booking_id": "VX123"},
                            }
                        }
                    )
                ],
            ),
            Content(
                role="function",
                parts=[
                    Part.from_function_response(
                        name="provide_booking_id_for_change",
                        response={
                            "content": {
                                "status": "booking_id_received",
                                "booking_id": "VX123",
                            }
                        },
                    )
                ],
            ),
            Content(
                role="model",
                parts=[
                    Part.from_text(
                        "Thanks! And the new time you'd like (YYYY-MM-DD HH:MM:SS)?"
                    )
                ],
            ),
        ]
        user_message = "Please change it to 2025-11-10 15:30:00"
        print("  Sending user message with new time...")
        response = await ai_manager.get_agent_response(
            chat_history=history, user_message=user_message
        )
        print(f"  LLM Response: {response}")
        self.assertIn(
            "function_call",
            response,
            "LLM should request confirm_booking_time_change call.",
        )
        fc_data = response["function_call"]
        self.assertEqual(fc_data["name"], "confirm_booking_time_change")
        self.assertIn(
            "booking_id", fc_data["args"], "Tool arguments should contain 'booking_id'."
        )
        self.assertEqual(
            fc_data["args"]["booking_id"],
            "VX123",
            "LLM should use the previously collected booking ID.",
        )
        self.assertIn(
            "new_time", fc_data["args"], "Tool arguments should contain 'new_time'."
        )
        self.assertEqual(
            fc_data["args"]["new_time"],
            "2025-11-10 15:30:00",
            "LLM should extract the new time correctly.",
        )


if __name__ == "__main__":
    unittest.main()
