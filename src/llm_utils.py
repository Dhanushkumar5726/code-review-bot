"""
Shared LLM utilities for the Code Review Bot.

Provides a centralized LLM factory and retry logic.
Supports Ollama (local), Google Gemini (cloud), and Groq (cloud, free).

Set LLM_PROVIDER in .env: "ollama", "gemini", or "groq"
"""

import os
import time
import json
import requests  # pyre-ignore


class OllamaLLM:
    """
    Lightweight Ollama wrapper that uses the HTTP API directly.
    Avoids langchain-ollama library conflicts.
    """

    def __init__(self, model: str = "qwen2.5:1.5b", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def invoke(self, prompt: str):
        """Send a prompt to Ollama and return the response."""
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt if isinstance(prompt, str) else str(prompt),
            "stream": False,
            "options": {
                "temperature": self.temperature,
            },
        }

        resp = requests.post(url, json=payload, timeout=1200)
        resp.raise_for_status()
        data = resp.json()

        return _LLMResponse(data.get("response", ""))


class GroqLLM:
    """
    Lightweight Groq wrapper using the groq SDK.
    Free tier: 30 req/min, 14,400 req/day for llama-3.3-70b.
    """

    def __init__(self, model: str = "llama-3.3-70b-versatile", temperature: float = 0.1):
        from groq import Groq  # pyre-ignore
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model
        self.temperature = temperature

    def invoke(self, prompt: str):
        """Send a prompt to Groq and return the response."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt if isinstance(prompt, str) else str(prompt)}],
            temperature=self.temperature,
        )
        return _LLMResponse(response.choices[0].message.content)


class OpenAILLM:
    """
    Lightweight OpenAI wrapper using standard requests.
    Supports chat completions like gpt-4o-mini.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.1):
        self.model = model
        self.temperature = temperature
        self.api_key = os.getenv("OPENAI_API_KEY")

    def invoke(self, prompt: str):
        """Send a prompt to OpenAI API and return the response."""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is not set.")
            
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt if isinstance(prompt, str) else str(prompt)}],
            "temperature": self.temperature,
        }

        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()

        return _LLMResponse(data["choices"][0]["message"]["content"])


class _LLMResponse:
    """Simple response wrapper to match LangChain's response.content interface."""

    def __init__(self, content: str):
        self.content = content


def create_llm(temperature: float = 0.1):
    """
    Create the LLM instance based on the LLM_PROVIDER env var.

    - 'groq'   → Groq cloud (free, fast) — recommended
    - 'gemini'  → Google Gemini API
    - 'ollama'  → Ollama local model
    """
    provider = os.getenv("LLM_PROVIDER", "groq").lower()

    if provider == "groq":
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        return GroqLLM(model=model, temperature=temperature)
    elif provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
        return OllamaLLM(model=model, temperature=temperature)
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # pyre-ignore
        return ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature=temperature,
        )
    elif provider == "openai":
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        return OpenAILLM(model=model, temperature=temperature)
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER: '{provider}'. Use 'groq', 'ollama', 'gemini', or 'openai'."
        )


def invoke_with_retry(llm, prompt, max_retries: int = 5, base_delay: int = 10):
    """
    Invoke the LLM with automatic retry and exponential backoff
    for handling rate limit (429) errors.
    """
    import re

    for attempt in range(max_retries):
        try:
            return llm.invoke(prompt)
        except requests.exceptions.ReadTimeout:
            if attempt < max_retries - 1:
                print(f"     ⏳ Request timed out. Retrying ({attempt + 1}/{max_retries})...")
                time.sleep(5)
            else:
                print("\n❌ Request timed out after all retries.")
                print("   The model may be too slow for this prompt.")
                raise
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                # Try to extract the suggested retry delay from the error
                # Groq format: "Please try again in 1.446s."
                groq_match = re.search(r'try again in (\d+(?:\.\d+)?)s', error_str)
                # Other generic retry delay
                generic_match = re.search(r'retryDelay.*?(\d+)', error_str)
                
                if groq_match:
                    delay = float(groq_match.group(1)) + 1.0  # Add 1s buffer
                elif generic_match:
                    delay = int(generic_match.group(1)) + 5
                else:
                    delay = base_delay * (attempt + 1)
                
                if attempt < max_retries - 1:
                    print(f"     ⏳ Rate limited. Waiting {delay:.2f}s before retry ({attempt + 1}/{max_retries})...")
                    time.sleep(delay)
                else:
                    print("\n❌ API quota exhausted after all retries.")
                    print("   Try using Ollama (local) by setting LLM_PROVIDER=ollama in .env\n")
                    raise
            else:
                raise


def parse_json_from_response(text: str) -> list:
    """
    Extract and parse JSON array from LLM response.
    Handles cases where the JSON is wrapped in markdown code fences.
    """
    cleaned = text.strip()

    if "```json" in cleaned:
        cleaned = cleaned.split("```json")[1]
        cleaned = cleaned.split("```")[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.split("```")[0]

    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def extract_code_from_response(text: str) -> str:
    """Extract Python code from LLM response, handling code fences."""
    cleaned = text.strip()

    if "```python" in cleaned:
        cleaned = cleaned.split("```python")[1]
        cleaned = cleaned.split("```")[0]
    elif "```" in cleaned:
        cleaned = cleaned.split("```")[1]
        cleaned = cleaned.split("```")[0]

    return cleaned.strip()
