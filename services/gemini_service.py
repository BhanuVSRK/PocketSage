import logging
from typing import List, Dict, Tuple
import google.genai as genai
from google.genai import types

from config import settings
from schemas import ChatMessage, SourceCitation, UserInDB   

logger = logging.getLogger(__name__)

# --- UPDATED System Prompt ---
# We now instruct the AI to be less repetitive with the disclaimer.
def get_system_prompt(user_profile: UserInDB) -> str:
    """
    Dynamically constructs the system prompt with the user's health profile.
    """
    profile_section = "The user has not provided any specific health information."
    if user_profile:
        profile_parts = []
        if user_profile.age: profile_parts.append(f"- Age: {user_profile.age}")
        if user_profile.gender: profile_parts.append(f"- Gender: {user_profile.gender}")
        if user_profile.weight_kg: profile_parts.append(f"- Weight: {user_profile.weight_kg} kg")
        if user_profile.height_cm: profile_parts.append(f"- Height: {user_profile.height_cm} cm")
        if user_profile.allergies: profile_parts.append(f"- Known Allergies: {', '.join(user_profile.allergies)}")
        if user_profile.previous_issues: profile_parts.append(f"- Previous Medical Issues: {', '.join(user_profile.previous_issues)}")
        if user_profile.current_medications: profile_parts.append(f"- Current Medications: {', '.join(user_profile.current_medications)}")
        
        if profile_parts:
            profile_section = "You MUST consider the following user health profile in your response:\n" + "\n".join(profile_parts)

    return f"""
        You are SageAI, a sophisticated and empathetic AI Medical Advisor. Your primary role is to provide safe, informative, and helpful guidance based on user queries and real-time, grounded web search results.

        ---
        {profile_section}
        ---
    **Your Core Directives:**

    1.  **CRITICAL SAFETY PROTOCOL:**
        - For the **very first message** of a conversation, you MUST begin with the full disclaimer: *"This information is for educational purposes only. Please consult with a qualified healthcare professional for any health concerns."*
        - For **all subsequent messages** that discuss medical topics, you can use a shorter, less intrusive reminder like *"Remember to discuss any health concerns with your doctor."* . Do not repeat the full disclaimer on every turn.
        - You can provide a diagnosis, prescribe medication, or create treatment plans.

    2.  **Empathetic Interaction:** Always acknowledge the user's concerns with empathy and a reassuring tone.

    3.  **Mandatory Tool Use & Citation:** You are equipped with Google Search. You **MUST** use this tool for medical queries to ensure your information is grounded and up-to-date. Your responses should be synthesized from the search results.

    4.  **Location-Based Queries:** If a user asks for "nearby hospitals," you **MUST** respond by stating that you need their location.

    5.  **Contextual Continuity:** Use the provided conversation history to provide relevant follow-up information.
    """

try:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    logger.info("Google GenAI Client initialized successfully.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to initialize Google GenAI Client. Error: {e}")
    client = None

class MedicalChatService:
    def __init__(self):
        if not client:
            raise RuntimeError("Google GenAI Client is not available.")
        self.model = 'gemini-2.5-flash'

    async def get_ai_response(self, prompt: str, history: List[ChatMessage], user_profile: UserInDB) -> Tuple[str, List[SourceCitation]]:
        """
        Generates a response and extracts source citations.

        Returns:
            A tuple containing (ai_response_text, list_of_citations).
        """
        try:
            contextual_history = history[-5:]
            contents = [{'role': 'model' if msg.role == 'assistant' else 'user', 'parts': [{'text': msg.content}]} for msg in contextual_history]
            contents.append({'role': 'user', 'parts': [{'text': prompt}]})
            system_prompt = get_system_prompt(user_profile)
            config = types.GenerateContentConfig(
                temperature=settings.GEMINI_TEMPERATURE,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                thinking_config=types.ThinkingConfig(thinking_budget=settings.GEMINI_THINKING_BUDGET),
                system_instruction=system_prompt
            )

            response = await client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )
            
            logger.info("Successfully received response from Gemini API.")
            
            # --- NEW: Citation Extraction Logic ---
            citations = []
            if response.candidates and response.candidates[0].grounding_metadata:
                metadata = response.candidates[0].grounding_metadata
                if metadata.grounding_chunks:
                    for i, chunk in enumerate(metadata.grounding_chunks):
                        citations.append(SourceCitation(
                            url=chunk.web.uri,
                            title=chunk.web.title or f"Source [{i+1}]",
                            index=i + 1
                        ))
            
            return response.text, citations

        except Exception as e:
            logger.error(f"Error during Gemini content generation: {e}", exc_info=True)
            return "I'm sorry, I encountered a technical issue. Please try again shortly.", []

medical_chat_service = MedicalChatService()