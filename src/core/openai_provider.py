import json
import os
import time
import urllib.error
import urllib.request
from typing import Dict, Any, Optional, Generator
from src.core.llm_provider import LLMProvider

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.use_system_proxy = os.getenv("OPENAI_USE_SYSTEM_PROXY", "false").lower() in {"1", "true", "yes", "on"}
        self.client = OpenAI(api_key=self.api_key) if OpenAI else None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        messages = self._build_messages(prompt, system_prompt)

        if self.client:
            content, usage = self._generate_with_sdk(messages)
        else:
            content, usage = self._generate_with_rest(messages)

        end_time = time.time()
        latency_ms = int((end_time - start_time) * 1000)

        return {
            "content": content,
            "usage": usage,
            "latency_ms": latency_ms,
            "provider": "openai"
        }

    def _build_messages(self, prompt: str, system_prompt: Optional[str] = None) -> list:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _generate_with_sdk(self, messages: list) -> tuple[str, Dict[str, Any]]:
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
        )
        content = response.choices[0].message.content
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        return content, usage

    def _generate_with_rest(self, messages: list) -> tuple[str, Dict[str, Any]]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY chưa được cấu hình trong file .env.")

        body = json.dumps({
            "model": self.model_name,
            "messages": messages,
        }).encode("utf-8")

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        opener = urllib.request.build_opener() if self.use_system_proxy else urllib.request.build_opener(
            urllib.request.ProxyHandler({})
        )

        try:
            with opener.open(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            message = "OpenAI API request failed."
            try:
                message = json.loads(detail).get("error", {}).get("message", message)
            except json.JSONDecodeError:
                pass

            if exc.code == 401:
                raise RuntimeError(
                    "OPENAI_API_KEY không hợp lệ hoặc đã bị thu hồi. Hãy cập nhật key hợp lệ trong file .env rồi restart server."
                ) from exc
            if exc.code == 403:
                raise RuntimeError(
                    "OpenAI API key không có quyền truy cập model này hoặc tài khoản chưa đủ quyền."
                ) from exc
            raise RuntimeError(f"OpenAI API error {exc.code}: {message}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Không kết nối được tới OpenAI API. Mình đã bỏ qua proxy hệ thống mặc định; "
                "hãy kiểm tra internet/VPN/firewall hoặc đặt OPENAI_BASE_URL nếu bạn dùng API gateway riêng."
            ) from exc

        content = payload["choices"][0]["message"]["content"]
        usage = payload.get("usage", {})
        return content, {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        messages = self._build_messages(prompt, system_prompt)

        if not self.client:
            yield self.generate(prompt, system_prompt=system_prompt)["content"]
            return

        stream = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            stream=True
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
