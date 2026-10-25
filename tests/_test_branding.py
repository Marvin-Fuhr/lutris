"""Branding conversion preserves existing asset contracts and source alpha."""

import base64
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

spec = importlib.util.spec_from_file_location("update_branding", "utils/update_branding.py")
assert spec is not None and spec.loader is not None
branding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(branding)
SVG_NS, XLINK_NS = branding.SVG_NS, branding.XLINK_NS
asset_paths, replace_branding = branding.asset_paths, branding.replace_branding


class BrandingTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        icon = self.root / "share/icons/hicolor/16x16/apps/net.lutris.Lutris.png"
        icon.parent.mkdir(parents=True)
        Image.new("RGBA", (16, 16), "red").save(icon)
        self.original_sizes = {}
        for path in asset_paths(self.root):
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == ".png":
                size = (16, 16) if path == icon else (256, 256)
                Image.new("RGBA", size, "red").save(path)
                self.original_sizes[path] = size
            else:
                path.write_text(
                    f'<svg xmlns="{SVG_NS}" width="56mm" height="80mm" viewBox="0 0 56 80">'
                    '<path d="M 0 0 L 56 80"/></svg>'
                )
        self.source = self.root / "source.png"
        Image.new("RGBA", (64, 32), (23, 80, 185, 128)).save(self.source)

    def test_png_sizes_alpha_and_aspect_ratio_are_preserved(self):
        replace_branding(self.source, self.root)
        for path, size in self.original_sizes.items():
            with Image.open(path) as image:
                self.assertEqual(image.size, size)
                self.assertEqual(image.mode, "RGBA")
                self.assertEqual(image.getpixel((size[0] // 2, size[1] // 2))[3], 128)
                self.assertEqual(image.getpixel((size[0] // 2, 0))[3], 0)
                self.assertEqual(image.info.get("interlace", 0), 0)

    def test_svg_keeps_canvas_and_embeds_original_pixels_without_external_links(self):
        paths = replace_branding(self.source, self.root)
        with Image.open(self.source) as source:
            expected_pixels = source.tobytes()
        for path in paths:
            if path.suffix == ".svg":
                svg = ET.parse(path).getroot()
                self.assertEqual(svg.attrib, {"width": "56mm", "height": "80mm", "viewBox": "0 0 56 80"})
                self.assertIsNone(svg.find(f"{{{SVG_NS}}}path"))
                image = svg.find(f"{{{SVG_NS}}}image")
                self.assertIsNotNone(image)
                assert image is not None
                uri = image.attrib[f"{{{XLINK_NS}}}href"]
                self.assertTrue(uri.startswith("data:image/png;base64,"))
                with Image.open(io.BytesIO(base64.b64decode(uri.split(",", 1)[1]))) as embedded:
                    self.assertEqual(embedded.tobytes(), expected_pixels)
