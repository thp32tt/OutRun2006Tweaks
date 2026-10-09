import ast, asyncio, datetime, pathlib, os, time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCES = [
    ("vr", ROOT / "src-vr-v2"),
    ("localization", ROOT / "src"),
]
class FakePage:
    def __init__(self, fail_eval=False, closed=False):
        self.handlers = {}
        self.fail_eval = fail_eval
        self.closed = closed
        self.visited = None
        self.url = "about:blank"
    def on(self, event, callback): self.handlers[event] = callback
    def is_closed(self): return self.closed
    async def evaluate(self, expression):
        if self.fail_eval: raise RuntimeError("renderer hung")
        return 1
    async def screenshot(self, **kwargs): return b"fake screenshot"
    async def close(self, **kwargs): self.closed = True
    async def goto(self, url, **kwargs): self.url = self.visited = url
class FakeBrowser:
    def __init__(self): self.connected = True
    def is_connected(self): return self.connected
class FakeContext:
    def __init__(self): self.browser = FakeBrowser(); self.created=[]
    async def new_page(self):
        page = FakePage()
        self.created.append(page)
        return page
class Log:
    def __getattr__(self, name): return lambda *args, **kwargs: None

async def verify(name, directory):
    source = "".join((directory / f"controller.py.part0{i}").read_text(encoding="utf-8") for i in range(4))
    path = directory / "controller.py (assembled)"
    tree = ast.parse(source, filename=str(path))
    wanted = {"_watch_slot_page_health", "monitor_slot_tab_health"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in wanted or isinstance(node, ast.AsyncFunctionDef) and node.name in wanted or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id.startswith("TAB_HEALTH_") or isinstance(t, ast.Name) and t.id=="TAB_RECOVERY_COOLDOWN_SECONDS" for t in node.targets)]
    assert len(nodes)==6, (path, [(getattr(x,"name",None),type(x).__name__) for x in nodes])
    stats=[]
    reg=SimpleNamespace(slots=[SimpleNamespace(name="A",url="https://chatgpt.com/g/g-p-abc/c/persisted")])
    writes=[]
    globals_=dict(os=os,asyncio=asyncio,time=time,datetime=datetime.datetime,TZ=ZoneInfo("Asia/Seoul"),Path=pathlib.Path,Page=FakePage,BrowserContext=FakeContext,load_registry=lambda now:reg, is_project_scoped_chat_url=lambda url:"/c/" in url,BASE_URL="https://chatgpt.com/",log=Log(),runtime={},write_runtime=lambda **kw:(writes.append(kw),globals_["runtime"].update(kw)))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path), "exec"),globals_)
    monitor=globals_["monitor_slot_tab_health"]

    # A healthy tab remains untouched; a renderer crash replaces only that tab.
    context=FakeContext();old=FakePage();pages={"A":old};state={}
    await monitor(context,pages,state)
    assert pages["A"] is old and not context.created
    old.handlers["crash"](old)
    await monitor(context,pages,state)
    assert pages["A"] is not old and pages["A"].visited==reg.slots[0].url
    assert old.closed and len(context.created)==1
    assert globals_["runtime"]["tab_recovery_last_reason"]=="renderer_crash"
    stats.append("crash replaces one tab/preserves URL")

    # A closed tab also recovers; a slow-but-operating tab requires 3 failures.
    globals_["runtime"].clear();context=FakeContext();old=FakePage(closed=True);pages={"A":old};state={}
    await monitor(context,pages,state)
    assert pages["A"].visited==reg.slots[0].url and globals_["runtime"]["tab_recovery_last_reason"]=="closed"
    stats.append("closed tab recovery")

    globals_["runtime"].clear();context=FakeContext();old=FakePage(fail_eval=True);pages={"A":old};state={}
    await monitor(context,pages,state);await monitor(context,pages,state)
    assert pages["A"] is old and not context.created
    await monitor(context,pages,state)
    assert pages["A"].visited==reg.slots[0].url and globals_["runtime"]["tab_recovery_last_reason"]=="unresponsive"
    stats.append("three-failure debounce")

    globals_["runtime"].clear();context=FakeContext();context.browser.connected=False;pages={"A":FakePage()};state={}
    try: await monitor(context,pages,state)
    except RuntimeError as exc: assert "Docker restart" in str(exc)
    else: raise AssertionError("Disconnected browser must be fatal")
    assert not context.created
    stats.append("CDP disconnect fail-fast")

    # The health probe must not call the prompt sender or mutate durable TASK_ID.
    func=next(x for x in tree.body if isinstance(x,ast.AsyncFunctionDef) and x.name=="monitor_slot_tab_health")
    names=[x.func.id for x in ast.walk(func) if isinstance(x,ast.Call) and isinstance(x.func,ast.Name)]
    assert not {"send_message", "save_queue_state", "save_registry", "allocate_lane_production_id"} & set(names)
    stats.append("no prompt send/queue mutation")
    print(path.name, "COMPILE+MOCK PASS", ", ".join(stats))
for name, directory in SOURCES:
    asyncio.run(verify(name, directory))
print("TOTAL 2/2 combined controllers compiled; 10/10 behavior contracts passed")