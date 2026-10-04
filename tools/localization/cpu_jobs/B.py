#!/usr/bin/env python3
import json, os, platform, time
from pathlib import Path

import numpy as np
from PIL import Image

t0=time.perf_counter()
a=np.arange(4096*4096,dtype=np.uint32).reshape(4096,4096)
checksum=int(a.sum(dtype=np.uint64))
img=Image.fromarray((a & 255).astype(np.uint8),mode="L")
bbox=img.getbbox()
elapsed=time.perf_counter()-t0

out=Path("localization/graphics/worker_results/CPU_WORKER_SMOKE_20261004.json")
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps({
    "status":"PASS",
    "worker":os.environ.get("OUTRUN_CPU_WORKER"),
    "role":os.environ.get("OUTRUN_CPU_ROLE"),
    "platform":platform.platform(),
    "cpu_count":os.cpu_count(),
    "numpy_version":np.__version__,
    "pillow_version":Image.__version__,
    "array_shape":[4096,4096],
    "checksum":checksum,
    "bbox":bbox,
    "elapsed_seconds":elapsed
},indent=2)+"\n",encoding="utf-8")
print(out)
