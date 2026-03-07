from typing import Dict, Optional, AsyncGenerator
from google import genai
from google.genai import types
import json
from app.config import get_settings

settings = get_settings()

SYSTEM_INSTRUCTION = """You are a query parser for a logistics document system.
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

class NLQueryParser:
    """Novel Feature: Natural Language Query to Database Filters"""

    def __init__(self):
        self.client = genai.Client(api_key=settings.google_api_key) if settings.google_api_key else None

    def parse(self, query: str) -> Dict:
        """Parse natural language query into filters."""
        if not self.client:
            return self._fallback_parse(query)

        try:
            response = self.client.models.generate_content(
                model="gemini-2.0-flash",
                contents=query,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    max_output_tokens=200,
                    response_mime_type="application/json",  # Force JSON output
                )
            )
            return json.loads(response.text)
        except json.JSONDecodeError:
            return self._fallback_parse(query)
        except Exception as e:
            return {"error": str(e)}

    async def parse_stream(self, query: str) -> AsyncGenerator[str, None]:
        """Stream the parsing process for UI feedback."""
        if not self.client:
            yield json.dumps(self._fallback_parse(query))
            return

        try:
            async for chunk in await self.client.aio.models.generate_content_stream(
                model="gemini-2.0-flash",
                contents=query,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    max_output_tokens=200,
                )
            ):
                if chunk.text:
                    yield chunk.text
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
            filters['date_to']   = datetime.now().strftime('%Y-%m-%d')

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
