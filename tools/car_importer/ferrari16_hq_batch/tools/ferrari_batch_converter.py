#!/usr/bin/env python3
"""Fail-closed, no-LOD glTF/GLB -> OutRun experimental OVRCABH4 sidecars with optional live dashboard bindings.

This is an OFFLINE conversion tool, not a game-ready installer. Only explicitly
provided GLBs with attested car_id/source SHA and verified game coordinate
transforms are converted. No source assets or rights are inferred from names.
"""
from __future__ import annotations

import argparse
import base64
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import zlib

import numpy as np
from PIL import Image

MAX_GLB_BYTES = 512 * 1024 * 1024
MAX_SIDECAR_BYTES = 128 * 1024 * 1024
MAX_GPU_BYTES = 112 * 1024 * 1024
MAX_VERTEX = 1_000_000
MAX_TRIANGLES = 2_000_000
MAX_MATERIALS = 64
MAX_GROUPS = 512
MAX_TEXTURE_DIM = 2048


class ConversionError(ValueError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def ensure(condition, message):
    if not condition:
        raise ConversionError(message)


def read_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def load_glb(path: Path):
    size = path.stat().st_size
    ensure(32 <= size <= MAX_GLB_BYTES, 'GLB file size exceeds bounded loader')
    contents = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', contents, 0)
    ensure((magic, version, length) == (b'glTF', 2, size), 'invalid GLB header')
    offsets = []
    p = 12
    while p < size:
        ensure(p + 8 <= size, 'truncated GLB chunk header')
        length, typ = struct.unpack_from('<II', contents, p)
        p += 8
        ensure(length % 4 == 0 and length <= size-p, 'GLB chunk bounds')
        offsets.append((typ, p, length))
        p += length
    ensure(len(offsets) == 2 and offsets[0][0] == 0x4e4f534a and offsets[1][0] == 0x004e4942,
           'only fully embedded GLB JSON + BIN supported (no external assets)')
    ensure(offsets[0][2] <= 32 * 1024 * 1024, 'GLB metadata unbounded')
    x = offsets[0]
    g = json.loads(contents[x[1]:x[1]+x[2]].decode('utf-8').rstrip(' \0\t\r\n'))
    ensure(g.get('asset', {}).get('version') == '2.0', 'not glTF 2.0')
    x = offsets[1]
    binary = memoryview(contents)[x[1]:x[1]+x[2]]
    ensure(len(g.get('buffers', [])) == 1 and 'uri' not in g['buffers'][0], 'external GLB buffers unsupported')
    ensure(0 <= len(binary)-g['buffers'][0]['byteLength'] <= 3, 'GLB buffer length mismatch')
    ensure(not g.get('extensionsRequired'), 'GLB requires unsupported extensions: '+str(g.get('extensionsRequired',[])))
    return g, binary


DTYPES = {5120: np.int8, 5121: np.uint8, 5122: np.int16,
          5123: np.uint16, 5125: np.uint32, 5126: np.float32}
COMPONENTS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4,
              'MAT2': 4, 'MAT3': 9, 'MAT4': 16}


def accessor(g, binary, which, components=None):
    accessors = g.get('accessors', [])
    ensure(isinstance(which, int) and 0 <= which < len(accessors), 'invalid accessor ID')
    acc = accessors[which]
    ensure('sparse' not in acc, 'sparse accessors must be flattened before conversion')
    view_id = acc.get('bufferView')
    views = g.get('bufferViews', [])
    ensure(isinstance(view_id, int) and 0 <= view_id < len(views), 'accessor bufferView missing')
    view = views[view_id]
    ensure(view.get('buffer', 0) == 0, 'external binary view unsupported')
    dtype = DTYPES.get(acc.get('componentType'))
    ncomp = COMPONENTS.get(acc.get('type'))
    ensure(dtype is not None and ncomp is not None, 'accessor type unsupported')
    ensure(components is None or ncomp == components, 'accessor dimensionality mismatch')
    count = acc.get('count')
    ensure(isinstance(count, int) and 0 < count <= 4_000_000, 'accessor count invalid')
    item = ncomp * np.dtype(dtype).itemsize
    stride = view.get('byteStride', item)
    ensure(isinstance(stride, int) and item <= stride <= 252 and stride % np.dtype(dtype).itemsize == 0,
           'accessor stride invalid')
    start = view.get('byteOffset', 0)+acc.get('byteOffset', 0)
    end = start+(count-1)*stride+item
    ensure(0 <= start and end <= view.get('byteOffset', 0)+view.get('byteLength', -1) and end <= len(binary),
           'accessor exceeds BIN view')
    arr = np.ndarray((count, ncomp), dtype=np.dtype(dtype).newbyteorder('<'),
                     buffer=binary, offset=start, strides=(stride, np.dtype(dtype).itemsize)).copy()
    if acc.get('normalized'):
        ensure(dtype != np.float32, 'normalized float accessor invalid')
        maxval = float(np.iinfo(dtype).max)
        arr = np.maximum(-1., arr.astype(np.float32)/maxval) if np.issubdtype(dtype, np.signedinteger) else arr.astype(np.float32)/maxval
    return arr


