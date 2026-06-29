import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from disclosure_anchor.settings import Settings, load_settings


def _env(root: Path) -> dict[str, str]:
    data_root = root / "services" / "disclosure_anchor"
    shared_root = root / "shared"
    return {
        "DISCLOSURE_DATA_ROOT": str(data_root),
        "DISCLOSURE_SHARED_ROOT": str(shared_root),
        "DISCLOSURE_RUNTIME_ROOT": str(data_root / "runtime"),
        "MINERU_MODEL_CACHE": str(shared_root / "model_cache" / "mineru"),
        "HF_HOME": str(shared_root / "model_cache" / "huggingface"),
        "MODELSCOPE_CACHE": str(shared_root / "model_cache" / "modelscope"),
    }


class SettingsTests(unittest.TestCase):
    def test_loads_required_environment(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, _env(Path(tmp)), clear=True):
            settings = load_settings()
            self.assertIsInstance(settings, Settings)
            self.assertEqual(settings.agent_system_root, Path(tmp))
            self.assertIsNone(settings.database_url)
            self.assertIsNone(settings.cninfo_access_key)

    def test_secrets_are_optional_and_masked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = _env(Path(tmp))
            env.update(
                {
                    "DATABASE_URL": "postgresql://user:<set-in-private-env>@127.0.0.1:55432/db",
                    "CNINFO_ACCESS_KEY": "key",
                    "CNINFO_ACCESS_SECRET": "<set-in-private-env>",
                }
            )
            with patch.dict(os.environ, env, clear=True):
                settings = load_settings()
                self.assertNotIn("<set-in-private-env>", repr(settings.database_url))
                self.assertEqual(settings.cninfo_access_key.get_secret_value(), "key")


if __name__ == "__main__":
    unittest.main()
