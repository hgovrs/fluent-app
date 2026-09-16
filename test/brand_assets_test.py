import importlib.util
import math
import unittest
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "generate_brand_assets", ROOT / "tool" / "generate_brand_assets.py"
)
branding = importlib.util.module_from_spec(spec)
spec.loader.exec_module(branding)


class BrandAssetsTest(unittest.TestCase):
    def test_generated_assets_match_source(self):
        for name, expected in branding.generate().items():
            with self.subTest(path=name):
                self.assertEqual((ROOT / name).read_bytes(), expected)

    def test_complete_artwork_fits_inside_each_safe_circle(self):
        with Image.open(ROOT / "logo.png") as image:
            source = image.convert("RGBA")
        for size, diameter in [(32, 0.9), (512, 0.8), (108, 66 / 108), (432, 66 / 108)]:
            with self.subTest(size=size, safe_diameter=diameter):
                result = branding.icon(source, size, diameter)
                scale = size * diameter / math.hypot(source.width, source.height)
                width = math.floor(source.width * scale)
                height = math.floor(source.height * scale)
                self.assertLessEqual(math.hypot(width, height), size * diameter)
                left, top = (size - width) // 2, (size - height) // 2
                scaled = source.resize((width, height), Image.Resampling.LANCZOS)
                actual = result.crop((left, top, left + width, top + height))
                self.assertIsNone(
                    ImageChops.difference(scaled, actual).getbbox(alpha_only=False)
                )
                self.assertEqual(result.getpixel((0, 0))[3], 0)

    def test_opaque_icons_use_the_dark_background(self):
        with Image.open(ROOT / "logo.png") as image:
            icon = branding.icon(image.convert("RGBA"), 192, 0.8)
        with Image.open(BytesIO(branding.png(icon, opaque=True))) as result:
            self.assertEqual(result.mode, "RGB")
            self.assertEqual(result.getpixel((0, 0)), branding.BACKGROUND[:3])


if __name__ == "__main__":
    unittest.main()
