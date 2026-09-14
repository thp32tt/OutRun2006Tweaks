from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    text = read(path)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, found {count}: {old[:180]!r}")
    write(path, text.replace(old, new, 1))


# IDirect3DDevice9::Clear(count=0) clears the current viewport, not necessarily
# the complete render target. A newly-created right depth surface is therefore
# synchronized only after the game successfully duplicates a Z clear while the
# viewport covers the entire stereo backbuffer.
replace_once(
    "src/vr_stereo.cpp",
    '''\t\tbool FormatHasStencil(D3DFORMAT format)
\t\t{
\t\t\tswitch (format)
\t\t\t{
\t\t\tcase D3DFMT_D15S1:
\t\t\tcase D3DFMT_D24S8:
\t\t\tcase D3DFMT_D24X4S4:
\t\t\tcase D3DFMT_D24FS8:
\t\t\t\treturn true;
\t\t\tdefault:
\t\t\t\treturn false;
\t\t\t}
\t\t}
''',
    '''\t\tbool FormatHasStencil(D3DFORMAT format)
\t\t{
\t\t\tswitch (format)
\t\t\t{
\t\t\tcase D3DFMT_D15S1:
\t\t\tcase D3DFMT_D24S8:
\t\t\tcase D3DFMT_D24X4S4:
\t\t\tcase D3DFMT_D24FS8:
\t\t\t\treturn true;
\t\t\tdefault:
\t\t\t\treturn false;
\t\t\t}
\t\t}

\t\tbool ViewportCoversStereoBackbuffer(IDirect3DDevice9* device)
\t\t{
\t\t\tif (!device || !BackBufferDesc.Width || !BackBufferDesc.Height)
\t\t\t\treturn false;
\t\t\tD3DVIEWPORT9 viewport{};
\t\t\tif (FAILED(device->GetViewport(&viewport)))
\t\t\t\treturn false;
\t\t\treturn viewport.X == 0 && viewport.Y == 0 &&
\t\t\t\tviewport.Width == BackBufferDesc.Width &&
\t\t\t\tviewport.Height == BackBufferDesc.Height;
\t\t}
''',
)
replace_once(
    "src/vr_stereo.cpp",
    '''else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0) RightDepthSynchronized = true;''',
    '''else if ((flags & D3DCLEAR_ZBUFFER) != 0 && count == 0 &&
\t\t\t\tViewportCoversStereoBackbuffer(device)) RightDepthSynchronized = true;''',
)

stereo = read("src/vr_stereo.cpp")
for marker in (
    "ViewportCoversStereoBackbuffer",
    "viewport.Width == BackBufferDesc.Width",
    "viewport.Height == BackBufferDesc.Height",
    "ViewportCoversStereoBackbuffer(device)) RightDepthSynchronized = true",
):
    if marker not in stereo:
        raise RuntimeError(f"depth synchronization invariant missing: {marker}")

print("stereo depth synchronization now requires a full-backbuffer viewport clear")
