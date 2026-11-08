"""Read-only native .sz PMT primitive parser, F50 source import support.
Adapted from the project's pmt_export_base.py. No texture processing and no export APIs.
No original game asset bytes are embedded in this source.
"""
from pathlib import Path
import struct,math,zlib
MAX_PMT_BYTES = 128*1024*1024
MAX_VERTEX_BYTES = 64*1024*1024
def u16(data, off):
    if off < 0 or off + 2 > len(data):
        raise ValueError('u16 out of bounds')
    return struct.unpack_from('<H', data, off)[0]

def u32(data, off):
    if off < 0 or off + 4 > len(data):
        raise ValueError('u32 out of bounds')
    return struct.unpack_from('<I', data, off)[0]

def i32(data, off):
    if off < 0 or off + 4 > len(data):
        raise ValueError('i32 out of bounds')
    return struct.unpack_from('<i', data, off)[0]

def bounds(data, off, length):
    if off < 0 or length < 0 or off + length > len(data):
        raise ValueError('PMT segment out of bounds')
    return off

def unpack(data, fmt, off):
    bounds(data, off, struct.calcsize(fmt))
    return struct.unpack_from(fmt, data, off)

def open_pmt(path):
    raw = path.read_bytes()
    if raw[:2] not in (bytes((120, 156)), bytes((120, 218)), bytes((120, 1))):
        raise ValueError('expected zlib-compressed .sz')
    d = zlib.decompress(raw, max_length=MAX_PMT_BYTES) if hasattr(zlib, 'max_length') else zlib.decompress(raw)
    if len(d) > MAX_PMT_BYTES:
        raise ValueError('expanded PMT exceeds budget')
    obj_count, tex_count, syslen, vidlen = unpack(d, '<4I', 0)
    if obj_count > 4096 or tex_count > 4096 or syslen + vidlen + 16 != len(d):
        raise ValueError('invalid PMT header')
    system, video = (d[16:16 + syslen], d[16 + syslen:])
    if u32(system, 4) != obj_count or u32(system, 8) != tex_count:
        raise ValueError('PMT counts disagree')
    xpr_off = 24 + 60 * obj_count + 4 * (tex_count + 1)
    if system[xpr_off:xpr_off + 4] != b'XPR0':
        raise ValueError('missing XPR0')
    data_size = u32(system, xpr_off + 4) - u32(system, xpr_off + 8)
    offsets = [u32(system, xpr_off + 12 + 20 * i + 4) for i in range(tex_count)]
    if any((off > data_size for off in offsets)):
        raise ValueError('invalid XPR texture offset')
    return {'obj_count': obj_count, 'tex_count': tex_count, 'system': system, 'video': video, 'offsets': offsets, 'data_size': data_size}

def triangulate(raw, topology):
    out = []

    def emit(a, b, c):
        if a != b and b != c and (a != c):
            out.extend((a, b, c))
    if topology == 5:
        for i in range(0, len(raw), 3):
            emit(*raw[i:i + 3])
    elif topology == 6:
        for i in range(len(raw) - 2):
            a, b, c = raw[i:i + 3]
            emit(b, a, c) if i % 2 else emit(a, b, c)
    elif topology == 8:
        for i in range(0, len(raw), 4):
            a, b, c, d = raw[i:i + 4]
            emit(a, b, c)
            emit(a, c, d)
    else:
        raise ValueError('unsupported primitive topology %s' % topology)
    return out

