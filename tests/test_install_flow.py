"""Optional Rust setup must preserve the existing interface installation paths."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from scripts import finish_install


class FinishInstallTests(unittest.TestCase):
    def test_optional_rust_outcome_does_not_block_cli_setup(self):
        for enabled in (True, False):
            with self.subTest(enabled=enabled):
                events = []
                store = SimpleNamespace(load=lambda: {"language": "en"})

                def configure(language, *, root, events=events, enabled=enabled):
                    self.assertEqual(language, "en")
                    self.assertEqual(root, finish_install.BASE_DIR)
                    events.append("rust")
                    return enabled

                def choose(_prompt, events=events):
                    events.append("interface")
                    return "2"

                with patch.object(finish_install, "ConfigStore", return_value=store), \
                        patch.object(finish_install, "configure_rust", side_effect=configure), \
                        patch("builtins.input", side_effect=choose), \
                        patch("builtins.print"), \
                        patch.object(finish_install, "console_python", return_value="python"), \
                        patch.object(finish_install.subprocess, "call", return_value=0) as launch:
                    self.assertEqual(finish_install.main(), 0)
                self.assertEqual(events, ["rust", "interface"])
                self.assertEqual(launch.call_args.args[0],
                                 ["python", str(finish_install.BASE_DIR / "settings.py")])

    def test_python_only_choice_still_installs_and_launches_gui(self):
        store = SimpleNamespace(load=lambda: {"language": "en"})
        with patch.object(finish_install, "ConfigStore", return_value=store), \
                patch.object(finish_install, "configure_rust", return_value=False), \
                patch("builtins.input", return_value="1"), patch("builtins.print"), \
                patch.object(finish_install, "console_python", return_value="python"), \
                patch.object(finish_install.subprocess, "run") as install, \
                patch.object(finish_install.subprocess, "Popen") as launch:
            self.assertEqual(finish_install.main(), 0)
        self.assertEqual(install.call_args.args[0], ["uv", "sync", "--extra", "gui"])
        launch.assert_called_once()

    def test_existing_gui_dependency_failure_remains_an_installation_failure(self):
        store = SimpleNamespace(load=lambda: {"language": "en"})
        with patch.object(finish_install, "ConfigStore", return_value=store), \
                patch.object(finish_install, "configure_rust", return_value=False), \
                patch("builtins.input", return_value="1"), patch("builtins.print"), \
                patch.object(finish_install.subprocess, "run", side_effect=OSError("fixture")), \
                patch.object(finish_install.subprocess, "Popen") as launch:
            self.assertEqual(finish_install.main(), 1)
        launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
