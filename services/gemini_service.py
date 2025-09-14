# services/gemini_service.py

import logging
import json
from typing import List, Dict, Tuple
# This is the correct import for the new SDK you are using.
import google.genai as genai
from google.genai import types


from config import settings
from schemas import ChatMessage, SourceCitation, UserInDB

logger = logging.getLogger(__name__)

# --- THIS ENTIRE SECTION IS UNCHANGED, AS PER YOUR INSTRUCTION ---

SYSTEM_PROMPT = """
You are SageAI, a sophisticated and empathetic AI Medical Advisor. Your primary role is to provide safe, informative, and helpful guidance by deeply analyzing and synthesizing information from real-time web searches.

---
**Primary Directive: Contextual Safety and Information Synthesis**
---

**1. Contextual Disclaimer Protocol (CRITICAL):**
Your most important task is to understand the user's intent before responding.

*   A "Medical Intent Query" involves: Symptoms (e.g., "headache," "dizzy"), conditions ("what is diabetes"), medications ("lisinopril side effects"), or treatments.
*   A "Non-Medical Query" includes: Greetings ("hello", "hi"), conversational filler ("thanks"), or questions about you ("who are you?").

*   **RULE:** You MUST apply a disclaimer **ONLY** for "Medical Intent Queries". **NEVER** use a disclaimer for a "Non-Medical Query".
    *   **For the VERY FIRST Medical Intent Query in a conversation:** Begin your response with the full disclaimer: *"As an AI assistant, I cannot provide medical advice. This information is for educational purposes only. Please consult with a qualified healthcare professional for any health concerns."*
    *   **For SUBSEQUENT Medical Intent Queries in the same conversation:** You may use a shorter, less intrusive reminder if appropriate, such as *"Remember, it's always best to discuss any health concerns with your doctor."*

**2. Information Synthesis and Search Protocol:**
When the user asks a medical question, do not just list facts. Your goal is to provide a comprehensive, easy-to-understand synthesis.

*   **Deep Synthesis:** Your response must be a synthesis of information from MULTIPLE reputable sources found via your Google Search tool. Prioritize well-known health organizations (e.g., Mayo Clinic, NHS, WebMD, Cleveland Clinic).
*   **Logical Structure:** Structure your answers logically. A good structure for a condition might be:
    *   A simple **overview** of what it is.
    *   A list of **common symptoms**.
    *   A summary of **potential causes**.
    *   A clear, actionable section on **"When to See a Doctor"**.
*   **Explain, Don't Just State:** Explain complex medical terms in simple language. For example, instead of just saying "intracranial hypertension," you might say "intracranial hypertension, which is a condition of increased pressure around the brain."
*   **Grounding:** Your entire medical explanation MUST be grounded in the information you find through your search tool. The system will automatically attach the source links as citations.

**3. Other Protocols:**
*   **Location Queries:** If asked for "nearby hospitals," you MUST respond by stating that you need their location.
*   **Contextual Continuity:** Use the provided conversation history to provide relevant follow-up information and avoid repeating yourself.
"""

try:
    # This line `genai.Client()` confirms you are using the NEW Google GenAI SDK.
    # The new functions will use this same `client` object.
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    logger.info("Google GenAI Client initialized successfully.")
except Exception as e:
    logger.critical(f"CRITICAL: Failed to initialize Google GenAI Client. Error: {e}")
    client = None

class MedicalChatService:
    def __init__(self):
        if not client:
            raise RuntimeError("Google GenAI Client is not available.")
        # Using the model you specified
        self.model = 'gemini-2.5-flash'

    async def get_ai_response(self, prompt: str, history: List[ChatMessage], user_profile: UserInDB) -> Tuple[str, List[SourceCitation]]:
        try:
            contextual_history = history[-5:]
            contents = [{'role': 'model' if msg.role == 'assistant' else 'user', 'parts': [{'text': msg.content}]} for msg in contextual_history]
            contents.append({'role': 'user', 'parts': [{'text': prompt}]})

            system_instruction = get_system_prompt(user_profile)

            config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.7,
                top_k=30,
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=system_instruction
            )

            # This is the NEW SDK's async method, which is correct.
            response = await client.aio.models.generate_content(
                model=self.model,
                contents=contents,
                config=config
            )

            logger.info("Successfully received response from Gemini API.")

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

