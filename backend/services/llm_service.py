"""
Tax Intelligence Platform — LLM Service Layer

Interface to Qwen3-8B via Ollama REST API.
"""

import json
import logging

from backend.services.model_service import ModelService

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.model_service = ModelService()

    async def is_available(self) -> bool:
        """Check if Ollama is available."""
        return await self.model_service.is_llm_available()

    async def generate(self, prompt: str, system: str = None, temperature: float = 0.3) -> str:
        """Generate text using Ollama."""
        client = self.model_service.get_llm_client()
        
        payload = {
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        if system:
            payload["system"] = system

        try:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")
        except Exception as e:
            logger.error("LLM generation failed: %s", e)
            return "Error: Unable to connect to the AI service. Please ensure Ollama is running."

    async def generate_stream(self, prompt: str, system: str = None, temperature: float = 0.3):
        """Generate streaming text using Ollama."""
        client = self.model_service.get_llm_client()
        
        payload = {
            "model": "qwen2.5:3b",
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature
            }
        }
        if system:
            payload["system"] = system

        try:
            async with client.stream("POST", "/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
        except Exception as e:
            logger.error("LLM streaming failed: %s", e)
            yield f"Error: {e}"

    async def generate_citizen_summary(self, citizen_data: dict, stream: bool = False):
        """Generate an investigation summary for a citizen."""
        system_prompt = (
            "You are an expert tax intelligence analyst for the Government of Pakistan Federal Tax Intelligence system. "
            "Analyze the provided citizen data and provide a structured investigation summary. "
            "CRITICAL: Base your analysis STRICTLY on the provided JSON data. DO NOT include any external knowledge, public information, or news about the individual."
        )
        
        prompt = (
            f"Analyze the following citizen record and provide a structured summary covering:\n"
            f"- Risk Assessment\n"
            f"- Key Discrepancies\n"
            f"- Asset Analysis\n"
            f"- Recommended Actions\n\n"
            f"Citizen Data:\n{json.dumps(citizen_data, indent=2)}\n\n"
            f" /no_think"
        )
        
        if stream:
            return self.generate_stream(prompt, system=system_prompt, temperature=0.3)
        return await self.generate(prompt, system=system_prompt, temperature=0.3)

    async def chat(self, message: str, citizen_context: dict = None, stream: bool = False):
        """Chat with the LLM contextually."""
        system_prompt = (
            "You are Lumi, a highly secure, friendly, and helpful AI assistant for the Pakistan Federal Tax Intelligence system.\n"
            "STRICT RULES:\n"
            "1. You MUST ONLY answer questions based strictly on the provided Context Data.\n"
            "2. NEVER use your pre-trained knowledge to provide public information, news, or summaries about real people, politicians, or businesses.\n"
            "3. If a user asks about a specific person and no Context Data is provided, you MUST politely refuse and instruct the user to provide a Context ID.\n"
            "4. You may answer general questions about tax laws or how to use the system, but NO external facts about specific individuals."
        )
        
        prompt = message
        if citizen_context:
            prompt = f"Context Data:\n{json.dumps(citizen_context, indent=2)}\n\nUser Question:\n{message}"
            
        prompt += " /no_think"
        
        if stream:
            return self.generate_stream(prompt, system=system_prompt, temperature=0.3)
        return await self.generate(prompt, system=system_prompt, temperature=0.3)

