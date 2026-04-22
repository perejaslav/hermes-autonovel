import importlib
import json
import os
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


def install_adapter_stubs():
    httpx = types.ModuleType("httpx")
    httpx.post = lambda *args, **kwargs: None
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: None
    sys.modules["httpx"] = httpx
    sys.modules["dotenv"] = dotenv


class ApiAdapterConfigTests(unittest.TestCase):
    def tearDown(self):
        for key in [
            "AUTONOVEL_PROVIDER",
            "AUTONOVEL_AGENT_REQUEST_DIR",
            "AUTONOVEL_AGENT_RESPONSE_FILE",
            "MODEL_API_KEY",
            "MODEL_API_BASE_URL",
            "MODEL_API_HEADERS",
            "AUTONOVEL_WRITER_MODEL",
            "AUTONOVEL_JUDGE_MODEL",
            "AUTONOVEL_REVIEW_MODEL",
        ]:
            os.environ.pop(key, None)

    def test_auto_models_are_preserved_for_default_provider(self):
        os.environ.pop("AUTONOVEL_WRITER_MODEL", None)
        os.environ.pop("AUTONOVEL_JUDGE_MODEL", None)
        os.environ.pop("AUTONOVEL_REVIEW_MODEL", None)
        install_adapter_stubs()

        import _api_adapter

        importlib.reload(_api_adapter)

        self.assertEqual(_api_adapter.resolve_model("auto", "writer"), "auto")
        self.assertEqual(_api_adapter.resolve_model("auto", "judge"), "auto")
        self.assertEqual(_api_adapter.resolve_model("auto", "review"), "auto")

    def test_agent_provider_writes_request_and_requires_response(self):
        os.environ["AUTONOVEL_PROVIDER"] = "agent"
        install_adapter_stubs()

        import _api_adapter

        importlib.reload(_api_adapter)

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AUTONOVEL_AGENT_REQUEST_DIR"] = tmp
            importlib.reload(_api_adapter)

            with self.assertRaisesRegex(RuntimeError, "Hermes Agent response required"):
                _api_adapter.call_model(
                    "Draft a scene.",
                    system="You are a novelist.",
                    role="writer",
                    max_tokens=123,
                    temperature=0.4,
                )

            requests = list(Path(tmp).glob("*.json"))
            self.assertEqual(len(requests), 1)
            payload = json.loads(requests[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["role"], "writer")
            self.assertEqual(payload["prompt"], "Draft a scene.")
            self.assertEqual(payload["system"], "You are a novelist.")
            self.assertEqual(payload["max_tokens"], 123)
            self.assertEqual(payload["temperature"], 0.4)
            self.assertTrue(payload["response_path"].endswith(".response.json"))

    def test_agent_provider_reads_response_file(self):
        os.environ["AUTONOVEL_PROVIDER"] = "agent"
        install_adapter_stubs()

        import _api_adapter

        with tempfile.TemporaryDirectory() as tmp:
            response = Path(tmp) / "response.json"
            response.write_text(json.dumps({"content": "Ответ модели"}), encoding="utf-8")
            os.environ["AUTONOVEL_AGENT_RESPONSE_FILE"] = str(response)

            importlib.reload(_api_adapter)

            self.assertEqual(_api_adapter.call_writer("Напиши сцену"), "Ответ модели")

    def test_openai_compatible_provider_reads_chat_completion_content(self):
        os.environ["AUTONOVEL_PROVIDER"] = "openai_compatible"
        os.environ["MODEL_API_KEY"] = "test-key"
        os.environ["MODEL_API_BASE_URL"] = "https://example.invalid/v1"

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "OpenAI-style response"}}]}

        httpx = types.ModuleType("httpx")
        httpx.post = lambda *args, **kwargs: FakeResponse()
        dotenv = types.ModuleType("dotenv")
        dotenv.load_dotenv = lambda *args, **kwargs: None
        sys.modules["httpx"] = httpx
        sys.modules["dotenv"] = dotenv

        import _api_adapter

        importlib.reload(_api_adapter)

        self.assertEqual(_api_adapter.call_writer("Prompt"), "OpenAI-style response")


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

    def test_language_instruction_defaults_to_russian_for_story_outputs(self):
        from autonovel_utils import language_instruction

        instruction = language_instruction()

        self.assertIn("Russian", instruction)
        self.assertIn("JSON keys", instruction)
        self.assertIn("technical identifiers", instruction)

    def test_foundation_prompt_includes_language_contract(self):
        install_adapter_stubs()

        import gen_world

        prompt = gen_world.build_prompt("seed", "voice", "craft")

        self.assertIn("Write all book-facing content in Russian", prompt)
        self.assertIn("technical identifiers", prompt)

    def test_foundation_wizard_default_config_is_russian_and_interactive(self):
        from foundation_wizard import build_seed_options_prompt, default_config, save_config, load_config

        config = default_config()
        self.assertEqual(config["language"], "ru")
        self.assertTrue(config["interactive_foundation"])

        prompt = build_seed_options_prompt(config, "морской миф")
        self.assertIn("Write all book-facing content in Russian", prompt)
        self.assertIn("морской миф", prompt)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book_config.json"
            save_config(config, path)
            loaded = load_config(path)

        self.assertEqual(loaded["language"], "ru")
        self.assertEqual(loaded["foundation"]["premise_hint"], "")

    def test_foundation_wizard_can_save_chat_led_answers(self):
        install_adapter_stubs()

        from foundation_wizard import apply_foundation_answers, default_config, load_config

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "book_config.json"
            config = apply_foundation_answers(
                {
                    "premise_hint": "роман о забытом городе",
                    "genre": "мистический роман",
                    "tone": "тихий, тревожный",
                    "selected_seed": "архивариус ищет пропавшую площадь",
                    "world_direction": "современный город с невозможной географией",
                    "character_direction": "герой сомневается в собственной памяти",
                    "outline_direction": "от личной тайны к выбору судьбы города",
                },
                base_config=default_config(),
                path=path,
            )
            loaded = load_config(path)

        self.assertFalse(config["interactive_foundation"])
        self.assertEqual(loaded["language"], "ru")
        self.assertFalse(loaded["interactive_foundation"])
        self.assertEqual(loaded["foundation"]["premise_hint"], "роман о забытом городе")
        self.assertEqual(loaded["foundation"]["genre"], "мистический роман")
        self.assertEqual(loaded["foundation"]["selected_seed"], "архивариус ищет пропавшую площадь")

    def test_chat_led_book_start_skill_describes_intent_workflow(self):
        root = Path(__file__).resolve().parents[1]
        skill = root / "hermes-agent" / "skills" / "autonovel-book-start" / "SKILL.md"

        text = skill.read_text(encoding="utf-8")

        self.assertIn("name: autonovel-book-start", text)
        self.assertIn("хочу написать книгу", text)
        self.assertIn("start_book.py", text)
        self.assertIn("--archive-existing", text)
        self.assertIn("book_config.json", text)
        self.assertIn("seed.txt", text)
        self.assertIn("wait for explicit approval", text)
        self.assertNotIn("PowerShell", text)

    def test_start_book_archives_existing_artifacts_and_writes_new_book_state(self):
        install_adapter_stubs()

        from start_book import start_new_book

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "seed.txt").write_text("старый seed", encoding="utf-8")
            (root / "world.md").write_text("старый world", encoding="utf-8")
            (root / "book_config.json").write_text(json.dumps({"language": "en"}), encoding="utf-8")
            (root / "state.json").write_text(json.dumps({"phase": "drafting", "chapters_total": 12}), encoding="utf-8")
            (root / "results.tsv").write_text("old results", encoding="utf-8")
            (root / "manuscript.md").write_text("old manuscript", encoding="utf-8")
            (root / "chapters").mkdir()
            (root / "chapters" / "ch_01.md").write_text("old chapter", encoding="utf-8")
            (root / "edit_logs").mkdir()
            (root / "edit_logs" / "log.json").write_text("{}", encoding="utf-8")
            (root / "briefs").mkdir()
            (root / "briefs" / "brief.md").write_text("brief", encoding="utf-8")
            (root / "typeset").mkdir()
            (root / "typeset" / "build_tex.py").write_text("print('build')", encoding="utf-8")
            (root / "typeset" / "build_epub.py").write_text("print('build')", encoding="utf-8")
            (root / ".env").write_text("KEEP=1", encoding="utf-8")

            result = start_new_book(
                {
                    "premise_hint": "островная маячная история",
                    "genre": "literary mystery",
                    "audience": "adult readers",
                    "tone": "quiet and exact",
                    "selected_seed": "Смотрительница маяка на шотландском острове скрывает чужую смерть.",
                    "world_direction": "остров живет по собственным приливам и слухам",
                    "character_direction": "героиня стареет, но не отступает от долга",
                    "outline_direction": "от бытового распорядка к раскрытию тайны острова",
                },
                project_root=root,
                archive_existing=True,
                run_foundation=False,
            )

            archive_root = root / "archive"
            archives = list(archive_root.iterdir())
            self.assertEqual(len(archives), 1)
            archived = archives[0]
            self.assertTrue((archived / "seed.txt").exists())
            self.assertTrue((archived / "world.md").exists())
            self.assertTrue((archived / "chapters" / "ch_01.md").exists())
            self.assertTrue((archived / "edit_logs" / "log.json").exists())
            self.assertTrue((archived / "briefs" / "brief.md").exists())
            self.assertTrue((archived / "archive_manifest.json").exists())
            self.assertTrue((root / ".env").exists())
            self.assertTrue((root / "typeset" / "build_tex.py").exists())
            self.assertTrue((root / "typeset" / "build_epub.py").exists())
            self.assertTrue((root / "seed.txt").exists())
            self.assertTrue((root / "book_config.json").exists())
            self.assertTrue((root / "state.json").exists())

            config = json.loads((root / "book_config.json").read_text(encoding="utf-8"))
            state = json.loads((root / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(config["language"], "ru")
            self.assertFalse(config["interactive_foundation"])
            self.assertEqual(state["phase"], "foundation")
            self.assertEqual(state["current_focus"], "planning")
            self.assertEqual(state["chapters_total"], 0)
            self.assertIn("Смотрительница маяка", (root / "seed.txt").read_text(encoding="utf-8"))
            self.assertIn("archive", result["archive_dir"].as_posix())

    def test_start_book_rejects_incomplete_intake_without_writing_partial_files(self):
        install_adapter_stubs()

        from start_book import start_new_book

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "missing required intake fields"):
                start_new_book(
                    {
                        "premise_hint": "only one field",
                    },
                    project_root=root,
                    archive_existing=True,
                    run_foundation=False,
                )

            self.assertFalse((root / "seed.txt").exists())
            self.assertFalse((root / "book_config.json").exists())
            self.assertFalse((root / "state.json").exists())
            self.assertFalse((root / "archive").exists())

    def test_start_book_can_read_intake_from_stdin(self):
        install_adapter_stubs()

        from start_book import read_intake

        previous_stdin = sys.stdin
        try:
            sys.stdin = StringIO(json.dumps({"premise_hint": "stdin premise"}))
            intake = read_intake("-")
        finally:
            sys.stdin = previous_stdin

        self.assertEqual(intake["premise_hint"], "stdin premise")

    def test_audit_project_reports_state_unicode_and_heading_issues(self):
        from audit_project import collect_audit, format_audit

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            chapters = root / "chapters"
            chapters.mkdir()
            (root / "state.json").write_text(
                json.dumps({"chapters_drafted": 2, "chapters_total": 0}),
                encoding="utf-8",
            )
            (chapters / "ch_01.md").write_text("# Chapter 1\nText", encoding="utf-8")
            (chapters / "ch_02.md").write_text("Aul迆 harbor text", encoding="utf-8")

            report = collect_audit(root)

        self.assertIn("state_chapter_total_mismatch", report["issues"])
        self.assertIn("suspicious_unicode", report["issues"])
        self.assertIn("inconsistent_chapter_headings", report["issues"])
        format_audit(report).encode("cp1251")


class AgentModeCliTests(unittest.TestCase):
    def tearDown(self):
        for key in [
            "AUTONOVEL_PROVIDER",
            "AUTONOVEL_AGENT_REQUEST_DIR",
            "AUTONOVEL_AGENT_RESPONSE_FILE",
            "MODEL_API_KEY",
        ]:
            os.environ.pop(key, None)

    def test_seed_uses_agent_provider_without_api_key(self):
        os.environ["AUTONOVEL_PROVIDER"] = "agent"
        os.environ.pop("MODEL_API_KEY", None)
        install_adapter_stubs()

        import seed

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["AUTONOVEL_AGENT_REQUEST_DIR"] = tmp
            previous_argv = sys.argv
            sys.argv = ["seed.py", "--count", "1"]
            try:
                with self.assertRaisesRegex(RuntimeError, "Hermes Agent response required"):
                    with redirect_stdout(StringIO()):
                        seed.main()
            finally:
                sys.argv = previous_argv

    def test_reader_panel_uses_shared_adapter_call_model(self):
        install_adapter_stubs()
        fake_adapter = types.ModuleType("_api_adapter")

        def fake_call_model(prompt, system="", model="auto", max_tokens=0, temperature=0.0, role="writer"):
            self.assertEqual(role, "judge")
            self.assertIn("complete fantasy novel", prompt)
            self.assertIn("senior fiction editor", system)
            return json.dumps({
                "momentum_loss": "None",
                "earned_ending": "Yes",
                "cut_candidate": "None",
                "missing_scene": "None",
                "thinnest_character": "None",
                "best_scene": "Ch 1",
                "worst_scene": "None",
                "would_recommend": "Yes",
                "haunts_you": "A line",
                "next_book": "Yes",
            })

        fake_adapter.call_model = fake_call_model
        original_adapter = sys.modules.get("_api_adapter")
        sys.modules["_api_adapter"] = fake_adapter
        try:
            import reader_panel

            result = reader_panel.call_reader("editor", "Arc summary")
        finally:
            if original_adapter is not None:
                sys.modules["_api_adapter"] = original_adapter
            else:
                sys.modules.pop("_api_adapter", None)

        self.assertEqual(result["would_recommend"], "Yes")


if __name__ == "__main__":
    unittest.main()