def trs_matrix(node):
    if 'matrix' in node:
        ensure(len(node['matrix']) == 16, 'invalid node matrix')
        a = np.asarray(node['matrix'], dtype=np.float64).reshape((4, 4), order='F')
    else:
        a = np.eye(4)
        v = node.get('translation', [0, 0, 0])
        sc = node.get('scale', [1, 1, 1])
        q = node.get('rotation', [0, 0, 0, 1])
        ensure(len(v) == 3 and len(sc) == 3 and len(q) == 4, 'invalid TRS')
        q = np.asarray(q, dtype=np.float64)
        ensure(0.9 < np.linalg.norm(q) < 1.1, 'non-unit node rotation quaternion')
        x, y, z, w = q / np.linalg.norm(q)
        a[:3, :3] = np.array([
            [1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
            [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
            [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]
        ]) @ np.diag(sc)
        a[:3, 3] = v
    ensure(np.all(np.isfinite(a)) and 1e-12 < abs(np.linalg.det(a[:3, :3])) < 1e12,
           'invalid node transform')
    return a


def ordered_mesh_nodes(g, placement):
    scene = g.get('scene', 0)
    scenes = g.get('scenes', [])
    nodes = g.get('nodes', [])
    ensure(isinstance(scene, int) and 0 <= scene < len(scenes), 'missing glTF scene')
    ensure(len(nodes) <= 100_000, 'too many GLB nodes')
    transform = np.array(placement, dtype=np.float64).reshape(4, 4)
    ensure(np.all(np.isfinite(transform)) and 1e-12 < abs(np.linalg.det(transform[:3, :3])) < 1e12,
           'invalid game coordinate transform')
    def walk(idx, parent, ancestors):
        ensure(isinstance(idx, int) and 0 <= idx < len(nodes) and idx not in ancestors, 'node cycle/invalid ID')
        node = nodes[idx]
        matrix = parent @ trs_matrix(node)
        if 'mesh' in node:
            mi = node['mesh']
            ensure(isinstance(mi, int) and 0 <= mi < len(g.get('meshes', [])), 'mesh ID invalid')
            yield idx, g['meshes'][mi], matrix
        for child in node.get('children', []):
            yield from walk(child, matrix, ancestors | {idx})
    for i in scenes[scene].get('nodes', []):
        yield from walk(i, transform, set())


def raw_image(g, binary, index):
    images = g.get('images', [])
    ensure(isinstance(index, int) and 0 <= index < len(images), 'image index outside GLB')
    meta = images[index]
    if 'bufferView' in meta:
        vid = meta['bufferView']
        views = g.get('bufferViews', [])
        ensure(isinstance(vid, int) and 0 <= vid < len(views), 'invalid image bufferView')
        view = views[vid]
        ensure(view.get('buffer') == 0 and view.get('byteLength', 0) > 0, 'invalid embedded image')
        start = view.get('byteOffset', 0)
        length = view['byteLength']
        ensure(start >= 0 and start+length <= len(binary), 'image exceeds GLB')
        raw = bytes(binary[start:start+length])
    elif meta.get('uri', '').startswith('data:'):
        raw = base64.b64decode(meta['uri'].split(',', 1)[1], validate=True)
    else:
        raise ConversionError('External image files are not allowed; pack textures into GLB first')
    ensure(len(raw) <= 64 * 1024 * 1024, 'embedded texture too large')
    try:
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            ensure(0 < im.width <= MAX_TEXTURE_DIM and 0 < im.height <= MAX_TEXTURE_DIM,
                   'full-resolution source texture exceeds D3D9 sidecar limit: %dx%d' % im.size)
            ensure(im.width & (im.width-1) == 0 and im.height & (im.height-1) == 0,
                   'non-power-of-two texture requires explicit pre-processing; no silent resize')
            return im.convert('RGBA')
    except (OSError, ValueError) as exc:
        raise ConversionError('unable to decode source texture') from exc


def resolve_texture(g, binary, material, field):
    # exact material channel only; never substitute arbitrary image nodes
    texinfo = material.get('pbrMetallicRoughness', {}).get('baseColorTexture') if field == 'base' else material.get(field+'Texture')
    if field == 'mr':
        texinfo = material.get('pbrMetallicRoughness', {}).get('metallicRoughnessTexture')
    if not texinfo:
        return None, None
    idx = texinfo.get('index')
    tx = g.get('textures', [])
    ensure(isinstance(idx, int) and 0 <= idx < len(tx), 'invalid texture reference')
    ensure('KHR_texture_transform' not in texinfo.get('extensions', {}),
           'KHR_texture_transform not yet supported; would distort texture mapping')
    ensure(texinfo.get('texCoord', 0) == 0, 'texture uses non-base UV set; cannot preserve both maps')
    tex = tx[idx]
    return raw_image(g, binary, tex['source']), tex['source']


def rgba_dds(image: Image.Image, *, normal=False):
    ensure(image.width > 0 and image.height > 0, 'empty texture')
    ensure(image.width <= MAX_TEXTURE_DIM and image.height <= MAX_TEXTURE_DIM,
           'texture exceeds native sidecar 2048x2048 cap')
    ensure(image.width & (image.width-1) == 0 and image.height & (image.height-1) == 0,
           'texture must have power-of-two dimensions')
    head = bytearray(128)
    head[:4] = b'DDS '
    struct.pack_into('<I', head, 4, 124)
    struct.pack_into('<I', head, 8, 0x0002100F)
    struct.pack_into('<I', head, 12, image.height)
    struct.pack_into('<I', head, 16, image.width)
    struct.pack_into('<I', head, 20, image.width*4)
    mips = int(math.log2(max(image.width, image.height)))+1
    struct.pack_into('<I', head, 28, mips)
    struct.pack_into('<I', head, 76, 32)
    struct.pack_into('<I', head, 80, 0x41)
    struct.pack_into('<I', head, 88, 32)
    struct.pack_into('<4I', head, 92, 0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000)
    struct.pack_into('<I', head, 108, 0x401008)
    b = bytearray(head)
    im = image
    for _ in range(mips):
        rgba = np.asarray(im.convert('RGBA'), dtype=np.uint8)
        b.extend(rgba[:, :, [2, 1, 0, 3]].tobytes(order='C'))
        if im.size == (1, 1):
            break
        next_size = (max(1, im.width//2), max(1, im.height//2))
        im = im.resize(next_size, Image.Resampling.LANCZOS)
        if normal:
            channels = np.asarray(im.convert('RGB'), dtype=np.float32)/127.5-1
            length = np.linalg.norm(channels, axis=2, keepdims=True)
            channels = channels/np.maximum(length, 1e-4)
            out = np.rint(np.clip((channels+1)*127.5, 0, 255)).astype(np.uint8)
            rgba_new = np.concatenate([out, np.full(out.shape[:2]+(1,), 255, dtype=np.uint8)], axis=2)
            im = Image.fromarray(rgba_new, 'RGBA')
    return bytes(b)


def multiply_color(image: Image.Image, factor):
    f = np.asarray(factor, dtype=np.float32)
    ensure(f.shape == (4,) and np.all(np.isfinite(f)) and np.all((f >= 0) & (f <= 1)),
           'invalid baseColorFactor')
    rgba = np.asarray(image.convert('RGBA'), dtype=np.float32)
    return Image.fromarray(np.rint(np.clip(rgba*f, 0, 255)).astype(np.uint8), 'RGBA')


def get_material_textures(g, binary, material):
    base, _ = resolve_texture(g, binary, material, 'base')
    normal, _ = resolve_texture(g, binary, material, 'normal')
    mr, _ = resolve_texture(g, binary, material, 'mr')
    ao, _ = resolve_texture(g, binary, material, 'occlusion')
    pbr = material.get('pbrMetallicRoughness', {})
    base = base or Image.new('RGBA', (16, 16), (255, 255, 255, 255))
    base = multiply_color(base, pbr.get('baseColorFactor', [1, 1, 1, 1]))
    kind = str(material.get('name', '')).lower()
    is_glass = any(t in kind for t in ('window', 'glass', 'windshield'))
    alpha_extrema = base.getextrema()[3]
    # Some GLB exporters mark opaque painted panels as BLEND even when alpha
    # is uniformly 255. Never turn those body panels into see-through glass.
    source_alpha = alpha_extrema[0] < 254
    transparent = is_glass or (material.get('alphaMode', 'OPAQUE') in ('MASK', 'BLEND') and source_alpha)
    if is_glass and alpha_extrema == (255, 255):
        # Name-proven glass without source alpha needs a visible track surface.
        rgba = np.asarray(base).copy()
        rgba[:, :, 3] = np.uint8(round(.20*255))
        base = Image.fromarray(rgba, 'RGBA')
    orm = None
    if mr is not None or ao is not None:
        # glTF MR: roughness G, metal B; occlusion R from occlusionTexture.
        width = (mr or ao).width
        height = (mr or ao).height
        if mr is not None and ao is not None:
            ensure(mr.size == ao.size, 'ORM maps use inconsistent resolutions; cannot pack without resizing')
        mr_rgba = np.asarray(mr if mr else Image.new('RGBA', (width, height), (255, 255, 255, 255)))
        ao_rgba = np.asarray(ao if ao else Image.new('RGBA', (width, height), (255, 255, 255, 255)))
        result = np.full((height, width, 4), 255, dtype=np.uint8)
        result[:, :, 0] = ao_rgba[:, :, 0]
        result[:, :, 1] = mr_rgba[:, :, 1]
        result[:, :, 2] = mr_rgba[:, :, 2]
        orm = Image.fromarray(result, 'RGBA')
    rough = float(pbr.get('roughnessFactor', 1.))
    metal = float(pbr.get('metallicFactor', 1.))
    scale = float(material.get('normalTexture', {}).get('scale', 1.))
    ensure(all(math.isfinite(x) for x in (rough, metal, scale)) and .04 <= rough <= 1 and 0 <= metal <= 1 and 0 <= scale <= 2,
           'PBR material factors invalid/out of native range')
    return base, normal, orm, (rough, metal, scale), transparent


@dataclass
class Geometry:
    group: str
    material: int
    vertices: np.ndarray
    indices: np.ndarray
    binding: int = -1


DASH_KIND = {'speed': 1, 'rpm': 2, 'gear': 3}


def parse_dashboard_bindings(g, metadata):
    """Resolve explicit GLB node -> live dashboard records without name guessing."""
    config = metadata.get('dashboard', {})
    raw = config.get('bindings', []) if isinstance(config, dict) else []
    ensure(isinstance(raw, list) and len(raw) <= 128, 'dashboard bindings must be a bounded list')
    nodes = g.get('nodes', [])
    names = {}
    for i, node in enumerate(nodes):
        name = node.get('name')
        if isinstance(name, str) and name:
            names.setdefault(name, []).append(i)
    node_to_binding = {}
    records = []
    for item in raw:
        ensure(isinstance(item, dict), 'dashboard binding must be an object')
        name = item.get('node')
        kind_name = item.get('kind')
        ensure(isinstance(name, str) and name, 'dashboard node name missing')
        ensure(kind_name in DASH_KIND, 'dashboard kind must be speed/rpm/gear')
        ids = names.get(name, [])
        ensure(len(ids) == 1, 'dashboard node must resolve exactly once: '+name)
        node_id = ids[0]
        ensure('mesh' in nodes[node_id], 'dashboard node has no mesh: '+name)
        ensure(node_id not in node_to_binding, 'dashboard node bound twice: '+name)
        kind = DASH_KIND[kind_name]
        rec = dict(node=name, kind=kind, gear=0, pivot=[0.,0.,0.],
                   axis=[0.,0.,1.], input=[0.,1.], angle_rad=[0.,0.])
        if kind == 3:
            gear = item.get('gear')
            ensure(isinstance(gear, int) and 0 <= gear <= 7, 'gear binding requires gear 0..7')
            rec['gear'] = gear
        else:
            pivot = item.get('pivot')
            axis = item.get('axis')
            input_range = item.get('input')
            angle_deg = item.get('angle_deg')
            ensure(isinstance(pivot, list) and len(pivot) == 3, 'dashboard pivot requires xyz')
            ensure(isinstance(axis, list) and len(axis) == 3, 'dashboard axis requires xyz')
            ensure(isinstance(input_range, list) and len(input_range) == 2, 'dashboard input requires min/max')
            ensure(isinstance(angle_deg, list) and len(angle_deg) == 2, 'dashboard angle_deg requires min/max')
            vals = [float(v) for v in pivot+axis+input_range+angle_deg]
            ensure(all(math.isfinite(v) for v in vals), 'dashboard binding contains nonfinite value')
            ensure(max(abs(float(v)) for v in pivot) < 10000, 'dashboard pivot outside model bounds')
            axis = [float(v) for v in axis]
            axis_len = math.sqrt(sum(v*v for v in axis))
            ensure(.99 <= axis_len <= 1.01, 'dashboard axis must be normalized')
            input_range = [float(v) for v in input_range]
            ensure(input_range[1] > input_range[0], 'dashboard input range invalid')
            angle_deg = [float(v) for v in angle_deg]
            ensure(max(abs(v) for v in angle_deg) <= 720, 'dashboard angle exceeds safety bound')
            rec.update(pivot=[float(v) for v in pivot], axis=axis,
                       input=input_range,
                       angle_rad=[math.radians(v) for v in angle_deg])
        node_to_binding[node_id] = len(records)
        records.append(rec)
    return node_to_binding, records


def collect_groups(g, binary, placement, texture_records, node_bindings):
    materials = g.get('materials', [])
    ensure(1 <= len(materials) <= MAX_MATERIALS, 'material limit (1-64) exceeded')
    parts = defaultdict(list)
    count_triangles = 0
    count_primitives = 0
    bounding = [np.full(3, np.inf), np.full(3, -np.inf)]
    for node_id, mesh, transform in ordered_mesh_nodes(g, placement):
        matrix3 = transform[:3, :3]
        det = np.linalg.det(matrix3)
        ensure(abs(det) > 1e-10, 'degenerate model transform')
        normal_mat = np.linalg.inv(matrix3).T
        for p in mesh.get('primitives', []):
            ensure(p.get('mode', 4) == 4, 'non-triangle mesh primitive not supported')
            ensure('targets' not in p and 'extensions' not in p, 'morph/compressed primitive must be baked first')
            mid = p.get('material', 0)
            ensure(isinstance(mid, int) and 0 <= mid < len(materials), 'invalid material ID')
            attrs = p.get('attributes', {})
            ensure('POSITION' in attrs and 'indices' in p, 'positions and indexed triangles required')
            pos = accessor(g, binary, attrs['POSITION'], components=3)
            ensure(pos.dtype == np.float32, 'positions require FLOAT32 VEC3')
            index = accessor(g, binary, p['indices'], components=1)[:, 0].astype(np.uint32)
            ensure(len(index) % 3 == 0 and len(index) > 0 and np.max(index) < len(pos), 'triangle index invalid')
            if det < 0:
                index = index.reshape(-1, 3)[:, [0, 2, 1]].reshape(-1)
            xyz = pos.astype(np.float64) @ matrix3.T + transform[:3, 3]
            ensure(np.all(np.isfinite(xyz)) and np.max(np.abs(xyz)) < 10_000, 'position exceeds native bounds')
            bounding[0] = np.minimum(bounding[0], xyz.min(axis=0))
            bounding[1] = np.maximum(bounding[1], xyz.max(axis=0))
            if 'NORMAL' in attrs:
                normals = accessor(g, binary, attrs['NORMAL'], components=3).astype(np.float64) @ normal_mat.T
                ensure(np.all(np.isfinite(normals)), 'normal contains NaN')
            else:
                normals = np.zeros_like(xyz)
                tris = index.reshape(-1, 3)
                faces = np.cross(xyz[tris[:, 1]]-xyz[tris[:, 0]], xyz[tris[:, 2]]-xyz[tris[:, 0]])
                for k in range(3):
                    np.add.at(normals, tris[:, k], faces)
            normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-10)
            if 'TEXCOORD_0' in attrs:
                uv = accessor(g, binary, attrs['TEXCOORD_0'], components=2).astype(np.float32)
            else:
                ensure(not materials[mid].get('pbrMetallicRoughness', {}).get('baseColorTexture'),
                       'textured surface missing UV; would lose texture')
                uv = np.zeros((len(xyz), 2), dtype=np.float32)
            ensure('COLOR_0' not in attrs and 'JOINTS_0' not in attrs and 'WEIGHTS_0' not in attrs,
                   'vertex colors/skinned geometry must be baked; not silently discarded')
            ensure(len(uv) == len(pos) and len(normals) == len(pos), 'attribute vertex count mismatch')
            vertex = np.concatenate((xyz.astype(np.float32), normals.astype(np.float32), uv), axis=1)
            ensure(vertex.shape[1] == 8, 'D3D9 FVF stride mismatch')
            parts[(mid, node_bindings.get(node_id, -1))].append((vertex, index))
            count_triangles += len(index)//3
            count_primitives += 1
            ensure(count_triangles <= MAX_TRIANGLES, 'total triangles exceed native sidecar budget')
    ensure(count_triangles > 0 and count_primitives > 0, 'empty model')
    output = []
    batchid = 0
    for mid, binding in sorted(parts, key=lambda k: (texture_records[k[0]][-1], k[0], k[1])):
        transp = texture_records[mid][-1]
        name_prefix = 'EXT_GLASS_' if transp else 'EXT_OPAQUE_'
        for vertex, inds in parts[(mid, binding)]:
            # The model contains original vertex positions and indexed triangles.
            # Split only at 1M vertices/group, NEVER decimate triangles.
            for ix in range(0, len(inds), 3*250_000):
                sub = inds[ix:ix+3*250_000]
                used, mapped = np.unique(sub, return_inverse=True)
                geom = vertex[used]
                ensure(len(geom) <= MAX_VERTEX, 'mesh group exceeds native vertex budget')
                output.append(Geometry(name_prefix+f'{mid:02d}_{batchid:03d}', mid,
                                       geom.astype('<f4', copy=False), mapped.astype('<u4', copy=False),
                                       binding))
                batchid += 1
                ensure(batchid <= MAX_GROUPS, 'draw group count exceeds sidecar limit')
    ensure(len(output) > 0, 'no drawable meshes')
    return output, count_triangles, (bounding[0].tolist(), bounding[1].tolist())


def encode_sidecar(g, binary, metadata):
    matrix = metadata['external_to_game_matrix']
    ensure(len(matrix) == 16, 'explicit 4x4 source-to-game matrix required')
    materials = g.get('materials', [])
    texture_records = [get_material_textures(g, binary, mat) for mat in materials]
    node_bindings, dashboard_specs = parse_dashboard_bindings(g, metadata)
    groups, triangle_count, bounds = collect_groups(g, binary, matrix, texture_records, node_bindings)
    ensure(metadata.get('geometry_space') == 'outrun_local_y_up_meters',
           'only verified game-local metre coordinates accepted')
    # Independent geometry QA: all original triangles appear once in output.
    ensure(sum(len(group.indices)//3 for group in groups) == triangle_count, 'triangle preservation check failed')
    textures = texture_records
    payload = bytearray()
    nv = 0
    nglass = 0
    gpu_bytes = 0
    for group in groups:
        name = group.group.encode('ascii')
        vertex_data = group.vertices.astype('<f4', copy=False).tobytes()
        index_data = group.indices.astype('<u4', copy=False).tobytes()
        payload.extend(struct.pack('<HHIII', len(name), group.material, len(group.vertices), len(group.indices), 4))
        payload.extend(name)
        payload.extend(vertex_data)
        payload.extend(index_data)
        nv += len(group.vertices)
        gpu_bytes += len(vertex_data)+len(index_data)
        if group.group.startswith('EXT_GLASS_'):
            nglass += len(group.indices)//3
    for base, _, _, _, _ in textures:
        raw = rgba_dds(base)
        payload.extend(struct.pack('<I', len(raw)))
        payload.extend(raw)
        gpu_bytes += len(raw)
    payload.extend(b'OVCPBR3!')
    normal_count = 0
    for _, normal, orm, factors, _ in textures:
        payload.extend(struct.pack('<3f', *factors))
        for map in (normal, orm):
            raw = rgba_dds(map, normal=(map is normal)) if map is not None else b''
            payload.extend(struct.pack('<I', len(raw)))
            payload.extend(raw)
            gpu_bytes += len(raw)
        normal_count += normal is not None
    payload.extend(b'OVCDASH4')
    dashboard_groups = [(mesh_index, dashboard_specs[group.binding])
                        for mesh_index, group in enumerate(groups) if group.binding >= 0]
    payload.extend(struct.pack('<I', len(dashboard_groups)))
    for mesh_index, spec in dashboard_groups:
        payload.extend(struct.pack(
            '<4I10f', mesh_index, spec['kind'], spec['gear'], 0,
            *spec['pivot'], *spec['axis'], *spec['input'], *spec['angle_rad']))
    ensure(nv <= MAX_VERTEX and triangle_count <= MAX_TRIANGLES, 'native geometry cap exceeded')
    ensure(gpu_bytes <= MAX_GPU_BYTES and 36+len(payload) <= MAX_SIDECAR_BYTES,
           f'file exceeds native x86 sidecar budget; lossless compressor/streaming needed (GPU {gpu_bytes:,} bytes)')
    header = b'OVRCABH4'+struct.pack('<7I', 4, len(groups), len(materials), nv,
                                    triangle_count, len(payload), zlib.crc32(payload) & 0xffffffff)
    result = header+payload
    ensure(len(result) < MAX_SIDECAR_BYTES, 'sidecar exceeds native loader cap')
    return result, dict(triangles=triangle_count, vertices=nv, groups=len(groups),
                        materials=len(materials), glass_triangles=nglass,
                        normal_map_materials=normal_count,
                        dashboard_nodes=len(dashboard_specs),
                        dashboard_mesh_bindings=len(dashboard_groups),
                        source_images=len(g.get('images', [])), game_bounds=bounds,
                        gpu_payload_bytes=gpu_bytes)


def audit_entry(root, car, strict_source=False):
    car_id = car['id']
    glb = root/'sources'/car_id/'source.glb'
    meta_path = root/'sources'/car_id/'source.json'
    result = dict(id=car_id, name=car['name'], native_source=car.get('native_source'),
                  source_glb_exists=glb.is_file(), source_manifest_exists=meta_path.is_file(),
                  status='SOURCE_MISSING')
    if not glb.is_file() or not meta_path.is_file():
        return result
    try:
        meta = read_json(meta_path)
        ensure(meta.get('car_id') == car_id, 'car source identity mismatch')
        actual = sha256(glb)
        ensure(meta.get('source_sha256') == actual, 'car source SHA-256 mismatch')
        ensure(meta.get('geometry_space') == 'outrun_local_y_up_meters', 'car source native alignment not verified')
        ensure(meta.get('alignment_verified') is True, 'car origin/height/axis calibration not verified')
        ensure(meta.get('model_scope') == 'full_car', 'cockpit-only source is not a complete external car')
        ensure(meta.get('origin_type') in ('external_mod','user_authored'), 'source provenance not declared')
        ensure(len(meta.get('external_to_game_matrix', [])) == 16, 'game coordinate matrix missing')
        result.update(status='READY_PRIVATE_CONVERSION', model_bytes=glb.stat().st_size,
                      sha256=actual, origin_type=meta['origin_type'])
        if strict_source:
            g, binary = load_glb(glb)
            _, dashboard_specs = parse_dashboard_bindings(g, meta)
            if meta.get('dashboard_required') is True:
                ensure(dashboard_specs, 'dashboard_required but no verified bindings supplied')
            result.update(source_meshes=len(g.get('meshes', [])),
                          source_materials=len(g.get('materials', [])),
                          source_textures=len(g.get('textures', [])),
                          source_images=len(g.get('images', [])),
                          dashboard_nodes=len(dashboard_specs))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        result.update(status='BLOCKED_SOURCE_QA', reason=str(exc))
    return result


def command_audit(root, registry, strict_source=False):
    rows = [audit_entry(root, car, strict_source) for car in registry['cars']]
    ready = sum(r['status'] == 'READY_PRIVATE_CONVERSION' for r in rows)
    return {'schema': 1, 'total_cars': len(rows), 'ready_count': ready,
            'missing_count': sum(r['status'] == 'SOURCE_MISSING' for r in rows),
            'blocked_count': sum(r['status'] == 'BLOCKED_SOURCE_QA' for r in rows),
            'results': rows}


def convert_one(root, car):
    status = audit_entry(root, car, strict_source=True)
    ensure(status['status'] == 'READY_PRIVATE_CONVERSION',
           f"{car['id']}: {status['status']} {status.get('reason', '')}")
    src = root/'sources'/car['id']/'source.glb'
    meta = read_json(src.with_name('source.json'))
    g, binary = load_glb(src)
    output, summary = encode_sidecar(g, binary, meta)
    dest = root/'outputs'/car['id']
    dest.mkdir(parents=True, exist_ok=True)
    ovc = dest/(car['id']+'_External_Test.ovc')
    manifest = dest/'conversion_report.json'
    ensure(not ovc.exists() and not manifest.exists(), 'output already exists; never overwrite a previous test without manual backup')
    try:
        ovc.write_bytes(output)
        check_output(ovc)
        summary.update(status='OVRCABH4_DASHBOARD_READY_CONVERSION_PASS_NOT_GAME_TESTED',
                       car_id=car['id'], source_sha256=sha256(src),
                       output_sha256=sha256(ovc), output_bytes=len(output),
                       source_scope=meta['model_scope'], runtime_tested=False,
                       author_rights=meta.get('rights_note', 'USER_MUST_VERIFY'))
        manifest.write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        return summary
    except Exception:
        # Remove only this failed in-flight output; never touch preexisting outputs.
        if not manifest.exists() and ovc.exists():
            ovc.unlink()
        raise


def check_output(ovc: Path):
    """Second-pass file/data validation, independent of exporter data buffers."""
    raw = ovc.read_bytes()
    signature = raw[:8] if len(raw) >= 8 else b''
    ensure(36 <= len(raw) <= MAX_SIDECAR_BYTES and signature in (b'OVRCABH3', b'OVRCABH4'),
           'not OVC3/OVC4 file')
    version, groups, materials, vertices, triangles, payload, crc = struct.unpack_from('<7I', raw, 8)
    expected_version = 4 if signature == b'OVRCABH4' else 3
    ensure(version == expected_version and 0 < groups <= MAX_GROUPS and 0 < materials <= MAX_MATERIALS,
           'invalid OVC header')
    ensure(payload == len(raw)-36 and zlib.crc32(raw[36:]) & 0xffffffff == crc, 'OVC CRC mismatch')
    def dds_at(offset, length):
        ensure(length >= 128 and offset+length <= len(raw), 'DDS byte bounds')
        d = memoryview(raw)[offset:offset+length]
        ensure(bytes(d[:4]) == b'DDS ' and struct.unpack_from('<I', d, 4)[0] == 124 and
               struct.unpack_from('<I', d, 76)[0] == 32, 'DDS header invalid')
        h, w, n = struct.unpack_from('<I', d, 12)[0], struct.unpack_from('<I', d, 16)[0], struct.unpack_from('<I', d, 28)[0]
        ensure(0 < w <= MAX_TEXTURE_DIM and 0 < h <= MAX_TEXTURE_DIM and
               w & (w-1) == 0 and h & (h-1) == 0 and 1 <= n <= 12,
               'DDS dimensions/mip count invalid')
        fmt, bpp = struct.unpack_from('<II', d, 84)
        ensure(fmt == 0 and bpp == 32, 'DDS must be ARGB32')
        required = 128
        for m in range(n):
            required += max(w >> m, 1) * max(h >> m, 1)*4
        ensure(required == length, 'DDS mip payload length mismatch')
    p, nvert, ntri, mem = 36, 0, 0, 0
    for _ in range(groups):
        ensure(p+16 <= len(raw), 'group header outside OVC')
        nl, mid, nv, ni, width = struct.unpack_from('<HHIII', raw, p)
        p += 16
        ensure(0 < nl <= 256 and mid < materials and 0 < nv <= MAX_VERTEX and
               ni >= 3 and ni % 3 == 0 and width in (2, 4), 'group metadata invalid')
        need = nl+32*nv+width*ni
        ensure(need <= len(raw)-p, 'group body truncated')
        name = raw[p:p+nl].decode('ascii')
        ensure(name.startswith(('EXT_OPAQUE_', 'EXT_GLASS_')), 'unexpected group identity')
        p += nl
        arr = np.frombuffer(raw, dtype='<f4', count=nv*8, offset=p)
        ensure(np.all(np.isfinite(arr)) and np.max(np.abs(arr)) < 10_000, 'vertex has invalid components')
        p += 32*nv
        indices = np.frombuffer(raw, dtype='<u4' if width == 4 else '<u2', count=ni, offset=p)
        ensure(int(indices.max()) < nv, 'index outside group vertex bounds')
        p += width*ni
        nvert += nv
        ntri += ni//3
        mem += 32*nv+width*ni
    ensure(nvert == vertices and ntri == triangles, 'geometry totals do not match header')
    for _ in range(materials):
        ensure(p+4 <= len(raw), 'DDS size outside OVC')
        size = struct.unpack_from('<I', raw, p)[0]
        p += 4
        dds_at(p, size)
        mem += size
        p += size
    ensure(raw[p:p+8] == b'OVCPBR3!', 'PBR extension missing')
    p += 8
    for _ in range(materials):
        ensure(p+12 <= len(raw), 'PBR factors truncated')
        rough, metal, scale = struct.unpack_from('<3f', raw, p)
        ensure(math.isfinite(rough) and .039 <= rough <= 1.00001 and
               math.isfinite(metal) and 0 <= metal <= 1.00001 and
               math.isfinite(scale) and 0 <= scale <= 2.00001, 'invalid PBR factors')
        p += 12
        for _ in range(2):
            ensure(p+4 <= len(raw), 'PBR DDS size outside OVC')
            size = struct.unpack_from('<I', raw, p)[0]
            p += 4
            if size:
                dds_at(p, size)
                mem += size
                p += size
    dashboard_bindings = 0
    if signature == b'OVRCABH4':
        ensure(p+12 <= len(raw) and raw[p:p+8] == b'OVCDASH4', 'dashboard extension missing')
        dashboard_bindings = struct.unpack_from('<I', raw, p+8)[0]
        p += 12
        ensure(dashboard_bindings <= groups, 'dashboard binding count invalid')
        seen = set()
        for _ in range(dashboard_bindings):
            ensure(p+56 <= len(raw), 'dashboard record truncated')
            mesh, kind, gear, reserved, *vals = struct.unpack_from('<4I10f', raw, p)
            p += 56
            ensure(mesh < groups and mesh not in seen and kind in (1,2,3) and reserved == 0,
                   'dashboard record identity invalid')
            seen.add(mesh)
            pivot, axis = vals[:3], vals[3:6]
            inp, angles = vals[6:8], vals[8:10]
            ensure(all(math.isfinite(v) for v in vals) and max(abs(v) for v in pivot) < 10000,
                   'dashboard record nonfinite')
            if kind == 3:
                ensure(gear <= 7, 'dashboard gear invalid')
            else:
                axis_len = sum(v*v for v in axis)
                ensure(.9801 <= axis_len <= 1.0201 and inp[1] > inp[0] and
                       max(abs(v) for v in angles) <= 12.566371,
                       'dashboard needle bounds invalid')
    ensure(p == len(raw) and mem <= MAX_GPU_BYTES, 'OVC trailer or GPU budget invalid')
    return dict(sha256=hashlib.sha256(raw).hexdigest(), groups=groups,
                materials=materials, vertices=vertices, triangles=triangles,
                dashboard_bindings=dashboard_bindings, size=len(raw))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['audit','convert','verify'])
    parser.add_argument('--workspace', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--car', help='one of the 16 verified Ferrari registry car IDs')
    parser.add_argument('--strict', action='store_true')
    ns = parser.parse_args(argv)
    root = ns.workspace.resolve()
    registry = read_json(root/'registry.json')
    cars = registry['cars']
    ensure(len(cars) == 16 and len({c['id'] for c in cars}) == 16, 'registry lacks 16 unique cars')
    if ns.car:
        cars = [c for c in cars if c['id'] == ns.car]
        ensure(cars, 'unknown car_id; no guessed mappings')
    if ns.command == 'audit':
        result = command_audit(root, {'cars':cars}, ns.strict)
        out = root/'audit_results.json'
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif ns.command == 'convert':
        results = []
        for car in cars:
            status = audit_entry(root, car, strict_source=True)
            if status['status'] != 'READY_PRIVATE_CONVERSION':
                results.append(status)
                continue
            try:
                results.append(convert_one(root, car))
            except (ValueError, TypeError, OSError) as exc:
                results.append(dict(id=car['id'], status='CONVERSION_BLOCKED', reason=str(exc)))
        print(json.dumps(results, ensure_ascii=False, indent=2))
        if any(r['status'] == 'CONVERSION_BLOCKED' for r in results):
            return 1
    else:
        results=[]
        for car in cars:
            p = root/'outputs'/car['id']/(car['id']+'_External_Test.ovc')
            results.append(dict(id=car['id'], **(check_output(p) if p.exists() else {'status':'OUTPUT_MISSING'})))
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ConversionError, OSError, TypeError, KeyError, json.JSONDecodeError) as e:
        print(f'BLOCKED: {e}', file=sys.stderr)
        sys.exit(2)