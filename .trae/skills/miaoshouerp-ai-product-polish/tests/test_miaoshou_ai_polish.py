import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "miaoshou_ai_polish.py"


def load_module():
    spec = importlib.util.spec_from_file_location("miaoshou_ai_polish", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class MiaoshouAiPolishContractTests(unittest.TestCase):
    def run_cli(self, *args, check=True):
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            check=check,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )

    def test_ai_names_preview(self):
        data = json.loads(self.run_cli("ai-names").stdout)
        self.assertEqual(data["method"], "POST")
        self.assertEqual(data["path"], "/open/v1/product/common/open_ai/get_generate_product_info_support_ai_name_list")
        self.assertEqual(data["payload"], {})

    def test_product_info_preview(self):
        payload = {
            "generateTypeList": ["title", "notes"],
            "functionModule": "createCollectBox",
            "platform": "tiktok",
            "aiName": "douBao1.6",
            "title": "Portable fan",
            "languageName": "en",
        }
        data = json.loads(self.run_cli("product-info", "--payload", json.dumps(payload)).stdout)
        self.assertEqual(data["path"], "/open/v1/product/common/open_ai/generate_product_info")
        self.assertEqual(data["payload"], payload)

    def test_edit_product_info_requires_id(self):
        payload = {
            "generateTypeList": ["title"],
            "functionModule": "editItem",
            "platform": "tiktok",
            "aiName": "douBao1.6",
            "title": "Portable fan",
            "languageName": "en",
        }
        result = self.run_cli("product-info", "--payload", json.dumps(payload), check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("functionModuleProductId is required", result.stderr)

    def test_sku_spec_preserves_ids_and_images(self):
        payload = {
            "platform": "tiktok",
            "aiName": "douBao1.6",
            "functionModule": "createCollectBox",
            "skuPropertyList": [{
                "attrName": "颜色",
                "attrId": "a1",
                "attrValueList": [{
                    "attrValueId": "v1",
                    "attrValue": "红色",
                    "imgUrl": "https://example.com/red.jpg",
                    "supplementarySkuImageUrls": ["https://example.com/red-2.jpg"],
                }],
            }],
        }
        data = json.loads(self.run_cli("sku-spec", "--payload", json.dumps(payload)).stdout)
        self.assertEqual(data["payload"], payload)

    def test_live_request_does_not_print_session_values(self):
        module = load_module()
        args = mock.Mock(
            execute=True,
            config=None,
            base_url="https://example.test",
            timeout=10,
            apifox_debug=False,
        )
        response = mock.MagicMock()
        response.read.return_value = b'{"result":"success","code":"200","data":{}}'
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        with mock.patch.dict(
            module.os.environ,
            {"MIAOSHOU_COOKIE": "SECRET_COOKIE", "MIAOSHOU_TIMER_TOKEN": "SECRET_TOKEN"},
            clear=False,
        ), mock.patch.object(module.urllib.request, "urlopen", return_value=response) as urlopen, mock.patch("sys.stdout"):
            module.call_api("languages", {}, args)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("Cookie"), "SECRET_COOKIE")
        self.assertIn("timerToken=SECRET_TOKEN", request.full_url)


if __name__ == "__main__":
    unittest.main()
