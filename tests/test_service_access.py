import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


class ServiceAccessTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {"APP_ENV": "production", "FACE_SERVICE_API_KEY": "test-service-key"},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        # Do not start lifespan: these tests must not download or load models.
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def extract(self, key=None):
        headers = {} if key is None else {"X-API-Key": key}
        return self.client.post(
            "/extract-embedding",
            files={"image": ("invalid.jpg", b"not an image", "image/jpeg")},
            headers=headers,
        )

    def test_health_supports_get_and_post_without_credentials(self):
        for method in (self.client.get, self.client.post):
            response = method("/health")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "ok")

    def test_extraction_rejects_missing_key(self):
        self.assertEqual(self.extract().status_code, 401)

    def test_extraction_rejects_wrong_key(self):
        self.assertEqual(self.extract("wrong-key").status_code, 401)

    def test_laravel_header_allows_request_to_reach_image_validation(self):
        with patch.object(main, "face_analyzer", object()):
            response = self.extract("test-service-key")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid image file.")

    def test_production_without_key_rejects_extraction(self):
        with patch.dict(os.environ, {"FACE_SERVICE_API_KEY": ""}):
            self.assertEqual(self.extract().status_code, 503)

    def test_local_mode_can_run_without_key(self):
        with patch.dict(os.environ, {"APP_ENV": "local", "FACE_SERVICE_API_KEY": ""}):
            with patch.object(main, "face_analyzer", object()):
                self.assertEqual(self.extract().status_code, 400)


class StartupTests(unittest.IsolatedAsyncioTestCase):
    async def test_production_requires_key_before_model_download(self):
        with patch.dict(os.environ, {"APP_ENV": "production", "FACE_SERVICE_API_KEY": ""}):
            with patch.object(main, "FaceAnalysis") as model:
                with self.assertRaisesRegex(RuntimeError, "FACE_SERVICE_API_KEY"):
                    async with main.lifespan(main.app):
                        pass
                model.assert_not_called()


if __name__ == "__main__":
    unittest.main()
