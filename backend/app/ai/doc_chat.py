from typing import AsyncGenerator, Dict, Optional
from google import genai
from google.genai import types
from app.config import get_settings

settings = get_settings()

SYSTEM_INSTRUCTION = (
    "You are an AI assistant helping with logistics document analysis. "
    "You have access to the extracted text and entities from a document (LR, POD, or Invoice). "
    "Answer questions accurately based on the document content. "
    "If information is not available in the document, say so clearly. "
    "Be concise and helpful."
)

class DocumentChat:
    """Novel Feature: Chat with documents using AI"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None

    async def chat_stream(
        self,
        document_text: str,
        document_entities: Dict,
        user_message: str,
        chat_history: list = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response about a document."""
        if not self.client:
            yield "Error: Google API key not configured"
            return

        context = f"""Document Content:
{document_text[:3000]}

Extracted Entities:
- Shipment ID: {document_entities.get('shipment_id', 'N/A')}
- Amount: {document_entities.get('amount', 'N/A')}
- Date: {document_entities.get('date', 'N/A')}
- Party Name: {document_entities.get('party_name', 'N/A')}
- Origin: {document_entities.get('origin', 'N/A')}
- Destination: {document_entities.get('destination', 'N/A')}
- Vehicle Number: {document_entities.get('vehicle_number', 'N/A')}
- Weight: {document_entities.get('weight', 'N/A')}
- GST Number: {document_entities.get('gst_number', 'N/A')}
"""
        # Seed with document context as first user/model exchange
        contents = [
            types.Content(role="user",  parts=[types.Part.from_text(f"Here is the document context:\n{context}")]),
            types.Content(role="model", parts=[types.Part.from_text("I have reviewed the document. How can I help you?")]),
        ]

        # Append prior chat history (last 3 exchanges = 6 messages)
        if chat_history:
            for msg in chat_history[-6:]:
                role = "model" if msg.get("role") == "assistant" else "user"
                contents.append(
                    types.Content(role=role, parts=[types.Part.from_text(msg.get("content", ""))])
                )

        # Current user message
        contents.append(types.Content(role="user", parts=[types.Part.from_text(user_message)]))

        try:
            async for chunk in await self.client.aio.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    max_output_tokens=500,
                )
            ):
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"Error: {str(e)}"

    def chat_sync(
        self,
        document_text: str,
        document_entities: Dict,
        user_message: str
    ) -> str:
        """Synchronous chat for non-streaming use cases."""
        if not self.client:
            return "Error: Google API key not configured"

        context = f"""Document Content:
{document_text[:3000]}

Extracted Entities:
{document_entities}
"""
        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=f"Document:\n{context}\n\nQuestion: {user_message}",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    max_output_tokens=500,
                )
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
