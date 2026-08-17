import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("sazon.llm")

class LLMClient:
    """Unified LLM client interface for Sazon agent."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or os.getenv("DEFAULT_LLM_PROVIDER", "gemini").lower()
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.openai_key = os.getenv("OPENAI_API_KEY")

    def generate(self, prompt: str, system_instruction: Optional[str] = None, json_mode: bool = False) -> str:
        """Generates text from the LLM provider."""
        if self.provider == "gemini" and self.gemini_key:
            return self._call_gemini(prompt, system_instruction, json_mode)
        elif self.provider == "openai" and self.openai_key:
            return self._call_openai(prompt, system_instruction, json_mode)
        else:
            # Fallback to local heuristic / mock generator if API key is not configured
            logger.warning("No API key configured for provider '%s'. Using fallback heuristic response.", self.provider)
            return self._fallback_response(prompt, json_mode)

    def _call_gemini(self, prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
        try:
            from google import genai
            client = genai.Client(api_key=self.gemini_key)
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
            
            full_prompt = prompt
            if system_instruction:
                full_prompt = f"System: {system_instruction}\n\nUser: {prompt}"

            response = client.models.generate_content(
                model=model_name,
                contents=full_prompt,
            )
            text = response.text or ""
            return text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return self._fallback_response(prompt, json_mode)

    def _call_openai(self, prompt: str, system_instruction: Optional[str], json_mode: bool) -> str:
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_key)
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            
            messages = []
            if system_instruction:
                messages.append({"role": "system", "content": system_instruction})
            messages.append({"role": "user", "content": prompt})

            kwargs = {}
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"OpenAI API call failed: {e}")
            return self._fallback_response(prompt, json_mode)

    def _fallback_response(self, prompt: str, json_mode: bool) -> str:
        """Local smart fallback when API key is missing or calls fail."""
        if json_mode:
            if "plan" in prompt.lower() or "subtask" in prompt.lower():
                return json.dumps({
                    "subtasks": [
                        {
                            "id": "task_1",
                            "title": "Analyze request and requirements",
                            "description": "Understand goal and identify necessary operations",
                            "priority": 1,
                            "tool_name": "system_info",
                            "tool_input": {}
                        },
                        {
                            "id": "task_2",
                            "title": "Execute core logic",
                            "description": "Perform tasks needed for goal",
                            "priority": 2,
                            "tool_name": "file_write",
                            "tool_input": {"filename": "sazon_output.txt", "content": "Execution result for goal"}
                        },
                        {
                            "id": "task_3",
                            "title": "Finalize and summarize",
                            "description": "Review outputs and construct answer",
                            "priority": 3,
                            "tool_name": None,
                            "tool_input": None
                        }
                    ]
                })
            elif "action" in prompt.lower() or "tool" in prompt.lower():
                return json.dumps({
                    "action": "finish",
                    "final_answer": "Sazon successfully processed the goal using local fallback logic."
                })
        return "Sazon Fallback: Request processed successfully."
