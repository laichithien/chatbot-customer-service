from typing import List, Dict, Any, Optional
from google.cloud.aiplatform_v1beta1.types import (
    Content,
)  # Specific to Vertex AI history

# Import specific agent implementations
from .vertex_agent import VertexAIAgent
# from .openai_agent import OpenAIAgent # Future placeholder
# from .anthropic_agent import AnthropicAgent # Future placeholder

# Import configuration
from backend.app import config as app_config


class AIAgentsManager:
    def __init__(self):
        self.active_agent = None
        self.provider_name = app_config.ACTIVE_LLM_PROVIDER  # Use from config

        if self.provider_name == "VERTEX_AI":
            self.active_agent = VertexAIAgent()
            if not self.active_agent.model:
                print(
                    f"CRITICAL: Failed to initialize {self.provider_name} agent model. AI functionalities will be impacted."
                )
        # elif self.provider_name == "OPENAI":
        #     self.active_agent = OpenAIAgent() # Assuming OpenAIAgent is defined elsewhere
        #     if not self.active_agent.is_ready(): # Example check
        #          print(f"CRITICAL: Failed to initialize {self.provider_name} agent.")
        # elif self.provider_name == "ANTHROPIC":
        #     self.active_agent = AnthropicAgent()
        #     if not self.active_agent.is_ready():
        #          print(f"CRITICAL: Failed to initialize {self.provider_name} agent.")
        else:
            print(
                f"CRITICAL: Unsupported LLM provider configured: {self.provider_name}. AI functionalities will not work."
            )
            raise ValueError(f"Unsupported LLM provider: {self.provider_name}")

        if self.active_agent:
            print(
                f"AIAgentsManager initialized with active provider: {self.provider_name}"
            )

    async def get_agent_response(
        self,
        chat_history: List[Any],
        user_message: str,
        image_base64: Optional[str] = None,
        image_mime_type: Optional[str] = None,
        audio_base64: Optional[str] = None,
        audio_mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Gets a response from the currently active LLM agent, potentially with multimodal input.
        This is the single, generic method that the application should use for LLM interactions.

        Args:
            chat_history: The conversation history. The format might need to be adapted
                          by the specific agent implementation if they differ significantly.
                          For Vertex AI, this is List[Content].
            user_message: The current user's message.

        Returns:
            A dictionary containing either a "text" response or a "function_call",
            or an "error" key if something went wrong.
        """
        if not self.active_agent:
            return {
                "error": f"No active LLM agent configured or agent failed to initialize ({self.provider_name})."
            }

        try:
            if self.provider_name == "VERTEX_AI":
                # VertexAIAgent.get_gemini_response expects List[Content] for history
                # Ensure chat_history is in the correct format or adapt it here if necessary.
                # main.py should provide chat_history in the correct format for the current AI.
                return await self.active_agent.get_gemini_response(
                    chat_history=chat_history,  # type: ignore
                    user_message=user_message,
                    image_base64=image_base64,
                    image_mime_type=image_mime_type,
                    audio_base64=audio_base64,
                    audio_mime_type=audio_mime_type,
                )
            # elif self.provider_name == "OPENAI":
            #     # Adapt chat_history format if needed for OpenAI
            #     return await self.active_agent.get_openai_response(chat_history, user_message)
            # elif self.provider_name == "ANTHROPIC":
            #     # Adapt chat_history format if needed for Anthropic
            #     return await self.active_agent.get_anthropic_response(chat_history, user_message)
            else:
                # This case should have been caught in __init__, but as a safeguard:
                return {
                    "error": f"Unsupported LLM provider '{self.provider_name}' in get_agent_response."
                }
        except Exception as e:
            print(
                f"Error during LLM interaction via AIAgentsManager ({self.provider_name}): {e}"
            )
            return {
                "error": f"An unexpected error occurred with the AI agent: {str(e)}"
            }


# Global instance of the manager
# The application will import and use this instance.
ai_manager = AIAgentsManager()

if __name__ == "__main__":
    # Example of how this manager might be tested (basic)
    async def test_manager():
        print(f"Testing AIAgentsManager with provider: {ai_manager.provider_name}")
        if not ai_manager.active_agent:
            print("No active agent to test.")
            return

        sample_history = []  # For Vertex AI, this would be List[Content]
        if ai_manager.provider_name == "VERTEX_AI":
            # For a direct test, we might need to create dummy Content objects or skip history
            pass

        response = await ai_manager.get_agent_response(  # Basic text-only test
            chat_history=sample_history, user_message="Hello, who are you?"
        )
        print("Test Response (text only):", response)

        # This example test primarily focuses on text-based interactions.
        response_faq = await ai_manager.get_agent_response(
            chat_history=sample_history,
            user_message="How to cancel ticket?",
        )
        print("Test FAQ Response (text only):", response_faq)

    import asyncio

    asyncio.run(test_manager())
