import vertexai
from vertexai.generative_models import GenerativeModel, Part


def call_gemini_api(project_id: str, location: str, model_name: str, prompt_text: str):
    """Calls the Gemini API with the given parameters and prints the response.

    Args:
        project_id: The Google Cloud project ID.
        location: The Google Cloud region for the API call.
        model_name: The name of the Gemini model to use.
        prompt_text: The text prompt to send to the model.
    """
    try:
        # Initialize Vertex AI
        vertexai.init(project=project_id, location=location)

        # Load the generative model
        model = GenerativeModel(model_name)

        # Create the prompt
        prompt_parts = [
            Part.from_text(prompt_text),
        ]

        # Send the prompt to the model
        print(f"Sending prompt to model: {model_name}...")
        response = model.generate_content(prompt_parts)

        # Print the response
        print("\nModel Response:")
        if response.candidates:
            for candidate in response.candidates:
                if candidate.content and candidate.content.parts:
                    for part in candidate.content.parts:
                        if part.text:
                            print(part.text)
                        else:
                            print("[No text in part]")
                else:
                    print("[No content in candidate]")
        else:
            print("[No candidates in response]")

        print(f"\nFull response object:\n{response}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    # --- CONFIGURATION ---
    PROJECT_ID = "singular-ray-456411-t7"
    LOCATION = "us-central1"
    # As per your instruction, this is not a typo.
    MODEL_NAME = "gemini-2.5-pro-preview-05-06"
    USER_PROMPT = (
        "Translate the following English text to French: 'Hello, how are you today?'"
    )
    # --- END CONFIGURATION ---

    print(f"Attempting to call Gemini API with:")
    print(f"  Project ID: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Model Name: {MODEL_NAME}")
    print(f'  Prompt: "{USER_PROMPT}"')
    print("-" * 30)

    call_gemini_api(PROJECT_ID, LOCATION, MODEL_NAME, USER_PROMPT)
