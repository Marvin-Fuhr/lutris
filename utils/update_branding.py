#!/usr/bin/env python3
"""Replace Lutris branding with an image, preserving every asset's dimensions.

PNG assets remain non-interlaced 8-bit RGBA. SVG containers embed a lossless PNG;
a supplied raster logo is not misrepresented as a traced vector drawing. No
background removal, cropping, recolouring or generative reconstruction is applied.
"""

import argparse
import base64
import io
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image, ImageOps

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"


def asset_paths(root):
    icons = root / "share/icons/hicolor"
    return sorted(
        [
            *icons.glob("*/apps/net.lutris.Lutris.png"),
            *icons.glob("*/mimetypes/application-x-lutris.png"),
            icons / "scalable/apps/net.lutris.Lutris.svg",
            icons / "scalable/mimetypes/application-x-lutris.svg",
            *(
                root / "share/lutris/media" / name
                for name in (
                    "logo.png",
                    "logo.svg",
                    "default_icon.png",
                    "default_banner.png",
                    "side-dark.svg",
                    "side-light.svg",
                    "splash-dark.svg",
                    "splash-light.svg",
                )
            ),
        ]
    )


def replace_branding(source, root):
    with Image.open(source) as original:
        original.load()
        image = ImageOps.exif_transpose(original).convert("RGBA")
    payload = io.BytesIO()
    image.save(payload, format="PNG", optimize=True)
    encoded = base64.b64encode(payload.getvalue()).decode("ascii")
    paths = asset_paths(root)
    # Validate all targets before changing any file.
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.suffix == ".svg":
            ET.parse(path)
        else:
            with Image.open(path) as old:
                old.verify()
    ET.register_namespace("", SVG_NS)
    ET.register_namespace("xlink", XLINK_NS)
    for path in paths:
        if path.suffix == ".png":
            with Image.open(path) as old:
                size = old.size
            resized = ImageOps.contain(image, size, Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", size, (0, 0, 0, 0))
            canvas.paste(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2))
            canvas.save(path, format="PNG", optimize=True)
        else:
            original_root = ET.parse(path).getroot()
            attributes = {key: original_root.attrib[key] for key in ("width", "height", "viewBox")}
            x, y, width, height = attributes["viewBox"].split()
            svg = ET.Element(f"{{{SVG_NS}}}svg", attributes)
            ET.SubElement(
                svg,
                f"{{{SVG_NS}}}image",
                {
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                    "preserveAspectRatio": "xMidYMid meet",
                    f"{{{XLINK_NS}}}href": "data:image/png;base64," + encoded,
                },
            )
            ET.ElementTree(svg).write(path, encoding="UTF-8", xml_declaration=True)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Original PNG image; alpha is preserved")
    args = parser.parse_args()
    for path in replace_branding(args.image, Path(__file__).resolve().parents[1]):
        print(path)


if __name__ == "__main__":
    main()
