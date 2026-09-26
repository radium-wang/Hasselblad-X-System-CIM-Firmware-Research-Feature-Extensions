#!/usr/bin/env python3
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


TOOL = Path(__file__).resolve().parents[2] / "tools" / "audit_symbol_surface.py"
SPEC = importlib.util.spec_from_file_location("audit_symbol_surface", TOOL)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(audit)


class SymbolSurfaceTests(unittest.TestCase):
    def test_strong_imports_and_export_visibility(self):
        # The mock isolates report logic from large external firmware inputs.
        source = Path("source")
        target = Path("target")

        def symbols(path):
            if path == source / "bin" / "dji_ml":
                return {"common", "new"}, set()
            return {"common"}, set()

        def libraries(path):
            if path == source:
                return {"libshared.so": {"common", "new"}}
            return {"libshared.so": {"common"}}

        with patch.object(audit, "dynamic_symbols", side_effect=symbols), patch.object(
            audit, "library_exports", side_effect=libraries
        ):
            result = audit.build_report(source, target)
        self.assertEqual(result["source_imports_missing_in_target_count"], 1)
        self.assertFalse(result["direct_runtime_substitution_symbol_complete"])
        self.assertEqual(
            result["source_imports_missing_in_target"],
            [{"symbol": "new", "source_providers": ["libshared.so"], "source_only_providers": []}],
        )
        self.assertEqual(result["target_unresolved_in_target"], [])


if __name__ == "__main__":
    unittest.main()
