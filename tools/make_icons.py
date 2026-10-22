"""Draw the QPR Buddy home-screen icon: the crest on blue-and-white hoops."""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "icons")


def icon(size, crest):
    s = 1024
    im = Image.new("RGB", (s, s), "#1d5ba4")
    d = ImageDraw.Draw(im)
    for y in range(0, s, 128):                       # hoops
        d.rectangle((0, y + 96, s, y + 128), fill="#2a6bb8")
    d.ellipse((132, 132, 892, 892), fill="white")
    c = crest.resize((700, 700), Image.LANCZOS)
    im.paste(c, (162, 162), c)
    return im.resize((size, size), Image.LANCZOS)


crest = Image.open(os.path.join(HERE, "crest.png")).convert("RGBA")
for n in (180, 192, 512):
    icon(n, crest).save(os.path.join(OUT, f"icon-{n}.png"))
print("icons written")
