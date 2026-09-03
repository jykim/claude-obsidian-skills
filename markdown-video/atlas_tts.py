"""Atlas Cloud text-to-speech client with guarded async polling."""

import time
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple
from urllib.parse import quote

import requests


ATLAS_API_BASE = "https://api.atlascloud.ai"
ATLAS_CATALOG_PATH = "/api/v1/models"
DEFAULT_ATLAS_MODEL = "bytedance/seed-audio-1.0"
DEFAULT_ATLAS_SPEAKER = "zh_female_vv_uranus_bigtts"


def _data(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = payload.get("data")
    return value if isinstance(value, dict) else payload


def _read_json(response: requests.Response, operation: str) -> Dict[str, Any]:
    try:
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError(f"Atlas Cloud {operation} failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"Atlas Cloud {operation} returned invalid JSON")
    code = payload.get("code")
    if isinstance(code, int) and code not in {0, 200}:
        message = str(payload.get("message") or "unknown error")
        raise RuntimeError(f"Atlas Cloud {operation} failed (code {code}): {message}")
    return payload


class AtlasTTSClient:
    """Resolve a live audio schema, submit once, and poll within a time bound."""

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_ATLAS_MODEL,
        speaker: str = DEFAULT_ATLAS_SPEAKER,
        timeout: int = 300,
        session: Optional[requests.Session] = None,
        api_base: str = ATLAS_API_BASE,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.speaker = speaker
        self.timeout = timeout
        self.session = session or requests.Session()
        self.api_base = api_base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.create_path, self.result_path, self.input_fields = self._load_schema()

    def _load_schema(self) -> Tuple[str, str, Set[str]]:
        catalog = _read_json(
            self.session.get(f"{self.api_base}{ATLAS_CATALOG_PATH}", timeout=30),
            "model catalog",
        )
        models = catalog.get("data")
        if not isinstance(models, list):
            raise RuntimeError("Atlas Cloud model catalog has no model list")
        selected = next(
            (
                item
                for item in models
                if isinstance(item, dict) and item.get("model") == self.model
            ),
            None,
        )
        if not selected:
            raise RuntimeError(f"Atlas Cloud model is not listed: {self.model}")
        if (
            selected.get("type") != "Audio"
            or selected.get("display_console") is not True
            or not selected.get("schema")
        ):
            raise RuntimeError(f"Atlas Cloud model is not an enabled audio model: {self.model}")

        schema = _read_json(
            self.session.get(str(selected["schema"]), timeout=30),
            "model schema",
        )
        paths = schema.get("paths", {})
        if not isinstance(paths, dict):
            raise RuntimeError("Atlas Cloud model schema has no routes")
        create_path = next(
            (
                path
                for path, operations in paths.items()
                if isinstance(operations, dict) and "post" in operations
            ),
            None,
        )
        result_path = next(
            (
                path
                for path, operations in paths.items()
                if isinstance(operations, dict)
                and "get" in operations
                and "{request_id}" in path
            ),
            None,
        )
        components = schema.get("components", {})
        schemas = components.get("schemas", {}) if isinstance(components, dict) else {}
        input_schema = schemas.get("Input", {}) if isinstance(schemas, dict) else {}
        properties = input_schema.get("properties", {}) if isinstance(input_schema, dict) else {}
        if not create_path or not result_path or not isinstance(properties, dict):
            raise RuntimeError("Atlas Cloud model schema is missing generation fields")
        return create_path, result_path, set(properties)

    def _request_body(self, text: str) -> Dict[str, Any]:
        body: Dict[str, Any] = {"model": self.model, "text": text}
        if "format" in self.input_fields:
            body["format"] = "mp3"
        if self.speaker and "references" in self.input_fields:
            body["references"] = [{"speaker": self.speaker}]
        elif self.speaker and "voice" in self.input_fields:
            body["voice"] = self.speaker
        return body

    def generate(self, text: str, output_file: Path) -> None:
        # A paid generation request is issued exactly once and is never retried.
        created = _data(
            _read_json(
                self.session.post(
                    f"{self.api_base}{self.create_path}",
                    headers={**self.headers, "Content-Type": "application/json"},
                    json=self._request_body(text),
                    timeout=60,
                ),
                "generation",
            )
        )
        request_id = created.get("id") or created.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise RuntimeError("Atlas Cloud generation returned no prediction id")

        deadline = time.monotonic() + self.timeout
        delay = 2.0
        prediction: Optional[Dict[str, Any]] = None
        while time.monotonic() < deadline:
            result_url = (
                f"{self.api_base}"
                f"{self.result_path.replace('{request_id}', quote(request_id, safe=''))}"
            )
            try:
                current = _read_json(
                    self.session.get(result_url, headers=self.headers, timeout=30),
                    "prediction",
                )
            except RuntimeError:
                if time.monotonic() + delay >= deadline:
                    raise
                time.sleep(delay)
                delay = min(delay * 1.5, 15.0)
                continue

            result = _data(current)
            status = str(result.get("status", "")).lower()
            if status in {"completed", "succeeded", "success"}:
                prediction = result
                break
            if status in {"failed", "cancelled", "canceled", "timeout"}:
                raise RuntimeError(f"Atlas Cloud prediction ended with status: {status}")
            time.sleep(delay)
            delay = min(delay * 1.5, 15.0)

        if prediction is None:
            raise RuntimeError(f"Atlas Cloud prediction timed out: {request_id}")
        outputs = prediction.get("outputs")
        if not isinstance(outputs, list) or not outputs or not isinstance(outputs[0], str):
            raise RuntimeError("Atlas Cloud prediction completed without an audio URL")

        download = self.session.get(outputs[0], timeout=60)
        try:
            download.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"Atlas Cloud audio download failed: {exc}") from exc
        output_file.write_bytes(download.content)
