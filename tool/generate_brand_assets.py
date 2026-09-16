"""Generate app icons from the complete, unmodified root logo.png."""

import argparse
import hashlib
import json
import math
from io import BytesIO
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
BACKGROUND = (13, 13, 13, 255)
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def icon(source: Image.Image, size: int, safe_diameter: float) -> Image.Image:
    # Fit the entire rectangle inside the safe circle, not just its opaque pixels.
    scale = size * safe_diameter / math.hypot(source.width, source.height)
    dimensions = (
        max(1, math.floor(source.width * scale)),
        max(1, math.floor(source.height * scale)),
    )
    artwork = source.resize(dimensions, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size))
    canvas.paste(artwork, ((size - artwork.width) // 2, (size - artwork.height) // 2))
    return canvas


def png(image: Image.Image, *, opaque: bool) -> bytes:
    if opaque:
        background = Image.new("RGBA", image.size, BACKGROUND)
        background.alpha_composite(image)
        image = background.convert("RGB")
    result = BytesIO()
    image.save(result, format="PNG", optimize=True)
    return result.getvalue()


def generate() -> dict[str, bytes]:
    original = (ROOT / "logo.png").read_bytes()
    with Image.open(BytesIO(original)) as supplied:
        source = supplied.convert("RGBA")
    outputs = {"web/logo.png": original}
    for density, scale in DENSITIES.items():
        size = round(48 * scale)
        outputs[f"android/app/src/main/res/mipmap-{density}/ic_launcher.png"] = png(
            icon(source, size, 0.9), opaque=True
        )
        size = round(108 * scale)
        outputs[
            f"android/app/src/main/res/drawable-{density}/ic_launcher_foreground.png"
        ] = png(icon(source, size, 66 / 108), opaque=False)
    outputs["android/app/src/main/res/drawable-nodpi/brand_logo.png"] = original
    outputs["web/favicon.png"] = png(icon(source, 32, 0.9), opaque=True)
    outputs["web/icons/apple-touch-icon.png"] = png(
        icon(source, 180, 0.9), opaque=True
    )
    for size in (192, 512):
        outputs[f"web/icons/icon-{size}.png"] = png(
            icon(source, size, 0.9), opaque=True
        )
        outputs[f"web/icons/icon-maskable-{size}.png"] = png(
            icon(source, size, 0.8), opaque=True
        )
    manifest = {
        "source": "logo.png",
        "sourceSha256": hashlib.sha256(original).hexdigest(),
        "width": source.width,
        "height": source.height,
        "preserveEntireImage": True,
        "outputs": {
            name: hashlib.sha256(data).hexdigest()
            for name, data in sorted(outputs.items())
        },
    }
    outputs["assets/branding/manifest.json"] = (
        json.dumps(manifest, indent=2) + "\n"
    ).encode()
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Fail if any generated asset is stale."
    )
    args = parser.parse_args()
    outputs = generate()
    if args.check:
        stale = [
            name
            for name, data in outputs.items()
            if not (ROOT / name).is_file() or (ROOT / name).read_bytes() != data
        ]
        if stale:
            parser.exit(1, "Outdated brand assets:\n" + "\n".join(stale) + "\n")
        print(f"{len(outputs)} brand assets match logo.png.")
        return
    for name, data in outputs.items():
        path = ROOT / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    print(f"Generated {len(outputs)} brand assets without cropping or recoloring.")


if __name__ == "__main__":
    main()