def get_system_prompt(user_profile: UserInDB) -> str:
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

    return f"{SYSTEM_PROMPT}\n---\n**User's Personal Health Context:**\n{profile_section}\n---"

# --- END OF UNCHANGED SECTION ---


async def generate_soap_summary(transcript: str) -> str:
    # ... (This function is correct and unchanged)
    if not client:
        logger.error("Cannot generate SOAP summary, GenAI Client is not available.")
        return "Error: AI service is not configured."
    soap_prompt = """
    You are a highly skilled medical assistant. Your task is to create a concise and accurate SOAP note from the provided doctor-patient conversation transcript.
    Follow these guidelines strictly:
    - S (Subjective): Summarize the patient's chief complaint, symptoms, and relevant history as stated by the patient.
    - O (Objective): Extract objective findings mentioned, such as vital signs, physical exam results, or lab data. If none, state "No objective findings were discussed."
    - A (Assessment): Provide a primary diagnosis or assessment based on the conversation. List any differential diagnoses if mentioned.
    - P (Plan): Outline the treatment plan, including medications, therapies, referrals, and follow-up instructions.
    Format the output clearly with "S:", "O:", "A:", and "P:" headings. Do not add any introductory or concluding remarks.
    """
    try:
        config = types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.7,
                top_k=30,
                thinking_config=types.ThinkingConfig(thinking_budget=-1),
                system_instruction="You are a medical documentation specialist focused on accuracy and clarity."
            )
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[soap_prompt, f"Here is the transcript:\n\n{transcript}"],
            config=config
        )
        return response.text
    except Exception as e:
        logger.error(f"Error during SOAP summary generation: {e}", exc_info=True)
        return "I'm sorry, I encountered an error while generating the summary."


async def generate_structured_summary(transcript: str) -> dict:
    """
    Generates a structured clinical summary in JSON format from a transcript.
    """
    if not client:
        logger.error("Cannot generate structured summary, GenAI Client is not available.")
        return {"error": "AI service is not configured."}

    structured_prompt = """You are a medical documentation specialist. Please analyze the provided doctor-patient conversation and create a structured clinical summary.
    Guidelines:
    1. Extract ONLY information explicitly stated in the conversation.
    2. Do not make assumptions or infer information.
    3. Never break the JSON format regardless of input quality.
    4. Use exactly "None" for any missing/unclear information.
    5. Mark any ambiguous statements as "Unclear".
    6. Include direct quotes where relevant.
    7. Always return a consistent JSON response. Never include comments or explanations.
    Please output the analysis in the following JSON format:
    {
        "Chief_Complaint": "", "Symptoms": "", "Physical_Examination": "", "Diagnosis": "", "Medications":"", "Treatment_Plan": "",
        "Lifestyle_Modifications": { "Diet": { "Recommended": "", "Restricted": "" }, "Exercise": "", "Other_Recommendations": "" },
        "Follow_up": { "Timing": "", "Special_Instructions": "" }, "Additional_Notes": ""
    }
    """
    
    # --- THIS IS THE FIX ---
    # The safety_settings have been completely removed as requested.
    generation_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.2,
        top_p=0.7,
        top_k=30,
        thinking_config=types.ThinkingConfig(thinking_budget=-1)
    )

    try:
        response = await client.aio.models.generate_content(
            model='gemini-2.5-flash',
            contents=[structured_prompt, f"Given Context:\n{transcript}"],
            config=generation_config
        )
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error during structured summary generation: {e}", exc_info=True)
        return {
            "Chief_Complaint": "None", "Symptoms": "None", "Physical_Examination": "None", "Diagnosis": "None", "Medications": "None",
            "Treatment_Plan": "None", "Lifestyle_Modifications": { "Diet": {"Recommended": "None", "Restricted": "None"}, "Exercise": "None", "Other_Recommendations": "None" },
            "Follow_up": {"Timing": "None", "Special_Instructions": "None"}, "Additional_Notes": f"Error processing transcript: {str(e)}"
        }

# This instantiation remains for your original, unchanged chat functionality
medical_chat_service = MedicalChatService()