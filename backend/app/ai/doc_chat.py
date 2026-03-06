from typing import AsyncGenerator, Dict, Optional
import google.generativeai as genai
from app.config import get_settings

settings = get_settings()

class DocumentChat:
    """Novel Feature: Chat with documents using AI"""
    
    def __init__(self):
        if settings.google_api_key:
            genai.configure(api_key=settings.google_api_key)
            self.model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction=(
                    "You are an AI assistant helping with logistics document analysis. "
                    "You have access to the extracted text and entities from a document (LR, POD, or Invoice). "
                    "Answer questions accurately based on the document content. "
                    "If information is not available in the document, say so clearly. "
                    "Be concise and helpful."
                )
            )
        else:
            self.model = None
    
    async def chat_stream(
        self, 
        document_text: str, 
        document_entities: Dict,
        user_message: str,
        chat_history: list = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response about a document."""
        if not self.model:
            yield "Error: Google API key not configured"
            return
        
        # Build document context
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
        
        # Build multi-turn contents list for Gemini
        # Seed conversation with document context as the first exchange
        contents = [
            {"role": "user",  "parts": [f"Here is the document context:\n{context}"]},
            {"role": "model", "parts": ["I have reviewed the document. How can I help you?"]},
        ]
        
        # Append previous chat history (last 3 exchanges = 6 messages)
        if chat_history:
            for msg in chat_history[-6:]:
                role = "model" if msg.get("role") == "assistant" else "user"
                contents.append({"role": role, "parts": [msg.get("content", "")]})
        
        # Append current user question
        contents.append({"role": "user", "parts": [user_message]})
        
        try:
            response = await self.model.generate_content_async(
                contents,
                stream=True,
                generation_config=genai.GenerationConfig(max_output_tokens=500)
            )
            async for chunk in response:
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
        if not self.model:
            return "Error: Google API key not configured"
        
        context = f"""Document Content:
{document_text[:3000]}

Extracted Entities:
{document_entities}
"""
        
        try:
            response = self.model.generate_content(
                f"Document:\n{context}\n\nQuestion: {user_message}",
                generation_config=genai.GenerationConfig(max_output_tokens=500)
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
