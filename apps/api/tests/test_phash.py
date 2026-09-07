"""Tests for perceptual hash."""

import io

import imagehash
from PIL import Image


def test_phash_stable():
    img = Image.new("RGB", (64, 64), color=(10, 20, 30))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    data = buf.getvalue()
    h1 = str(imagehash.phash(Image.open(io.BytesIO(data))))
    h2 = str(imagehash.phash(Image.open(io.BytesIO(data))))
    assert h1 == h2
    assert len(h1) > 8
