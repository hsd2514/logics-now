from typing import Dict, Optional, AsyncGenerator
from openai import OpenAI
import json
from app.config import get_settings

settings = get_settings()

class NLQueryParser:
    """Novel Feature: Natural Language Query to Database Filters"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.system_prompt = """You are a query parser for a logistics document system.
Convert natural language queries into structured filters.

Available filter fields:
- vendor_name: string (party/vendor name)
- amount_min: number (minimum amount)
- amount_max: number (maximum amount)
- date_from: string (YYYY-MM-DD)
- date_to: string (YYYY-MM-DD)
- status: string (PENDING, APPROVED, REJECTED, REVIEW)
- document_type: string (LR, POD, INVOICE)
- fraud_risk: string (LOW, MEDIUM, HIGH)
- route_origin: string (origin city)
- route_destination: string (destination city)

Return ONLY valid JSON with applicable filters. Example:
{"vendor_name": "ABC Transport", "amount_min": 50000, "date_from": "2024-01-01"}

If the query is unclear, return {"error": "explanation"}.
"""
    
    def parse(self, query: str) -> Dict:
        """Parse natural language query into filters."""
        if not self.client:
            return self._fallback_parse(query)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query}
                ],
                max_tokens=200
            )
            
            result = response.choices[0].message.content
            # Try to parse JSON
            return json.loads(result)
        except json.JSONDecodeError:
            return self._fallback_parse(query)
        except Exception as e:
            return {"error": str(e)}
    
    async def parse_stream(self, query: str) -> AsyncGenerator[str, None]:
        """Stream the parsing process for UI feedback."""
        if not self.client:
            result = self._fallback_parse(query)
            yield json.dumps(result)
            return
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": query}
                ],
                stream=True,
                max_tokens=200
            )
            
            full_response = ""
            for chunk in response:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
            
        except Exception as e:
            yield json.dumps({"error": str(e)})
    
    def _fallback_parse(self, query: str) -> Dict:
        """Fallback parsing without AI."""
        import re
        from datetime import datetime, timedelta
        
        filters = {}
        query_lower = query.lower()
        
        # Amount patterns
        amount_match = re.search(r'(?:above|over|greater than|more than|>)\s*(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)', query_lower)
        if amount_match:
            filters['amount_min'] = float(amount_match.group(1).replace(',', ''))
        
        amount_max_match = re.search(r'(?:below|under|less than|<)\s*(?:rs\.?|₹|inr)?\s*(\d+(?:,\d+)*(?:\.\d+)?)', query_lower)
        if amount_max_match:
            filters['amount_max'] = float(amount_max_match.group(1).replace(',', ''))
        
        # Date patterns
        if 'last week' in query_lower:
            filters['date_from'] = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        elif 'last month' in query_lower:
            filters['date_from'] = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        elif 'today' in query_lower:
            filters['date_from'] = datetime.now().strftime('%Y-%m-%d')
            filters['date_to'] = datetime.now().strftime('%Y-%m-%d')
        
        # Status patterns
        if 'pending' in query_lower:
            filters['status'] = 'PENDING'
        elif 'approved' in query_lower:
            filters['status'] = 'APPROVED'
        elif 'rejected' in query_lower:
            filters['status'] = 'REJECTED'
        elif 'review' in query_lower:
            filters['status'] = 'REVIEW'
        
        # Document type
        if 'invoice' in query_lower:
            filters['document_type'] = 'INVOICE'
        elif 'lr' in query_lower or 'lorry receipt' in query_lower:
            filters['document_type'] = 'LR'
        elif 'pod' in query_lower or 'proof of delivery' in query_lower:
            filters['document_type'] = 'POD'
        
        # Fraud risk
        if 'high risk' in query_lower or 'fraud' in query_lower:
            filters['fraud_risk'] = 'HIGH'
        
        # Vendor name (look for "from X" pattern)
        vendor_match = re.search(r'from\s+([A-Za-z\s&]+?)(?:\s+(?:above|below|last|today|$))', query_lower)
        if vendor_match:
            filters['vendor_name'] = vendor_match.group(1).strip().title()
        
        return filters if filters else {"error": "Could not parse query. Try: 'Show invoices above 50000 from last week'"}
