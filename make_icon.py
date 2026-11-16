# -*- coding: utf-8 -*-
"""Логотип и иконки Hassle Chat Mod."""
from PIL import Image, ImageDraw, ImageFilter

S = 1024
SS = 2
W = S * SS


def sc(v):
    return int(round(v * SS))


img = Image.new("RGBA", (W, W), (0, 0, 0, 0))

# --- фон ---
pad, r = sc(26), sc(210)
mask = Image.new("L", (W, W), 0)
ImageDraw.Draw(mask).rounded_rectangle([pad, pad, W - pad, W - pad], radius=r, fill=255)

grad = Image.new("RGB", (1, W))
for y in range(W):
    t = y / (W - 1)
    c0, c1 = (10, 22, 34), (16, 100, 143)
    grad.putpixel((0, y), (
        int(c0[0] + (c1[0] - c0[0]) * t ** 0.85),
        int(c0[1] + (c1[1] - c0[1]) * t ** 0.85),
        int(c0[2] + (c1[2] - c0[2]) * t ** 0.85),
    ))
grad = grad.resize((W, W))

glow = Image.new("L", (W, W), 0)
ImageDraw.Draw(glow).ellipse([-W * 0.25, -W * 0.55, W * 0.75, W * 0.35], fill=120)
glow = glow.filter(ImageFilter.GaussianBlur(sc(90)))
light = Image.new("RGB", (W, W), (90, 210, 255))
bg = Image.composite(light, grad, glow.point(lambda v: int(v * 0.45)))
bg.putalpha(mask)
img = bg.convert("RGBA")
d = ImageDraw.Draw(img)
d.rounded_rectangle([pad, pad, W - pad, W - pad], radius=r,
                    outline=(120, 214, 255, 110), width=sc(3))

# --- облачко ---
bx0, by0, bx1, by1 = sc(200), sc(300), sc(824), sc(690)
br = sc(96)

shadow = Image.new("RGBA", (W, W), (0, 0, 0, 0))
ImageDraw.Draw(shadow).rounded_rectangle(
    [bx0 + sc(6), by0 + sc(16), bx1 + sc(6), by1 + sc(16)], radius=br, fill=(0, 0, 0, 95))
shadow = shadow.filter(ImageFilter.GaussianBlur(sc(16)))
img = Image.alpha_composite(img, shadow)
d = ImageDraw.Draw(img)

d.rounded_rectangle([bx0, by0, bx1, by1], radius=br, fill=(243, 249, 255, 255))
d.polygon([(sc(300), sc(650)), (sc(300), sc(850)), (sc(480), sc(690))],
          fill=(243, 249, 255, 255))

# --- строки текста ---
text_col = (18, 96, 140, 255)
accent = (56, 183, 255, 255)
for x0, y0, x1, h, col in (
    (306, 386, 728, 62, text_col),
    (306, 486, 646, 62, text_col),
    (306, 586, 512, 62, accent),
):
    d.rounded_rectangle([sc(x0), sc(y0), sc(x1), sc(y0 + h)], radius=sc(h // 2), fill=col)

img = img.resize((S, S), Image.LANCZOS)
img.save(r"C:\Users\Alex\HassleChatMod\icon.png")
img.save(r"C:\Users\Alex\HassleChatMod\logo.png")
img.save(r"C:\Users\Alex\HassleChatMod\icon.ico",
         sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (40, 40), (48, 48),
                (64, 64), (96, 96), (128, 128), (256, 256)])
print("ok")
