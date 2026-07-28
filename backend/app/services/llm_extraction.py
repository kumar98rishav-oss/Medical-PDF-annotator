import urllib.request
import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LLMExtractionService:
    """
    Service to send unstructured OCR text to a Cloud AI (OpenAI) to extract structured
    medical fields (Facility, Provider, Date, Document Type) with zero reliance on regex.
    """
    
    # We use gpt-3.5-turbo or gpt-4o-mini as cheap/fast extractors
    MODEL = "gpt-3.5-turbo"
    API_URL = "https://api.openai.com/v1/chat/completions"

    @staticmethod
    def extract_with_ai(text: str, api_key: str) -> Dict[str, Any]:
        """
        Calls OpenAI to extract structured JSON from the text.
        Requires a valid api_key.
        """
        if not api_key:
            raise ValueError("API Key is missing. Please provide a valid OpenAI API key in settings.")
            
        if not text or len(text.strip()) < 10:
            return {"facilities": [], "providers": [], "dates_of_service": [], "document_types": []}

        system_prompt = (
            "You are an expert medical coder. Extract the following entities from the "
            "provided medical document text. Return ONLY a valid JSON object matching this strict schema:\n"
            "{\n"
            '  "facilities": ["List of hospital/clinic/office names found"],\n'
            '  "providers": ["List of full doctor/provider names found"],\n'
            '  "dates_of_service": ["List of encounter dates (MM/DD/YYYY)"],\n'
            '  "document_types": ["The type of document, e.g., Progress Note, Consult Note"]\n'
            "}\n"
            "If a field is not found, return an empty array for it. Do not return markdown, just the JSON string."
        )

        payload = {
            "model": LLMExtractionService.MODEL,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract details from this medical text:\n\n{text}"}
            ],
            "temperature": 0.0  # We want factual deterministic extraction
        }

        req = urllib.request.Request(
            LLMExtractionService.API_URL,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                result = json.loads(response.read().decode('utf-8'))
                content = result['choices'][0]['message']['content']
                
                # The prompt guarantees JSON output via response_format="json_object"
                data = json.loads(content)
                
                # Ensure the keys exist to prevent frontend crashing
                return {
                    "facilities": data.get("facilities", []),
                    "providers": data.get("providers", []),
                    "dates_of_service": data.get("dates_of_service", []),
                    "document_types": data.get("document_types", [])
                }
        except Exception as e:
            logger.error(f"LLM Extraction failed: {e}")
            raise Exception(f"AI Extraction failed: {str(e)}")
