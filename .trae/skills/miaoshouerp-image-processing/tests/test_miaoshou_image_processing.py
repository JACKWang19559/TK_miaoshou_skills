import argparse
import importlib.util
import pathlib
import sys
import types
import unittest
import tempfile
from unittest import mock


SCRIPT_PATH = pathlib.Path(__file__).parents[1] / "scripts" / "miaoshou_image_processing.py"
SPEC = importlib.util.spec_from_file_location("miaoshou_image_processing", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class MiaoshouImageProcessingTests(unittest.TestCase):
    def test_compact_json_is_stable_and_unicode_safe(self):
        self.assertEqual(
            MODULE.compact_json({"name": "白底图", "scene": 1}),
            '{"name":"白底图","scene":1}',
        )

    def test_sign_headers_matches_fixed_contract(self):
        config = MODULE.MiaoshouConfig(
            app_key="app-key",
            app_secret="app-secret",
        )
        headers = MODULE.sign_headers(
            config,
            "/open/v1/example",
            '{"a":1}',
            timestamp="1700000000",
        )
        self.assertEqual(
            headers["x-sign"],
            "66860ac4b38b4f13c604d011307684d0bbbf7490ec1e31cf6fd74451f1198b09",
        )
        self.assertEqual(headers["x-timestamp"], "1700000000")

    def test_image_urls_are_validated_deduplicated_and_ordered(self):
        urls = MODULE.validate_image_urls(
            [
                "https://example.com/a.jpg",
                "https://example.com/a.jpg",
                "http://example.com/b.png",
            ]
        )
        self.assertEqual(
            urls,
            ["https://example.com/a.jpg", "http://example.com/b.png"],
        )

    def test_invalid_image_url_is_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.validate_image_urls(["C:/tmp/a.jpg"])

    def test_remove_payload_enforces_trace_and_targets(self):
        args = types.SimpleNamespace(
            image_url=["https://example.com/a.jpg"],
            source="common_collect_box",
            collect_box_detail_id=None,
            common_collect_box_detail_id=123,
            platform=None,
            remove_watermark=True,
            remove_logo=False,
            remove_text=False,
            remove_psoriasis=False,
            area=["background", "background"],
        )
        payload = MODULE.build_remove_payload(args)
        self.assertEqual(payload["traceInfo"]["commonCollectBoxDetailId"], 123)
        self.assertEqual(payload["removeConfig"]["isRemoveWatermark"], 1)
        self.assertEqual(payload["removeConfig"]["removeAreas"], ["background"])

    def test_language_pair_searches_across_modes(self):
        support = {
            "aeAi": {
                "realTime": {"zh": ["en", "ja"]},
                "idle": {"en": ["zh"]},
            }
        }
        MODULE.validate_language_pair(support, "aeAi", "zh", "en")
        with self.assertRaises(ValueError):
            MODULE.validate_language_pair(support, "aeAi", "zh", "fr")

    def test_translation_exclusions_use_api_enum_values(self):
        args = types.SimpleNamespace(
            image_url=["https://example.com/a.jpg"],
            source_lang="zh",
            target_lang="en",
            platform="aeAi",
            exclude_product_text=False,
            exclude_brand=True,
        )
        payload = MODULE.build_translate_payload(args)
        self.assertEqual(payload["noTranslateImageTextOptions"], ["brand"])

    def test_derived_image_urls_collects_only_successes(self):
        response = {
            "data": {
                "imgMattingList": [
                    {"result": "success", "newImageUrl": "https://example.com/a.jpeg"},
                    {"result": "fail", "newImageUrl": "https://example.com/b.jpeg"},
                ]
            }
        }
        self.assertEqual(MODULE.derived_image_urls(response), ["https://example.com/a.jpeg"])

    def test_download_derived_images_saves_without_overwrite(self):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.headers.get.return_value = "image/png"
        response.read.return_value = b"png-data"
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(
            MODULE.urllib.request, "urlopen", return_value=response
        ):
            first = MODULE.download_derived_images(["https://example.com/result"], directory, timeout=5)
            second = MODULE.download_derived_images(["https://example.com/result"], directory, timeout=5)
            self.assertEqual(first[0]["status"], "saved")
            self.assertNotEqual(first[0]["path"], second[0]["path"])
            self.assertTrue(pathlib.Path(first[0]["path"]).exists())


if __name__ == "__main__":
    unittest.main()