def decode_object(asset, oi):
    sys, vid = (asset['system'], asset['video'])
    if oi < 0 or oi >= asset['obj_count']:
        raise ValueError('object index out of range')
    q = unpack(sys, '<15I', 24 + oi * 60)
    h = unpack(sys, '<13I', q[5])
    fmts = []
    for j in range(h[9]):
        fs = unpack(sys, '<11I', q[12] + j * 44)
        stream, vf, stride, shader = (fs[0], fs[8], fs[9], fs[10])
        if stream != 1 or shader != 0 or (vf, stride) not in ((18, 24), (274, 32)):
            raise ValueError('unsupported Dino FVF/stride/shader: %s' % ((stream, vf, stride, shader),))
        ip = u32(sys, q[1] + j * 4)
        ixoff = u32(sys, ip + 4)
        vp = u32(sys, q[2] + j * 16)
        voff = u32(sys, vp + 4)
        bounds(sys, ixoff, fs[6])
        bounds(vid, voff, fs[7])
        if fs[7] > MAX_VERTEX_BYTES or fs[7] % stride or fs[6] % 2:
            raise ValueError('invalid format buffers')
        fmts.append((vf, stride, ixoff, voff, fs[6] // 2, fs[7] // stride))
    result = []
    if (q[10] - q[9]) % 20 or q[10] < q[9]:
        raise ValueError('invalid vertex group table')
    for gi, goff in enumerate(range(q[9], q[10], 20)):
        fidx, first0, first1, count0, count1 = unpack(sys, '<5I', goff)
        if fidx >= len(fmts):
            raise ValueError('invalid format index')
        vf, stride, ixoff, voff, nic, nvert = fmts[fidx]
        for alpha, first, count in ((0, first0, count0), (1, first1, count1)):
            if count and first + count > h[10]:
                raise ValueError('invalid material group interval')
            for mgi in range(first, first + count):
                mg = unpack(sys, '<8I', q[10] + mgi * 32)
                base, mat, prstart, prcount = mg[:4]
                if mat >= h[11]:
                    raise ValueError('invalid material index')
                global_ids = []
                for pj in range(prcount):
                    pr = unpack(sys, '<4I', q[11] + (prstart + pj) * 16)
                    top, istart, icount = (pr[0], pr[1], pr[2])
                    n = icount * 3 if top == 5 else icount + 2 if top == 6 else icount * 4 if top == 8 else 0
                    if n <= 0 or istart + n > nic:
                        raise ValueError('invalid primitive index interval')
                    ids = [base + u16(sys, ixoff + 2 * (istart + i)) for i in range(n)]
                    if any((v >= nvert for v in ids)):
                        raise ValueError('primitive index exceeds vertices')
                    global_ids.extend(triangulate(ids, top))
                if not global_ids:
                    continue
                mapping = {}
                positions, normals, uvs, indices = ([], [], [], [])
                for old in global_ids:
                    if old not in mapping:
                        off = voff + old * stride
                        v = unpack(vid, '<6f', off)
                        if not all((math.isfinite(x) and abs(x) <= 10000 for x in v)):
                            raise ValueError('invalid vertex float')
                        pos, norm = (v[:3], v[3:6])
                        uv = unpack(vid, '<2f', off + 24) if vf == 274 else (0.0, 0.0)
                        if not all((math.isfinite(x) and abs(x) <= 10000 for x in uv)):
                            raise ValueError('invalid UV')
                        mapping[old] = len(positions)
                        positions.append(tuple(pos))
                        normals.append(tuple(norm))
                        uvs.append(tuple(uv))
                    indices.append(mapping[old])
                moff = q[13] + mat * 88
                tex_index = i32(sys, moff + 24)
                if tex_index < 0 or tex_index >= asset['tex_count']:
                    tex_index = None
                colorid = i32(sys, moff)
                c = unpack(sys, '<4f', q[14] + 72 * colorid) if 0 <= colorid < h[12] else (1.0, 1.0, 1.0, 1.0)
                if not all((math.isfinite(x) for x in c)):
                    c = (1.0, 1.0, 1.0, 1.0)
                result.append({'name': 'object%02d_group%02d_material%03d_a%d' % (oi, gi, mgi, alpha), 'object': oi, 'group': gi, 'material_group': mgi, 'tex_index': tex_index, 'color': [min(1, max(0, float(x))) for x in c], 'alpha': alpha, 'vertices': positions, 'normals': normals, 'uvs': uvs, 'indices': indices})
    return result