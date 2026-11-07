"""Credential, routing, role isolation and native stdio integration checks; no model calls."""
import asyncio
from contextlib import AsyncExitStack
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import uuid
from concurrent.futures import ThreadPoolExecutor
import threading

import codex_adapter
from codex_files import Files
from codex_mcp import check_arguments
import harness


class AdapterTests(unittest.TestCase):
    def test_jsonl_success_and_failure(self):
        lines = [{"type": "thread.started", "thread_id": "isolated"},
                 {"type": "item.completed", "item": {"type": "agent_message", "text": "Done"}},
                 {"type": "turn.completed", "usage": {"input_tokens": 42}}]
        result = codex_adapter.parse_output("chatter\n" + "\n".join(map(json.dumps, lines)))
        self.assertFalse(result["is_error"])
        self.assertEqual((result["session_id"], result["result"], result["usage"]["input_tokens"]), ("isolated", "Done", 42))
        lines.append({"type": "turn.failed", "error": {"message": "quota exceeded"}})
        self.assertTrue(codex_adapter.parse_output("\n".join(map(json.dumps, lines)))["is_error"])
        self.assertTrue(codex_adapter.parse_output("")["is_error"])

    def test_node_over_role_over_default(self):
        data = {"default": {"backend": "claude"}, "codex": {"model": "gpt-6-luna"},
                "nodes": {"review": {"backend": "codex"}, "review_final": {"backend": "claude"}}}
        self.assertEqual(harness.selection(data, "review", "review_draft")["model"], "gpt-6-luna")
        self.assertEqual(harness.selection(data, "review", "review_final")["backend"], "claude")
        data["nodes"]["review"]["model"] = "gpt-6-luna"
        self.assertNotIn("model", harness.selection(data, "review", "review_final"))

    def test_credentials_and_parent_identity_are_not_inherited(self):
        with patch.dict(os.environ, {"ANTHROPIC_AUTH_TOKEN": "qwen-secret", "OPENAI_API_KEY": "gpt-secret",
                                     "OTHER_SERVICE_TOKEN": "other-secret", "CODEX_THREAD_ID": "parent", "PATH": "runtime"}, clear=True):
            env = harness.process_env("codex", "private-home")
            self.assertEqual(env["OPENAI_API_KEY"], "gpt-secret")
            self.assertEqual(env["CODEX_HOME"], "private-home")
            self.assertFalse(any(k in env for k in ("ANTHROPIC_AUTH_TOKEN", "OTHER_SERVICE_TOKEN", "CODEX_THREAD_ID")))
            self.assertNotIn("OPENAI_API_KEY", harness.process_env("claude"))

    def test_files_enforce_roles_and_resolved_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = root / "cases" / "CASE-T"
            (case / "notes" / "analysis" / "round-1").mkdir(parents=True)
            (case / "rounds.json").write_text(json.dumps({"current": 1, "rounds": [{"round": 1}]}))
            p = case / "notes" / "analysis" / "round-1" / "law.md"
            p.write_text("Source checked.")
            analysis = Files("analysis", "CASE-T", root)
            self.assertIn("Source checked", analysis.read_file(str(p))["text"])
            for path in (".env", "key.md", "../outside", "cases/OTHER/intake/facts.json", "cases/CASE-T/../OTHER/secret.md"):
                with self.subTest(path=path), self.assertRaises((PermissionError, ValueError)):
                    analysis.path(path)
            with self.assertRaises(PermissionError):
                Files("review", "CASE-T", root).read_file(str(p))

    def test_argument_binding_and_optimizer_paths(self):
        for data in ({"case_id": "OTHER"}, {"filters": {"case_id": "OTHER"}},
                     {"id": "file:OTHER/notes.md"}, {"src_path": "key.md"},
                     {"products": "CASE-T/../OTHER/run"}, {"items": "OTHER/trace.json"}):
            with self.subTest(data=data), self.assertRaises(PermissionError):
                check_arguments(data, "CASE-T")
        check_arguments({"products": "CASE-T/intake/products/run", "path": "cn:company;hk:company"}, "CASE-T")

    def test_concurrent_claude_overrides_do_not_change_shared_models(self):
        import orchestrate_codex
        orch = orchestrate_codex.orch
        before = dict(orch.MODELS)
        barrier = threading.Barrier(2)

        def native_call(role, task, case_id, label):
            barrier.wait(timeout=10)
            return {"failure": None, "selected": orch.claude_env(role)["ANTHROPIC_MODEL"]}

        data = {"default": {"backend": "claude"}, "nodes": {"left": {"model": "qwen-left"}, "right": {"model": "qwen-right"}}}
        with tempfile.TemporaryDirectory() as tmp, patch.object(harness, "PROJECT", Path(tmp)), \
                patch.object(orch, "call_agent", native_call), \
                patch.object(orch, "claude_env", lambda role: {"ANTHROPIC_MODEL": "default"}), \
                patch.object(orch, "log_row", lambda *args, **kwargs: None):
            caller = orchestrate_codex.install(data)
            with ThreadPoolExecutor(max_workers=2) as pool:
                calls = [pool.submit(caller, "analysis", "check", "CASE-T", label) for label in ("left", "right")]
                self.assertEqual([job.result()["selected"] for job in calls], ["qwen-left", "qwen-right"])
        self.assertEqual(orch.MODELS, before)


class NativeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_role_write_and_read_denial(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        case_id = "CASE-CODEX-NATIVE-" + uuid.uuid4().hex[:10]
        self.case_id = case_id

        async with AsyncExitStack() as stack:
            async def connect(role, server):
                params = StdioServerParameters(command=sys.executable, args=[str(harness.PROJECT / "agent/tools/codex_mcp.py"),
                    "--role", role, "--case", case_id, "--server", server], env=harness.process_env("mcp"))
                read, write = await stack.enter_async_context(stdio_client(params))
                client = await stack.enter_async_context(ClientSession(read, write))
                await client.initialize()
                return client

            front = await connect("front", "tax-case-front")
            created = await front.call_tool("case_new", {"case_id": case_id})
            self.assertFalse(created.is_error)
            self.assertEqual(json.loads(created.content[0].text)["round"], 1)
            for role, required, forbidden in (("analysis", "write_report", "write_review"),
                                              ("review", "write_review", "write_report")):   # 2026-11-06: no polish role
                client = await connect(role, "tax-case-" + role)
                names = {t.name for t in (await client.list_tools()).tools}
                self.assertIn(required, names)
                self.assertNotIn(forbidden, names)
                bad = await client.call_tool("round_current", {"case_id": "OTHER"})
                self.assertTrue(bad.is_error)
                if role == "analysis":
                    written = await client.call_tool("notes_append", {"case_id": case_id, "book": "law", "text": "Native stdio check."})
                    self.assertNotIn("error", json.loads(written.content[0].text))
            reader = await connect("review", "tax-files")
            denied = await reader.call_tool("read_file", {"path": "cases/%s/notes/analysis/round-1/law.md" % case_id})
            self.assertTrue(denied.is_error)
            secret = await reader.call_tool("read_file", {"path": ".env.codex"})
            self.assertTrue(secret.is_error)
            own = await connect("analysis", "tax-files")
            read = await own.call_tool("read_file", {"path": "cases/%s/notes/analysis/round-1/law.md" % case_id})
            self.assertFalse(read.is_error)
            self.assertIn("Native stdio check", read.content[0].text)
            retrieval = await connect("analysis", "tax-read-analysis")
            fetched = await retrieval.call_tool("get", {"id": "file:%s/notes/analysis/round-1/law.md" % case_id})
            self.assertFalse(fetched.is_error)
            self.assertIn("Native stdio check", fetched.content[0].text)
            escaped = await retrieval.call_tool("get", {"id": "file:%s/../OTHER/intake/facts.json" % case_id})
            self.assertEqual(json.loads(escaped.content[0].text)["error"], "forbidden")
            for role, server, required in (("front", "tax-rule", "version"), ("front", "tax-opt-front", "run"),
                                            ("analysis", "tax-opt-calc", "evaluate")):
                client = await connect(role, server)
                names = {t.name for t in (await client.list_tools()).tools}
                self.assertIn(required, names)
                if server == "tax-opt-calc":
                    self.assertEqual(names, {"evaluate", "fx"})
            print("Native temporary case:", case_id)


if __name__ == "__main__":
    unittest.main()
