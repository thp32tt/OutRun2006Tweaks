"""VR headless launch contracts; no real browser, no network and no credentials."""
import ast
import asyncio
import io
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
ENTRY = (ROOT / "entrypoint.vr.sh").read_text()
COMPOSE = (ROOT / "docker-compose.portainer-vr.yml").read_text()
PART0 = (ROOT / "src-vr-v2/controller.py.part00").read_text()
PART3 = (ROOT / "src-vr-v2/controller.py.part03").read_text()


class HeadlessModeTests(unittest.TestCase):
    def test_launch_args_preserve_profile_and_local_cdp(self):
        start = ENTRY.index("build_chrome_args() {")
        end = ENTRY.index("\nstart_chrome() {", start)
        function = ENTRY[start:end]
        for mode in ("headless", "gui"):
            with self.subTest(mode=mode):
                script = (
                    "set -eu\nVR_BROWSER_MODE=" + mode +
                    "\nPROFILE_DIR=/data/browser-profile\n" + function +
                    "\nbuild_chrome_args\nprintf '%s\\n' \"${CHROME_ARGS[@]}\"\n"
                )
                args = subprocess.check_output(["bash", "-c", script], text=True).splitlines()
                self.assertEqual("--headless=new" in args, mode == "headless")
                self.assertIn("--user-data-dir=/data/browser-profile", args)
                self.assertIn("--remote-debugging-address=127.0.0.1", args)
                self.assertEqual(args[-1], "about:blank")
                self.assertFalse(any("chatgpt.com" in a for a in args))

    def test_headless_desktop_function_runs_no_processes(self):
        start = ENTRY.index("start_desktop() {")
        end = ENTRY.index("\nbuild_chrome_args() {", start)
        shell = (
            "set -eu\nVR_BROWSER_MODE=headless\n" +
            "mkdir(){ echo unexpected; exit 99; }\n" +
            "x11vnc(){ echo unexpected; exit 99; }\n" +
            "Xvfb(){ echo unexpected; exit 99; }\n" +
            "openbox(){ echo unexpected; exit 99; }\n" +
            "start_vnc(){ echo unexpected; exit 99; }\n" +
            "start_novnc(){ echo unexpected; exit 99; }\n" +
            ENTRY[start:end] + "\nstart_desktop\n"
        )
        self.assertEqual(subprocess.check_output(["bash", "-c", shell], text=True), "")

    def test_compose_preserves_login_and_queue_volumes_and_single_slot(self):
        self.assertIn('VR_BROWSER_MODE: "${VR_BROWSER_MODE:-headless}"', COMPOSE)
        self.assertIn('CHAT_SLOTS: "1"', COMPOSE)
        self.assertIn("outrun_chat_vr_data:/data", COMPOSE)
        self.assertIn("outrun_chat_vr_logs:/logs", COMPOSE)
        self.assertIn("/healthz", COMPOSE)
        self.assertIn('if VR_BROWSER_MODE == "gui" else ""', PART0)
        self.assertIn('if [[ "$VR_BROWSER_MODE" == "gui" ]]; then', ENTRY)
        self.assertIn("misses >= 3", ENTRY)
        self.assertIn("--max-time 4", ENTRY)

    def test_headless_rollover_closes_old_tab_before_navigation(self):
        source = "".join((ROOT / "src-vr-v2" / f"controller.py.part{i:02d}").read_text() for i in range(4))
        fn = next(n for n in ast.parse(source).body
                  if isinstance(n, ast.AsyncFunctionDef) and n.name == "hard_replace_slot_page")
        events = []
        class Page:
            def __init__(self, name, fail=False):
                self.name, self.fail, self.closed = name, fail, False
            def is_closed(self):
                return self.closed
            async def close(self, **kwargs):
                events.append("close:" + self.name)
                if self.fail:
                    raise TimeoutError("hung")
                self.closed = True
            async def goto(self, url, **kwargs):
                events.append("navigate:" + self.name)
            async def wait_for_timeout(self, ms):
                pass
        class Context:
            def __init__(self, old):
                self.pages = [old]
            async def new_page(self):
                events.append("new")
                p = Page("new")
                self.pages.append(p)
                return p
        env = {"BrowserContext": object, "Page": object, "Slot": object,
               "asyncio": asyncio, "VR_BROWSER_MODE": "headless", "CHAT_SLOTS": 1,
               "slot_project_home": lambda name: "https://chatgpt.com/project"}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "<rollover>", "exec"), env)
        old = Page("old")
        pages = {"A": old}
        slot = SimpleNamespace(name="A", url="old")
        result = asyncio.run(env["hard_replace_slot_page"](Context(old), pages, slot))
        self.assertIs(pages["A"], result)
        self.assertEqual(events, ["new", "close:old", "navigate:new"])
        events.clear()
        old = Page("hung", fail=True)
        with self.assertRaisesRegex(RuntimeError, "headless single-tab recycle required"):
            asyncio.run(env["hard_replace_slot_page"](Context(old), {"A": old}, slot))
        self.assertEqual(events, ["new", "close:hung"])

    def test_healthz_never_loads_queue_or_registry(self):
        from http.server import BaseHTTPRequestHandler
        cls = ast.parse(PART3).body[0]
        env = {"BaseHTTPRequestHandler": BaseHTTPRequestHandler}
        exec(compile(ast.Module(body=[cls], type_ignores=[]), "<status>", "exec"), env)
        handler = object.__new__(env["StatusHandler"])
        handler.path = "/healthz"
        handler.wfile = io.BytesIO()
        statuses = []
        handler.send_response = statuses.append
        handler.send_header = lambda *args: None
        handler.end_headers = lambda: None
        handler.do_GET()
        self.assertEqual(statuses, [200])
        self.assertEqual(handler.wfile.getvalue(), b"ok\n")


if __name__ == "__main__":
    unittest.main()
