"""
API TEST CLI - High-Performance AI API Client & Diagnostics Engine
"""

import time
import json
import httpx
from typing import Dict, Any, List, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


class APIDiagnosticsClient:
    def __init__(self, base_url: str, api_key: str = "", timeout: float = 30.0):
        self.raw_base_url = base_url.strip().rstrip("/")
        self.api_key = api_key.strip()
        self.timeout = timeout
        self._working_base_url: Optional[str] = None

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "APITestCLI/1.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_candidate_models_urls(self) -> List[str]:
        """Returns candidate model catalog URLs ordered by likelihood."""
        base = self.raw_base_url
        candidates = []
        if base.endswith("/v1"):
            candidates.append(f"{base}/models")
            candidates.append(f"{base.rstrip('/v1')}/models")
        else:
            candidates.append(f"{base}/v1/models")
            candidates.append(f"{base}/models")
        return list(dict.fromkeys(candidates))

    def get_candidate_chat_urls(self) -> List[str]:
        """Returns candidate chat completion URLs ordered by likelihood."""
        if self._working_base_url:
            return [f"{self._working_base_url}/chat/completions"]

        base = self.raw_base_url
        candidates = []
        if base.endswith("/v1"):
            candidates.append(f"{base}/chat/completions")
            candidates.append(f"{base.rstrip('/v1')}/chat/completions")
        else:
            candidates.append(f"{base}/v1/chat/completions")
            candidates.append(f"{base}/chat/completions")
        return list(dict.fromkeys(candidates))

    def _format_error(self, exc: Optional[Exception], response: Optional[httpx.Response] = None) -> Tuple[int, str]:
        if response is not None:
            status = response.status_code
            try:
                err_data = response.json()
                if isinstance(err_data, dict):
                    if "error" in err_data:
                        err_obj = err_data["error"]
                        if isinstance(err_obj, dict):
                            msg = err_obj.get("message") or err_obj.get("type") or str(err_obj)
                            return status, f"HTTP {status}: {msg}"
                        return status, f"HTTP {status}: {err_obj}"
                    if "message" in err_data:
                        return status, f"HTTP {status}: {err_data['message']}"
            except Exception:
                pass

            code_meanings = {
                400: "Bad Request (Malformed payload or unsupported model parameter)",
                401: "Unauthorized (Missing, expired, or invalid API Key)",
                403: "Forbidden (Access restricted / Insufficient permissions)",
                404: "Endpoint Not Found (Path does not exist on provider)",
                408: "Request Timeout (Upstream server timed out)",
                429: "Rate Limit / Quota Exceeded (Account quota exhausted or rate limit hit)",
                500: "Internal Server Error (Provider backend crashed)",
                502: "Bad Gateway (Upstream model runner or reverse proxy unreachable)",
                503: "Service Unavailable (Provider capacity overloaded)",
                504: "Gateway Timeout (Backend did not reply in time)",
            }
            meaning = code_meanings.get(status, response.reason_phrase or "HTTP Error")
            raw_text = response.text[:100].replace("\n", " ").strip()
            if raw_text and not raw_text.startswith("<"):
                return status, f"HTTP {status}: {meaning} | {raw_text}"
            return status, f"HTTP {status}: {meaning}"

        if isinstance(exc, httpx.ConnectError):
            return 0, f"Connection Refused: Target server unreachable at {self.raw_base_url}"
        if isinstance(exc, httpx.ConnectTimeout):
            return 0, f"Connect Timeout: Host failed to respond within {self.timeout}s"
        if isinstance(exc, httpx.ReadTimeout):
            return 0, f"Read Timeout: Server accepted connection but did not answer within {self.timeout}s"
        if isinstance(exc, httpx.InvalidURL):
            return 0, f"Invalid URL Format: '{self.raw_base_url}' is not a valid endpoint"
        if isinstance(exc, httpx.RemoteProtocolError):
            return 0, f"Protocol Error: Server closed connection unexpectedly"

        return 0, f"Network Error: {type(exc).__name__} - {str(exc)}"

    def fetch_models(self) -> Dict[str, Any]:
        """
        Fetches all available models from the provider endpoint.
        Tries /v1/models and /models seamlessly.
        """
        url_candidates = self.get_candidate_models_urls()
        headers = self._get_headers()
        last_error = "Unknown error"
        last_status = 0

        t0 = time.perf_counter()
        with httpx.Client(timeout=self.timeout, verify=True) as client:
            for url in url_candidates:
                try:
                    res = client.get(url, headers=headers)
                    latency_ms = (time.perf_counter() - t0) * 1000.0

                    if res.is_success:
                        # Auto-detect working base url prefix
                        if "/v1/models" in url:
                            self._working_base_url = url.split("/models")[0]
                        else:
                            self._working_base_url = url.split("/models")[0]

                        data = res.json()
                        raw_list = []
                        if isinstance(data, dict):
                            raw_list = data.get("data", []) or data.get("models", [])
                        elif isinstance(data, list):
                            raw_list = data

                        parsed_models = []
                        for item in raw_list:
                            if isinstance(item, dict):
                                parsed_models.append({
                                    "id": item.get("id") or item.get("name") or "unknown",
                                    "owned_by": item.get("owned_by") or item.get("developer") or "unknown",
                                    "created": item.get("created"),
                                    "context_window": item.get("context_window") or item.get("context_length") or item.get("max_tokens"),
                                })
                            elif isinstance(item, str):
                                parsed_models.append({
                                    "id": item,
                                    "owned_by": "custom",
                                })

                        return {
                            "success": True,
                            "models": parsed_models,
                            "latency_ms": round(latency_ms, 2),
                            "status_code": res.status_code,
                            "endpoint_used": url,
                            "error": None,
                        }
                    else:
                        last_status, last_error = self._format_error(None, res)
                except Exception as exc:
                    last_status, last_error = self._format_error(exc, None)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "success": False,
            "models": [],
            "latency_ms": round(latency_ms, 2),
            "status_code": last_status,
            "endpoint_used": url_candidates[0] if url_candidates else self.raw_base_url,
            "error": last_error,
        }

    def test_single_model_health(self, model_id: str, timeout: float = 12.0) -> Dict[str, Any]:
        """
        Fast health probe against a specific model by querying candidate chat endpoints.
        """
        candidate_chat_urls = self.get_candidate_chat_urls()
        headers = self._get_headers()
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
            "temperature": 0.0,
        }

        t0 = time.perf_counter()
        last_status = 0
        last_error = "Unknown error"

        with httpx.Client(timeout=timeout, verify=True) as client:
            for chat_url in candidate_chat_urls:
                try:
                    res = client.post(chat_url, headers=headers, json=payload)
                    latency_ms = (time.perf_counter() - t0) * 1000.0

                    if res.is_success:
                        # Remember working base URL
                        self._working_base_url = chat_url.rsplit("/chat/completions", 1)[0]
                        return {
                            "model": model_id,
                            "status": "OK",
                            "status_code": res.status_code,
                            "latency_ms": round(latency_ms, 1),
                            "error_reason": None,
                        }
                    else:
                        last_status, last_error = self._format_error(None, res)
                        # If 404, try next candidate URL (e.g. try /v1/chat/completions)
                        if res.status_code == 404:
                            continue
                        else:
                            # If 401, 429, 500, etc., don't retry route; return actual error
                            return {
                                "model": model_id,
                                "status": "FAILED",
                                "status_code": last_status,
                                "latency_ms": round(latency_ms, 1),
                                "error_reason": last_error,
                            }
                except Exception as exc:
                    latency_ms = (time.perf_counter() - t0) * 1000.0
                    last_status, last_error = self._format_error(exc, None)

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return {
            "model": model_id,
            "status": "FAILED",
            "status_code": last_status,
            "latency_ms": round(latency_ms, 1),
            "error_reason": last_error,
        }

    def probe_all_models_parallel(
        self,
        model_ids: List[str],
        max_workers: int = 6,
        timeout: float = 12.0,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Probes all models concurrently with ThreadPoolExecutor for instant latency & status checks.
        """
        results_map: Dict[str, Dict[str, Any]] = {}
        total = len(model_ids)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_model = {
                executor.submit(self.test_single_model_health, m_id, timeout): m_id
                for m_id in model_ids
            }

            for future in as_completed(future_to_model):
                m_id = future_to_model[future]
                completed += 1
                try:
                    res = future.result()
                    results_map[m_id] = res
                except Exception as exc:
                    results_map[m_id] = {
                        "model": m_id,
                        "status": "FAILED",
                        "status_code": 0,
                        "latency_ms": None,
                        "error_reason": str(exc),
                    }

                if progress_callback:
                    progress_callback(completed, total, results_map[m_id])

        # Return in original order
        return [results_map.get(m_id, {"model": m_id, "status": "FAILED", "latency_ms": None, "error_reason": "Missing result"}) for m_id in model_ids]

    def run_stream_benchmark(
        self,
        model_id: str,
        prompt: str = "Explain quantum computing in 2 short sentences.",
        max_tokens: int = 300,
        chunk_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Runs a streaming benchmark measuring:
        - TTFT (Time To First Token) in ms
        - Total Latency in ms
        - Generation Latency (Total - TTFT) in ms
        - Token Count & Speed (Tokens Per Second)
        - Streaming text chunks (including reasoning/thinking tokens)
        """
        candidate_chat_urls = self.get_candidate_chat_urls()
        headers = self._get_headers()
        payload = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": "You are a concise, helpful AI assistant."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "stream": True,
            "temperature": 0.7,
        }

        if status_callback:
            status_callback("Connecting to API endpoint...")

        t_start = time.perf_counter()
        t_first_token: Optional[float] = None
        t_end: Optional[float] = None

        full_response_text = ""
        chunk_count = 0
        response_headers = {}
        http_status = 0
        last_error = ""

        with httpx.Client(timeout=self.timeout, verify=True) as client:
            for chat_url in candidate_chat_urls:
                try:
                    if status_callback:
                        status_callback(f"Connecting to {chat_url}...")

                    with client.stream("POST", chat_url, headers=headers, json=payload) as response:
                        http_status = response.status_code
                        response_headers = dict(response.headers)

                        if response.status_code == 404 and len(candidate_chat_urls) > 1 and chat_url == candidate_chat_urls[0]:
                            # Try next candidate chat URL
                            continue

                        if not response.is_success:
                            body_text = response.read().decode("utf-8", errors="replace")
                            status_code, error_msg = self._format_error(None, response)
                            try:
                                j = json.loads(body_text)
                                if "error" in j:
                                    e = j["error"]
                                    if isinstance(e, dict):
                                        error_msg = f"HTTP {status_code}: {e.get('message', error_msg)}"
                                    else:
                                        error_msg = f"HTTP {status_code}: {e}"
                            except Exception:
                                pass

                            return {
                                "success": False,
                                "error": error_msg,
                                "status_code": status_code,
                                "model": model_id,
                                "ttft_ms": 0.0,
                                "total_latency_ms": round((time.perf_counter() - t_start) * 1000.0, 2),
                                "tps": 0.0,
                                "tokens": 0,
                                "response_text": "",
                                "headers": response_headers,
                            }

                        # Save working route
                        self._working_base_url = chat_url.rsplit("/chat/completions", 1)[0]

                        if status_callback:
                            status_callback("Streaming response tokens...")

                        for line in response.iter_lines():
                            if not line:
                                continue
                            line_str = line.strip()
                            if line_str.startswith("data: "):
                                data_content = line_str[6:].strip()
                                if data_content == "[DONE]":
                                    break
                                try:
                                    chunk_json = json.loads(data_content)
                                    choices = chunk_json.get("choices", [])
                                    if choices:
                                        delta = choices[0].get("delta", {})
                                        # Handle standard content, reasoning content, or text
                                        content_delta = delta.get("content") or delta.get("reasoning_content") or delta.get("text") or ""
                                        if content_delta:
                                            if t_first_token is None:
                                                t_first_token = time.perf_counter()

                                            chunk_count += 1
                                            full_response_text += content_delta

                                            current_tokens = max(chunk_count, len(full_response_text.split()))

                                            if chunk_callback:
                                                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                                                ttft_current = (t_first_token - t_start) * 1000.0 if t_first_token else elapsed_ms
                                                gen_sec = max(0.001, (time.perf_counter() - t_first_token)) if t_first_token else 0.001
                                                current_tps = current_tokens / gen_sec

                                                chunk_callback(content_delta, {
                                                    "elapsed_ms": round(elapsed_ms, 1),
                                                    "ttft_ms": round(ttft_current, 1),
                                                    "tps": round(current_tps, 1),
                                                    "tokens": current_tokens,
                                                    "text_length": len(full_response_text),
                                                })
                                except Exception:
                                    continue

                        t_end = time.perf_counter()
                        break

                except Exception as exc:
                    last_status, last_error = self._format_error(exc, None)
                    if chat_url == candidate_chat_urls[-1]:
                        return {
                            "success": False,
                            "error": last_error,
                            "status_code": last_status,
                            "model": model_id,
                            "ttft_ms": round((t_first_token - t_start) * 1000.0, 2) if t_first_token else 0.0,
                            "total_latency_ms": round((time.perf_counter() - t_start) * 1000.0, 2),
                            "tps": 0.0,
                            "tokens": 0,
                            "response_text": full_response_text,
                            "headers": response_headers,
                        }

        if t_end is None:
            t_end = time.perf_counter()

        total_latency_ms = (t_end - t_start) * 1000.0
        ttft_ms = ((t_first_token - t_start) * 1000.0) if t_first_token else total_latency_ms
        generation_sec = max(0.001, (t_end - (t_first_token or t_start)))

        estimated_token_count = max(chunk_count, len(full_response_text.split()))
        tps = estimated_token_count / generation_sec if estimated_token_count > 0 else 0.0

        return {
            "success": True,
            "error": None,
            "status_code": http_status,
            "model": model_id,
            "ttft_ms": round(ttft_ms, 2),
            "total_latency_ms": round(total_latency_ms, 2),
            "generation_latency_ms": round(generation_sec * 1000.0, 2),
            "tps": round(tps, 2),
            "tokens": estimated_token_count,
            "chunk_count": chunk_count,
            "response_text": full_response_text,
            "headers": response_headers,
        }
