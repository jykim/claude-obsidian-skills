import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from atlas_tts import AtlasTTSClient


class FakeResponse:
    def __init__(self, payload=None, content=b"", status_code=200):
        self.payload = payload
        self.content = content
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.post_calls = []
        self.predictions = [
            FakeResponse({"data": {"status": "processing"}}),
            FakeResponse(
                {
                    "data": {
                        "status": "completed",
                        "outputs": ["https://cdn/audio.mp3"],
                    }
                }
            ),
        ]

    def get(self, url, **kwargs):
        if url.endswith("/api/v1/models"):
            return FakeResponse(
                {
                    "data": [
                        {
                            "model": "audio/model",
                            "type": "Audio",
                            "display_console": True,
                            "schema": "https://schema/model.json",
                        }
                    ]
                }
            )
        if url == "https://schema/model.json":
            return FakeResponse(
                {
                    "paths": {
                        "/create": {"post": {}},
                        "/prediction/{request_id}": {"get": {}},
                    },
                    "components": {
                        "schemas": {
                            "Input": {
                                "properties": {
                                    "model": {},
                                    "text": {},
                                    "format": {},
                                    "references": {},
                                }
                            }
                        }
                    },
                }
            )
        if "/prediction/" in url:
            return self.predictions.pop(0)
        if url == "https://cdn/audio.mp3":
            return FakeResponse(content=b"ID3audio")
        raise AssertionError(f"unexpected GET {url}")

    def post(self, url, **kwargs):
        self.post_calls.append((url, kwargs))
        return FakeResponse({"data": {"id": "prediction-1", "status": "created"}})


class AtlasTTSClientTest(unittest.TestCase):
    def test_generation_submits_once_and_downloads_completed_audio(self):
        session = FakeSession()
        client = AtlasTTSClient(
            api_key="test-key",
            model="audio/model",
            speaker="speaker-1",
            timeout=10,
            session=session,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "speech.mp3"
            with patch("atlas_tts.time.sleep"):
                client.generate("hello", output)
            self.assertEqual(output.read_bytes(), b"ID3audio")

        self.assertEqual(len(session.post_calls), 1)
        self.assertEqual(
            session.post_calls[0][1]["json"],
            {
                "model": "audio/model",
                "text": "hello",
                "format": "mp3",
                "references": [{"speaker": "speaker-1"}],
            },
        )


if __name__ == "__main__":
    unittest.main()
