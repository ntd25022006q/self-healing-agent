import requests
from config import Config


class BaseAgent:
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.config = Config.get_llm_config()

    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        """
        Generic completion generator supporting Ollama, OpenAI, and Gemini using direct HTTP requests.
        """
        provider = self.config["provider"]

        try:
            if provider == "ollama":
                return self._call_ollama(system_prompt, user_prompt, temperature)
            elif provider == "openai":
                return self._call_openai(system_prompt, user_prompt, temperature)
            elif provider == "gemini":
                return self._call_gemini(system_prompt, user_prompt, temperature)
            else:
                raise ValueError(f"Unknown LLM provider: {provider}")
        except Exception as e:
            print(f"[Agent {self.name}] Error during generation: {e}")
            return f"Error: LLM Generation failed due to network or provider error: {str(e)}"

    def _call_ollama(self, system, user, temp) -> str:
        url = f"{self.config['ollama_host']}/api/generate"
        prompt = f"System: {system}\nUser: {user}\nAssistant:"
        payload = {
            "model": self.config["ollama_model"],
            "prompt": prompt,
            "options": {
                "temperature": temp
            },
            "stream": False
        }

        response = requests.post(url, json=payload, timeout=60)
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            raise Exception(
                f"Ollama returned status {response.status_code}: {response.text}")

    def _call_openai(self, system, user, temp) -> str:
        base_url = self.config.get("openai_base_url", "https://api.openai.com/v1")
        url = f"{base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config['openai_key']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.config["openai_model"],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temp
        }

        response = requests.post(url, headers=headers,
                                 json=payload, timeout=60)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
        else:
            raise Exception(
                f"OpenAI returned status {response.status_code}: {response.text}")

    def _call_gemini(self, system, user, temp) -> str:
        # standard API endpoint for Gemini
        model = self.config["gemini_model"]
        key = self.config["gemini_key"]
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

        headers = {
            "Content-Type": "application/json"
        }

        prompt = f"{system}\n\nUser Question:\n{user}"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temp
            }
        }

        response = requests.post(url, headers=headers,
                                 json=payload, timeout=60)
        if response.status_code == 200:
            # Parse gemini response JSON
            res_json = response.json()
            try:
                content = res_json["candidates"][0]["content"]["parts"][0]["text"]
                return content.strip()
            except KeyError:
                raise Exception(
                    f"Gemini returned unexpected JSON structure: {res_json}")
        else:
            raise Exception(
                f"Gemini returned status {response.status_code}: {response.text}")


if __name__ == "__main__":
    print("Testing BaseAgent...")
    agent = BaseAgent("Test", "Tester")
    print("Agent initialized successfully.")
