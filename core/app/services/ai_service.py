"""
AIDA-CRM AI Service
OpenRouter integration for lead qualification and content generation
"""

import httpx
import json
from typing import Dict, Any, List, Optional
import structlog

from ..core.config import settings

logger = structlog.get_logger()


class AIService:
    """AI service for lead qualification and automation"""

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.openrouter_model
        self.client = httpx.AsyncClient(timeout=30.0)

    async def qualify_lead(self, lead_data: Dict[str, Any]) -> float:
        """AI-powered lead qualification scoring"""
        try:
            prompt = self._build_qualification_prompt(lead_data)

            response = await self._make_llm_request(
                prompt=prompt,
                system_message="You are an expert sales qualification AI. Analyze leads and return only a qualification score between 0.0 and 1.0 as a single number."
            )

            # Extract score from response
            score = self._extract_score_from_response(response)
            return score

        except Exception as e:
            logger.error("Lead qualification failed", error=str(e))
            return 0.5  # Default score

    async def generate_email_content(
        self,
        lead_data: Dict[str, Any],
        email_type: str = "welcome",
        personalization_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Generate personalized email content"""
        try:
            prompt = self._build_email_prompt(lead_data, email_type, personalization_data)

            response = await self._make_llm_request(
                prompt=prompt,
                system_message="You are an expert email marketing copywriter. Create engaging, personalized emails that drive conversions. Return only valid JSON with 'subject' and 'content' fields."
            )

            # Parse email content
            return self._parse_email_response(response)

        except Exception as e:
            logger.error("Email generation failed", error=str(e))
            return {
                "subject": "Welcome to AIDA-CRM",
                "content": "Thank you for your interest in our platform!"
            }

    async def analyze_lead_intent(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze lead intent and suggest next actions"""
        try:
            prompt = self._build_intent_analysis_prompt(lead_data)

            response = await self._make_llm_request(
                prompt=prompt,
                system_message="You are an expert at analyzing customer intent. Return only valid JSON with 'intent_score', 'primary_intent', 'urgency_level', and 'recommended_actions' fields."
            )

            return self._parse_intent_response(response)

        except Exception as e:
            logger.error("Intent analysis failed", error=str(e))
            return {
                "intent_score": 0.5,
                "primary_intent": "unknown",
                "urgency_level": "medium",
                "recommended_actions": ["follow_up_email"]
            }

    async def _make_llm_request(self, prompt: str, system_message: str) -> str:
        """Make request to OpenRouter API"""
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 1000
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://aida-crm.com",
                "X-Title": "AIDA-CRM"
            }

            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )

            response.raise_for_status()
            result = response.json()

            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()

            raise Exception("No response from LLM")

        except httpx.HTTPStatusError as e:
            logger.error("OpenRouter API error", status_code=e.response.status_code, response=e.response.text)
            raise
        except Exception as e:
            logger.error("LLM request failed", error=str(e))
            raise

    def _build_qualification_prompt(self, lead_data: Dict[str, Any]) -> str:
        """Build prompt for lead qualification"""
        return f"""
Analyze this lead and provide a qualification score between 0.0 (poor) and 1.0 (excellent):

Lead Information:
- Email: {lead_data.get('email', 'N/A')}
- Name: {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}
- Company: {lead_data.get('company', 'N/A')}
- Phone: {lead_data.get('phone', 'N/A')}
- Source: {lead_data.get('source', 'N/A')}
- Campaign: {lead_data.get('campaign', 'N/A')}
- UTM Params: {json.dumps(lead_data.get('utm_params', {}), indent=2)}

Qualification Criteria:
- Email quality (domain, format)
- Company presence and relevance
- Contact completeness
- Source quality and intent signals
- Campaign alignment

Return only the numeric score (e.g., 0.75).
"""

    def _build_email_prompt(
        self,
        lead_data: Dict[str, Any],
        email_type: str,
        personalization_data: Optional[Dict[str, Any]]
    ) -> str:
        """Build prompt for email generation"""
        personalization = personalization_data or {}

        return f"""
Generate a personalized {email_type} email for this lead:

Lead Information:
- Name: {lead_data.get('first_name', 'there')}
- Company: {lead_data.get('company', 'your company')}
- Source: {lead_data.get('source', 'web')}
- Campaign: {lead_data.get('campaign', 'general')}

Additional Context:
{json.dumps(personalization, indent=2)}

Email Requirements:
- Professional but friendly tone
- Personalized with lead's name and company
- Clear value proposition
- Strong call-to-action
- Mobile-friendly format
- 150-300 words

Return JSON format:
{{
  "subject": "Email subject line",
  "content": "Email body content in HTML format"
}}
"""

    def _build_intent_analysis_prompt(self, lead_data: Dict[str, Any]) -> str:
        """Build prompt for intent analysis"""
        return f"""
Analyze this lead's intent and buying signals:

Lead Data:
- Email: {lead_data.get('email', 'N/A')}
- Company: {lead_data.get('company', 'N/A')}
- Source: {lead_data.get('source', 'N/A')}
- Campaign: {lead_data.get('campaign', 'N/A')}
- UTM Params: {json.dumps(lead_data.get('utm_params', {}), indent=2)}
- Custom Fields: {json.dumps(lead_data.get('custom_fields', {}), indent=2)}

Analyze for:
- Purchase intent strength (0.0-1.0)
- Primary intent category
- Urgency level (low/medium/high)
- Recommended actions

Return JSON format:
{{
  "intent_score": 0.75,
  "primary_intent": "product_evaluation",
  "urgency_level": "medium",
  "recommended_actions": ["send_demo_link", "schedule_call"]
}}
"""

    def _extract_score_from_response(self, response: str) -> float:
        """Extract qualification score from LLM response"""
        try:
            # Try to find a number between 0 and 1
            import re
            pattern = r'(?:^|\s)(0?\.\d+|1\.0+|1|0)(?:\s|$)'
            matches = re.findall(pattern, response)

            if matches:
                score = float(matches[0])
                return min(max(score, 0.0), 1.0)

            # Fallback: try to parse the entire response as a number
            cleaned = response.strip().rstrip('.')
            score = float(cleaned)
            return min(max(score, 0.0), 1.0)

        except Exception:
            logger.warning("Could not extract score from response", response=response)
            return 0.5

    def _parse_email_response(self, response: str) -> Dict[str, str]:
        """Parse email generation response"""
        try:
            # Try to parse as JSON first
            data = json.loads(response)
            return {
                "subject": data.get("subject", "Welcome to AIDA-CRM"),
                "content": data.get("content", "Thank you for your interest!")
            }

        except json.JSONDecodeError:
            # Fallback: extract subject and content manually
            lines = response.split('\n')
            subject = "Welcome to AIDA-CRM"
            content = response

            for line in lines:
                if 'subject' in line.lower() and ':' in line:
                    subject = line.split(':', 1)[1].strip().strip('"')
                    break

            return {"subject": subject, "content": content}

    def _parse_intent_response(self, response: str) -> Dict[str, Any]:
        """Parse intent analysis response"""
        try:
            data = json.loads(response)
            return {
                "intent_score": data.get("intent_score", 0.5),
                "primary_intent": data.get("primary_intent", "unknown"),
                "urgency_level": data.get("urgency_level", "medium"),
                "recommended_actions": data.get("recommended_actions", ["follow_up"])
            }

        except json.JSONDecodeError:
            logger.warning("Could not parse intent response", response=response)
            return {
                "intent_score": 0.5,
                "primary_intent": "unknown",
                "urgency_level": "medium",
                "recommended_actions": ["follow_up"]
            }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()