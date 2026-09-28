"""The two AI models, run straight through onnxruntime.

Not through rembg: on some Windows machines Application Control blocks the numba
DLLs rembg imports, so `import rembg` dies even though pip lists it. Talking to
onnxruntime directly needs nothing but numpy, and runs on CPU without torch.

  BiRefNet (lite, 224 MB)  object cutout   - danielgatis/rembg release assets
  LaMa big (fp32, 208 MB)  clean-plate fill - huggingface.co/Carve/LaMa-ONNX

Both are optional: split_layers.py falls back to OpenCV (`--lite`) when a model
file is missing, and says so in layers.json.
"""

import os

import cv2
import numpy as np

from pm_common import MODEL_DIR

MODELS = {
    "birefnet": ("birefnet_lite.onnx",
                 "https://github.com/danielgatis/rembg/releases/download/v0.0.0/"
                 "BiRefNet-general-bb_swin_v1_tiny-epoch_232.onnx", 224005088),
    "lama": ("lama_fp32.onnx",
             "https://huggingface.co/Carve/LaMa-ONNX/resolve/main/lama_fp32.onnx",
             208044816),
}
BIREFNET_SIZE = 1024
LAMA_SIZE = 512          # the Carve export has a fixed 512x512 input
IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
IMAGENET_STD = np.array([0.229, 0.224, 0.225], np.float32)
BYTE_RANGE_THRESHOLD = 1.5   # LaMa output above this is already 0..255

_sessions = {}


def model_path(key):
    return os.path.join(MODEL_DIR, MODELS[key][0])


def available(key):
    path = model_path(key)
    return os.path.exists(path) and os.path.getsize(path) == MODELS[key][2]


def _session(key):
    if key not in _sessions:
        import onnxruntime as ort
        _sessions[key] = ort.InferenceSession(
            model_path(key), providers=["CPUExecutionProvider"])
    return _sessions[key]


def object_alpha(rgb):
    """Soft 0..1 foreground matte of the main object, at the image's size."""
    h, w = rgb.shape[:2]
    x = cv2.resize(rgb, (BIREFNET_SIZE, BIREFNET_SIZE), interpolation=cv2.INTER_AREA)
    x = (x.astype(np.float32) / 255.0 - IMAGENET_MEAN) / IMAGENET_STD
    x = x.transpose(2, 0, 1)[None]
    sess = _session("birefnet")
    out = sess.run(None, {sess.get_inputs()[0].name: x})[0][0, 0]
    out = 1.0 / (1.0 + np.exp(-out))
    out = (out - out.min()) / max(float(out.max() - out.min()), 1e-6)
    return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def _lama_feeds(sess, img, mask):
    feeds = {}
    for inp in sess.get_inputs():
        feeds[inp.name] = mask if "mask" in inp.name.lower() else img
    return feeds


def inpaint(rgb, hole):
    """rgb with the `hole` (bool) region filled by LaMa. Only the hole changes."""
    h, w = rgb.shape[:2]
    img = cv2.resize(rgb, (LAMA_SIZE, LAMA_SIZE), interpolation=cv2.INTER_AREA)
    msk = cv2.resize(hole.astype(np.uint8), (LAMA_SIZE, LAMA_SIZE),
                     interpolation=cv2.INTER_NEAREST)
    img = (img.astype(np.float32) / 255.0).transpose(2, 0, 1)[None]
    msk = (msk > 0).astype(np.float32)[None, None]
    sess = _session("lama")
    out = sess.run(None, _lama_feeds(sess, img, msk))[0][0].transpose(1, 2, 0)
    if float(out.max()) <= BYTE_RANGE_THRESHOLD:
        out = out * 255.0
    out = cv2.resize(np.clip(out, 0, 255).astype(np.uint8), (w, h),
                     interpolation=cv2.INTER_CUBIC)
    result = rgb.copy()
    result[hole] = out[hole]
    return result
