"""
API TEST CLI - High-Performance AI API Client & Diagnostics Engine
"""

import time
import json
import httpx
from typing import Dict, Any, List, Optional, Callable, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    Computes summary statistical metrics (min, max, mean, median, p95, stdev)
    for latency and throughput arrays.
    """
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0, "stdev": 0.0}
    sorted_v = sorted(values)
    n = len(sorted_v)
    min_v = sorted_v[0]
    max_v = sorted_v[-1]
    mean_v = sum(sorted_v) / n
    if n % 2 == 1:
        median_v = sorted_v[n // 2]
    else:
        median_v = (sorted_v[n // 2 - 1] + sorted_v[n // 2]) / 2.0

    idx_p95 = int(round(0.95 * (n - 1)))
    p95_v = sorted_v[min(idx_p95, n - 1)]

    if n > 1:
        variance = sum((x - mean_v) ** 2 for x in sorted_v) / (n - 1)
        stdev_v = variance ** 0.5
    else:
        stdev_v = 0.0

    return {
        "min": round(min_v, 2),
        "max": round(max_v, 2),
        "mean": round(mean_v, 2),
        "median": round(median_v, 2),
        "p95": round(p95_v, 2),
        "stdev": round(stdev_v, 2),
    }


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
        full_reasoning_text = ""
        chunk_count = 0
        reasoning_chunk_count = 0
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
                                "reasoning_text": "",
                                "headers": response_headers,
                            }

                        # Save working route
                        self._working_base_url = chat_url.rsplit("/chat/completions", 1)[0]

                        if status_callback:
                            status_callback("Streaming response tokens...")

                        full_reasoning_text = ""
                        full_response_text = ""
                        chunk_count = 0
                        reasoning_chunk_count = 0

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
                                        reasoning_delta = delta.get("reasoning_content") or delta.get("reasoning") or ""
                                        content_delta = delta.get("content") or delta.get("text") or ""

                                        if reasoning_delta:
                                            if t_first_token is None:
                                                t_first_token = time.perf_counter()
                                            full_reasoning_text += reasoning_delta
                                            reasoning_chunk_count += 1
                                            if chunk_callback:
                                                elapsed_ms = (time.perf_counter() - t_start) * 1000.0
                                                chunk_callback(reasoning_delta, {
                                                    "elapsed_ms": round(elapsed_ms, 1),
                                                    "is_reasoning": True,
                                                })

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
                                                    "is_reasoning": False,
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
                            "reasoning_text": full_reasoning_text,
                            "headers": response_headers,
                        }

        if t_end is None:
            t_end = time.perf_counter()

        # Handle models that output <think>...</think> in standard content
        if not full_reasoning_text and "<think>" in full_response_text and "</think>" in full_response_text:
            parts = full_response_text.split("</think>", 1)
            full_reasoning_text = parts[0].replace("<think>", "").strip()
            full_response_text = parts[1].strip()

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
            "reasoning_text": full_reasoning_text,
            "reasoning_tokens": max(reasoning_chunk_count, len(full_reasoning_text.split())) if full_reasoning_text else 0,
            "headers": response_headers,
        }

    def test_single_chat_request(
        self,
        model_id: str,
        prompt: str = "Say hello in one word.",
        max_tokens: int = 25,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        """
        Sends a single non-streaming or fast chat request for health or concurrency stress testing.
        """
        candidate_chat_urls = self.get_candidate_chat_urls()
        headers = self._get_headers()
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.0,
        }

        t_start = time.perf_counter()
        with httpx.Client(timeout=timeout, verify=True) as client:
            for chat_url in candidate_chat_urls:
                try:
                    res = client.post(chat_url, headers=headers, json=payload)
                    latency_ms = (time.perf_counter() - t_start) * 1000.0
                    if res.is_success:
                        self._working_base_url = chat_url.rsplit("/chat/completions", 1)[0]
                        data = res.json()
                        usage = data.get("usage", {})
                        completion_tokens = usage.get("completion_tokens", 0)
                        if not completion_tokens:
                            choices = data.get("choices", [])
                            if choices:
                                content = choices[0].get("message", {}).get("content", "")
                                completion_tokens = max(1, len(content.split()))
                        return {
                            "success": True,
                            "status_code": res.status_code,
                            "latency_ms": round(latency_ms, 2),
                            "tokens": completion_tokens,
                            "error": None,
                        }
                    else:
                        code, err_msg = self._format_error(None, res)
                        if res.status_code == 404 and len(candidate_chat_urls) > 1 and chat_url == candidate_chat_urls[0]:
                            continue
                        return {
                            "success": False,
                            "status_code": code,
                            "latency_ms": round(latency_ms, 2),
                            "tokens": 0,
                            "error": err_msg,
                        }
                except Exception as exc:
                    code, err_msg = self._format_error(exc, None)
                    if chat_url == candidate_chat_urls[-1]:
                        latency_ms = (time.perf_counter() - t_start) * 1000.0
                        return {
                            "success": False,
                            "status_code": code,
                            "latency_ms": round(latency_ms, 2),
                            "tokens": 0,
                            "error": err_msg,
                        }
        return {
            "success": False,
            "status_code": 0,
            "latency_ms": round((time.perf_counter() - t_start) * 1000.0, 2),
            "tokens": 0,
            "error": "Failed to connect to candidate endpoints",
        }

    def run_multi_run_benchmark(
        self,
        model_id: str,
        prompt: str = "Explain quantum computing in 2 short sentences.",
        runs: int = 3,
        max_tokens: int = 300,
        chunk_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes multiple benchmark runs to compute percentile latency, throughput variance,
        and stability scoring.
        """
        runs = max(1, runs)
        individual_runs: List[Dict[str, Any]] = []

        for i in range(1, runs + 1):
            run_result = self.run_stream_benchmark(
                model_id=model_id,
                prompt=prompt,
                max_tokens=max_tokens,
                chunk_callback=chunk_callback if runs == 1 else None,
            )
            run_result["run_number"] = i
            individual_runs.append(run_result)
            if progress_callback:
                progress_callback(i, runs, run_result)

        successful_runs = [r for r in individual_runs if r.get("success")]
        failed_runs = [r for r in individual_runs if not r.get("success")]

        if not successful_runs:
            last_err = failed_runs[-1].get("error") if failed_runs else "All benchmark runs failed"
            return {
                "success": False,
                "model": model_id,
                "prompt": prompt,
                "total_runs": runs,
                "successful_runs": 0,
                "failed_runs": len(failed_runs),
                "error": last_err,
                "runs": individual_runs,
            }

        ttft_values = [r["ttft_ms"] for r in successful_runs]
        tps_values = [r["tps"] for r in successful_runs]
        total_lat_values = [r["total_latency_ms"] for r in successful_runs]
        gen_lat_values = [r.get("generation_latency_ms", 0.0) for r in successful_runs]
        tokens_values = [r["tokens"] for r in successful_runs]

        stats_ttft = calculate_statistics(ttft_values)
        stats_tps = calculate_statistics(tps_values)
        stats_total_lat = calculate_statistics(total_lat_values)
        stats_gen_lat = calculate_statistics(gen_lat_values)

        if stats_tps["mean"] > 0 and len(successful_runs) > 1:
            cv = (stats_tps["stdev"] / stats_tps["mean"]) * 100.0
            stability_score = max(0.0, min(100.0, round(100.0 - cv, 1)))
        else:
            stability_score = 100.0

        cold_start_ttft = successful_runs[0]["ttft_ms"]
        warm_runs = successful_runs[1:]
        warm_ttft = round(sum(r["ttft_ms"] for r in warm_runs) / len(warm_runs), 2) if warm_runs else cold_start_ttft
        latest_successful = successful_runs[-1]

        return {
            "success": True,
            "model": model_id,
            "prompt": prompt,
            "total_runs": runs,
            "successful_runs": len(successful_runs),
            "failed_runs": len(failed_runs),
            "error": None,
            "stats": {
                "ttft": stats_ttft,
                "tps": stats_tps,
                "total_latency": stats_total_lat,
                "generation_latency": stats_gen_lat,
                "stability_score": stability_score,
                "cold_start_ttft_ms": cold_start_ttft,
                "warm_ttft_ms": warm_ttft,
                "avg_tokens": round(sum(tokens_values) / len(tokens_values), 1),
            },
            "ttft_ms": stats_ttft["median"],
            "tps": stats_tps["median"],
            "total_latency_ms": stats_total_lat["median"],
            "generation_latency_ms": stats_gen_lat["median"],
            "tokens": int(round(sum(tokens_values) / len(tokens_values))),
            "response_text": latest_successful.get("response_text", ""),
            "reasoning_text": latest_successful.get("reasoning_text", ""),
            "runs": individual_runs,
        }

    def run_model_comparison(
        self,
        model_ids: List[str],
        prompt: str = "Explain quantum computing in 2 short sentences.",
        runs_per_model: int = 1,
        max_tokens: int = 300,
        progress_callback: Optional[Callable[[int, int, str, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Benchmarks multiple models head-to-head against the identical prompt and
        determines winner badges for TTFT, Throughput, and Latency.
        """
        model_results: List[Dict[str, Any]] = []
        total_models = len(model_ids)

        for idx, m_id in enumerate(model_ids, 1):
            if runs_per_model > 1:
                res = self.run_multi_run_benchmark(
                    model_id=m_id,
                    prompt=prompt,
                    runs=runs_per_model,
                    max_tokens=max_tokens,
                )
            else:
                res = self.run_stream_benchmark(
                    model_id=m_id,
                    prompt=prompt,
                    max_tokens=max_tokens,
                )
            model_results.append(res)
            if progress_callback:
                progress_callback(idx, total_models, m_id, res)

        successful = [r for r in model_results if r.get("success")]

        winners = {}
        if successful:
            fastest_ttft = min(successful, key=lambda x: x.get("ttft_ms", float("inf")))
            highest_tps = max(successful, key=lambda x: x.get("tps", 0.0))
            lowest_latency = min(successful, key=lambda x: x.get("total_latency_ms", float("inf")))

            winners = {
                "fastest_ttft": {
                    "model": fastest_ttft["model"],
                    "value": fastest_ttft.get("ttft_ms", 0.0),
                },
                "highest_tps": {
                    "model": highest_tps["model"],
                    "value": highest_tps.get("tps", 0.0),
                },
                "lowest_latency": {
                    "model": lowest_latency["model"],
                    "value": lowest_latency.get("total_latency_ms", 0.0),
                },
            }

        return {
            "prompt": prompt,
            "total_models": total_models,
            "successful_models": len(successful),
            "models": model_results,
            "winners": winners,
        }

    def run_stress_test(
        self,
        model_id: str,
        prompt: str = "Say hello in one word.",
        concurrency: int = 5,
        total_requests: int = 15,
        max_tokens: int = 30,
        progress_callback: Optional[Callable[[int, int, Dict[str, Any]], None]] = None,
    ) -> Dict[str, Any]:
        """
        Executes concurrent load and rate-limit testing against an endpoint.
        Measures success rate %, concurrency degradation, P95 latency, and aggregate TPS.
        """
        results: List[Dict[str, Any]] = []
        completed = 0
        t0 = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(self.test_single_chat_request, model_id, prompt, max_tokens)
                for _ in range(total_requests)
            ]
            for f in as_completed(futures):
                completed += 1
                try:
                    res = f.result()
                except Exception as exc:
                    res = {
                        "success": False,
                        "status_code": 0,
                        "latency_ms": 0.0,
                        "tokens": 0,
                        "error": str(exc),
                    }
                results.append(res)
                if progress_callback:
                    progress_callback(completed, total_requests, res)

        duration_sec = max(0.001, time.perf_counter() - t0)
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        total_tokens = sum(r.get("tokens", 0) for r in successful)

        error_breakdown: Dict[str, int] = {}
        for r in failed:
            err = r.get("error") or f"HTTP {r.get('status_code')}"
            error_breakdown[err] = error_breakdown.get(err, 0) + 1

        latencies = [r["latency_ms"] for r in successful] if successful else []
        stats_lat = calculate_statistics(latencies)

        aggregate_tps = round(total_tokens / duration_sec, 2) if duration_sec > 0 else 0.0
        success_rate = round((len(successful) / total_requests) * 100.0, 1)

        return {
            "model": model_id,
            "concurrency": concurrency,
            "total_requests": total_requests,
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate_pct": success_rate,
            "duration_sec": round(duration_sec, 2),
            "aggregate_tps": aggregate_tps,
            "total_tokens": total_tokens,
            "latency_stats": stats_lat,
            "error_breakdown": error_breakdown,
            "results": results,
        }
