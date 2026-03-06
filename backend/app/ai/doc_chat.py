from typing import AsyncGenerator, Dict, Optional
from openai import OpenAI
from app.config import get_settings

settings = get_settings()

class DocumentChat:
    """Novel Feature: Chat with documents using AI"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.system_prompt = """You are an AI assistant helping with logistics document analysis. 
You have access to the extracted text and entities from a document (LR, POD, or Invoice).
Answer questions accurately based on the document content.
If information is not available in the document, say so clearly.
Be concise and helpful."""
    
    async def chat_stream(
        self, 
        document_text: str, 
        document_entities: Dict,
        user_message: str,
        chat_history: list = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat response about a document."""
        if not self.client:
            yield "Error: OpenAI API key not configured"
            return
        
        # Build context
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
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Here is the document context:\n{context}"}
        ]
        
        # Add chat history
        if chat_history:
            messages.extend(chat_history[-6:])  # Last 3 exchanges
        
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                stream=True,
                max_tokens=500
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
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
            return "Error: OpenAI API key not configured"
        
        context = f"""Document Content:
{document_text[:3000]}

Extracted Entities:
{document_entities}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": f"Document:\n{context}\n\nQuestion: {user_message}"}
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {str(e)}"
