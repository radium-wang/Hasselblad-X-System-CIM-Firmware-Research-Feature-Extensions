#!/usr/bin/env python3
import importlib.util
import tempfile
import unittest
from pathlib import Path


TOOL = Path(__file__).resolve().parents[2] / "tools" / "audit_port.py"
SPEC = importlib.util.spec_from_file_location("audit_port", TOOL)
audit_port = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit_port)


def record(digest: str) -> dict[str, object]:
    return {"size": 1, "sha256": digest}


def firmware(*, device: str, contract: bool, formats: list[str], digest: str):
    flags = {token: contract for token in audit_port.BACKEND_TOKENS}
    modes = {token: contract for token in audit_port.OBJECT_MODES}
    dependencies = {"libcommon.so": record(digest)}
    return {
        "platform": {"device": device, "android_sdk": "28", "abi": "arm64-v8a"},
        "camera_service": {"backend_contract": flags, "object_modes": modes},
        "ml_runtime": {"needed": ["libcommon.so"], "dependency_records": dependencies},
        "models": [],
        "model_formats": formats,
        "accelerator_modules": {"vision.ko": record(digest)},
        "dsp_firmware": {"dsp.fw": record(digest)},
    }


class AuditPortTests(unittest.TestCase):
    def test_build_prop_parser_ignores_comments_and_splits_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "build.prop"
            path.write_text("# comment\nro.product.name=eagle2=value\n\n", encoding="utf-8")
            self.assertEqual(
                audit_port.parse_build_prop(path),
                {"ro.product.name": "eagle2=value"},
            )

    def test_equal_contract_is_ready(self):
        source = firmware(device="same", contract=True, formats=["json.eng.enc"], digest="a")
        target = firmware(device="same", contract=True, formats=["json.eng.enc"], digest="a")
        result = audit_port.evaluate(source, target)
        self.assertTrue(result["direct_binary_transplant_ready"])
        self.assertEqual(result["blockers"], [])

    def test_real_migration_shape_is_rejected(self):
        source = firmware(device="hb722", contract=True, formats=["json.eng.enc"], digest="a")
        target = firmware(device="ec1706", contract=False, formats=["tflite.eng.enc"], digest="b")
        target["ml_runtime"]["dependency_records"] = {}
        result = audit_port.evaluate(source, target)
        self.assertFalse(result["direct_binary_transplant_ready"])
        self.assertIn("libcommon.so", result["missing_target_dependencies"])
        self.assertGreaterEqual(len(result["blockers"]), 5)

    def test_model_inventory_is_stable_and_relative(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            model = root / "model" / "ml" / "person.json.eng.enc"
            model.parent.mkdir(parents=True)
            model.write_bytes(b"model")
            inventory = audit_port.model_inventory(root)
            self.assertEqual(inventory[0]["path"], "model/ml/person.json.eng.enc")
            self.assertEqual(inventory[0]["size"], 5)


if __name__ == "__main__":
    unittest.main()
