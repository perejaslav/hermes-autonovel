import importlib
import os
import sys
import types
import unittest
from pathlib import Path


def install_adapter_stubs():
    httpx = types.ModuleType("httpx")
    httpx.post = lambda *args, **kwargs: None
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["httpx"] = httpx
    sys.modules["dotenv"] = dotenv


class ApiAdapterConfigTests(unittest.TestCase):
    def test_minimax_api_base_url_takes_precedence(self):
        os.environ["MINIMAX_API_KEY"] = "test-key"
        os.environ["MINIMAX_API_BASE_URL"] = "https://example.invalid/minimax"
        os.environ["AUTONOVEL_API_BASE_URL"] = "https://example.invalid/legacy"
        install_adapter_stubs()

        import _api_adapter

        importlib.reload(_api_adapter)

        self.assertEqual(_api_adapter.BASE_URL, "https://example.invalid/minimax")

    def test_auto_models_are_preserved_for_minimax(self):
        os.environ["MINIMAX_API_KEY"] = "test-key"
        os.environ.pop("AUTONOVEL_WRITER_MODEL", None)
        os.environ.pop("AUTONOVEL_JUDGE_MODEL", None)
        os.environ.pop("AUTONOVEL_REVIEW_MODEL", None)
        install_adapter_stubs()

        import _api_adapter

        importlib.reload(_api_adapter)

        self.assertEqual(_api_adapter.resolve_model("auto", "writer"), "auto")
        self.assertEqual(_api_adapter.resolve_model("auto", "judge"), "auto")
        self.assertEqual(_api_adapter.resolve_model("auto", "review"), "auto")


class UtilityTests(unittest.TestCase):
    def test_discover_chapters_sorts_existing_chapter_files(self):
        from autonovel_utils import discover_chapters

        class FakeRoot:
            def __truediv__(self, name):
                return self

            def glob(self, pattern):
                return [
                    Path("/project/chapters/ch_10.md"),
                    Path("/project/chapters/ch_02.md"),
                    Path("/project/chapters/notes.md"),
                ]

        root = FakeRoot()
        found = discover_chapters(root)

        self.assertEqual([num for num, _ in found], [2, 10])

    def test_parse_json_response_extracts_fenced_object(self):
        from autonovel_utils import parse_json_response

        parsed = parse_json_response('```json\n{"title": "A", "items": [1, 2]}\n```\nextra')

        self.assertEqual(parsed["title"], "A")
        self.assertEqual(parsed["items"], [1, 2])

    def test_read_required_file_raises_clear_error_for_missing_input(self):
        from autonovel_utils import MissingInputError, read_required_file

        missing = Path(__file__).resolve().parents[1] / "__missing_seed_for_test__.txt"
        with self.assertRaisesRegex(MissingInputError, "Required input missing"):
            read_required_file(missing, "seed concept")


if __name__ == "__main__":
    unittest.main()
