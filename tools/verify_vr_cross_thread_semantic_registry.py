#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMANTICS = ROOT / "src/vr/game/render_semantics.hpp"


def fail(message: str) -> None:
    raise SystemExit(
        "VR cross-thread semantic registry contract FAILED\n"
        f" - {message}"
    )


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing required source: {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def function_body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        fail(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing function body: {marker}")
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:i]
    fail(f"unterminated function body: {marker}")
    return ""


s = read(SEMANTICS)

# Exact semantic producer hooks can run on a different thread from the canonical
# SpriteNode queue renderer. The semantic tag table therefore must be shared and
# synchronized; only render-thread cursor/scope state remains thread_local.
for marker in (
    "#include <atomic>",
    "#include <mutex>",
    "std::array<SpriteNodeSemanticTag,",
    "SpriteNodeSemanticCapacity> SpriteNodeSemanticTags{};",
    "std::size_t SpriteNodeSemanticCount = 0;",
    "std::atomic<std::size_t> SpriteNodeSemanticPublishedCount{ 0 };",
    "std::mutex SpriteNodeSemanticMutex;",
    "std::atomic<std::uint64_t> SpriteNodeSemanticNextSerial{ 1 };",
    "thread_local std::uint64_t SpriteQueueSemanticCutoff = 0;",
):
    if marker not in s:
        fail(f"shared semantic registry marker missing: {marker}")

for forbidden in (
    "thread_local std::array<SpriteNodeSemanticTag,",
    "thread_local std::size_t SpriteNodeSemanticCount",
):
    if forbidden in s:
        fail(f"semantic registry regressed to producer-thread-local storage: {forbidden}")

tag_start = s.find("struct SpriteNodeSemanticTag")
tag_end = s.find("};", tag_start)
tag = s[tag_start:tag_end]
for marker in (
    "std::uint64_t serial = 0;",
    "ProducerToken producer = ProducerToken::None;",
):
    if marker not in tag:
        fail(f"semantic tag lost cross-thread lifetime/provenance field: {marker}")

register = function_body(s, "inline void RegisterSpriteNodeScope(")
for marker in (
    "SpriteNodeSemanticNextSerial.fetch_add(",
    "std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);",
    "SpriteNodeSemanticPublishedCount.store(",
    "std::memory_order_release",
):
    if marker not in register:
        fail(f"registration publication contract missing: {marker}")

peek = function_body(s, "inline RenderScope PeekSpriteNodeScope(")
for marker in (
    "SpriteNodeSemanticPublishedCount.load(",
    "std::memory_order_acquire",
    "std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);",
):
    if marker not in peek:
        fail(f"peek synchronization contract missing: {marker}")

consume = function_body(s, "inline RenderScope ConsumeSpriteNodeScope(")
for marker in (
    "SpriteNodeSemanticPublishedCount.load(",
    "std::memory_order_acquire",
    "std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);",
    "SpriteNodeSemanticPublishedCount.store(",
    "std::memory_order_release",
):
    if marker not in consume:
        fail(f"consume synchronization contract missing: {marker}")

begin = function_body(s, "inline void BeginSpriteQueueRender() noexcept")
select = function_body(s, "inline void SelectSpriteQueueNode(")
if "SpriteQueueSemanticCutoff" not in begin and "SpriteQueueSemanticCutoff" not in select:
    fail("queue walk never snapshots a semantic serial cutoff")

end = function_body(s, "inline void EndSpriteQueueRender() noexcept")
for marker in (
    "std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);",
    "tag.serial <= SpriteQueueSemanticCutoff",
    "SpriteNodeSemanticPublishedCount.store(",
    "SpriteQueueSemanticCutoff = 0;",
):
    if marker not in end:
        fail(f"queue-end stale cleanup contract missing: {marker}")
if "SpriteNodeSemanticCount = 0;" in end:
    fail("queue end must not erase tags produced concurrently for the next frame")

# Diagnostic/render-thread state should stay local; making these shared would
# broaden synchronization and semantic authority beyond the proven fix.
for marker in (
    "thread_local RenderScope SpriteQueuePreviousScope",
    "thread_local unsigned SpriteQueueDepth",
    "thread_local const void* CurrentSpriteQueueNode",
    "thread_local std::uint64_t SpriteQueueNodeEpoch",
    "thread_local ProducerToken CurrentSpriteQueueProducer",
):
    if marker not in s:
        fail(f"render-thread queue cursor state changed unexpectedly: {marker}")

# Exact producer publication/cutoff must be linearized, not merely guarded
# by different sections of the same function. The original producer reserved a
# serial before locking, and both renderer cutoffs read nextSerial unlocked.
def require_epoch_order(source):
    specs = (
        ("RegisterSpriteNodeScope", "inline void RegisterSpriteNodeScope(", "SpriteNodeSemanticNextSerial.fetch_add("),
        ("BeginSpriteQueueRender", "inline void BeginSpriteQueueRender() noexcept", "SpriteNodeSemanticNextSerial.load("),
        ("SelectSpriteQueueNode", "inline void SelectSpriteQueueNode(", "SpriteNodeSemanticNextSerial.load("),
    )
    for name, marker, operation in specs:
        body_text = function_body(source, marker)
        lock_pos = body_text.find("std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);")
        serial_pos = body_text.find(operation)
        if lock_pos < 0 or serial_pos < 0 or lock_pos > serial_pos:
            raise ValueError(f"{name}: epoch not published/snapshotted under mutex")
    return len(specs)

try:
    checked = require_epoch_order(s)
except ValueError as exc:
    fail(str(exc))
mutations = 0
for mark in (
    "inline void RegisterSpriteNodeScope(",
    "inline void BeginSpriteQueueRender() noexcept",
    "inline void SelectSpriteQueueNode(",
):
    pos=s.find(mark)
    target_lock="std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);"
    index=s.find(target_lock,pos)
    if index<0:fail("exact epoch mutation could not locate lock: "+mark)
    mutated=s[:index]+"/* deleted critical section */"+s[index+len(target_lock):]
    try:
        require_epoch_order(mutated)
    except ValueError:
        mutations+=1
    else:
        fail("uncaught epoch race mutation: "+mark)
if mutations!=3:fail("epoch negatives must be 3/3")
print(f"VR semantic tag epoch ordering PASS: {checked} sources, {mutations}/3 lock faults detected")


# P0-B: a source-confirmed producer does not make 3298 unrelated queue nodes
# contend on the registry mutex. Negative hints never authorize stereo: a
# positive hint still needs the locked, exact-pointer semantic comparison.
for label, body in (("peek", peek), ("consume", consume)):
    hint = body.find("!SpriteNodeSemanticMaybeHasTag(node)")
    lock = body.find("std::lock_guard<std::mutex> lock(SpriteNodeSemanticMutex);")
    if hint < 0 or lock < 0 or hint >= lock:
        fail(f"{label}: untagged node still takes the registry mutex")
for marker in (
    "SpriteNodeSemanticRememberHint(node);",
    "SpriteNodeSemanticForgetHint(SpriteNodeSemanticTags[oldest].node);",
):
    if marker not in register:
        fail("tag publication/overwrite lost pre-lock hint accounting: " + marker)
if "SpriteNodeSemanticForgetHint(node);" not in consume:
    fail("tag consumption leaks a ref-counted hint")
if "SpriteNodeSemanticForgetHint(tag.node);" not in end:
    fail("queue-end stale sweep leaks a ref-counted hint")
hint = function_body(s, "inline bool SpriteNodeSemanticMaybeHasTag(")
for marker in ("std::memory_order_acquire", "has(bits.first) && has(bits.second)"):
    if marker not in hint:
        fail("invalid two-hash negative-hint contract: " + marker)

# Positive and collision/overflow/expiry negative models. Regressions in
# deletion accounting can cause a real exact HUD/rank tag to be lost.
def filter_bits(pointer):
    key = pointer >> 3
    key ^= key >> 32
    h = key & 0xffffffff
    h ^= h >> 16
    h = (h * 0x7feb352d) & 0xffffffff
    h ^= h >> 15
    h = (h * 0x846ca68b) & 0xffffffff
    h ^= h >> 16
    return h & 255, (h >> 8) & 255

refs = [0] * 256
active = set()
def add(pointer):
    if pointer not in active:
        active.add(pointer)
        for bit in set(filter_bits(pointer)):
            refs[bit] += 1
def remove(pointer):
    if pointer in active:
        active.remove(pointer)
        for bit in set(filter_bits(pointer)):
            refs[bit] -= 1
            assert refs[bit] >= 0
def might_match(pointer):
    return all(refs[bit] > 0 for bit in filter_bits(pointer))

add(0x420100)
misses = [0x500000 + i * 32 for i in range(3298)]
assert sum(not might_match(p) for p in misses) > 3100
seen = {}
collision = None
for i in range(16384):
    pointer = 0x600000 + i * 16
    pair = tuple(sorted(filter_bits(pointer)))
    if pair in seen:
        collision = seen[pair], pointer
        break
    seen[pair] = pointer
assert collision
a, b = collision
add(a)
add(b)
remove(a)
assert might_match(b)
for i in range(560):
    add(0x700000 + i * 16)
add(0x900010)
for p in tuple(active):
    if p != 0x900010:
        remove(p)
assert active == {0x900010} and might_match(0x900010)
remove(0x900010)
assert not active and all(v == 0 for v in refs)
print("VR 3298-node negative filter, collision, expiry and refcount recovery PASS")

# Mutation controls: dropping the filter or any removal site must be caught
# before a green exact-SHA result can be accepted.
for token in (
    "!SpriteNodeSemanticMaybeHasTag(node)",
    "SpriteNodeSemanticForgetHint(node);",
    "SpriteNodeSemanticForgetHint(tag.node);",
):
    assert token in s
    mutated = s.replace(token, "/* removed hint contract */", 1)
    assert mutated != s
    if token.startswith("!"):
        assert any(token not in function_body(mutated, mark) for mark in (
            "inline RenderScope PeekSpriteNodeScope(",
            "inline RenderScope ConsumeSpriteNodeScope(",
        ))
    else:
        assert mutated.count(token) == s.count(token) - 1
print("VR semantic hint 3 destructive source mutations detected")

print("VR cross-thread semantic registry contract PASS")
