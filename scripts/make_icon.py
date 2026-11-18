import sys
from PIL import Image, ImageDraw, ImageFont
out = sys.argv[1]
W, H, SS = 150, 60, 4
img = Image.new("RGBA", (W*SS, H*SS), (0, 0, 0, 0))
# gradient background
grad = Image.new("RGBA", (W*SS, H*SS))
gd = ImageDraw.Draw(grad)
c1, c2 = (0x00, 0xa4, 0xdc), (0xaa, 0x5c, 0xc3)
for x in range(W*SS):
    t = x / (W*SS - 1)
    col = tuple(int(c1[i] + (c2[i]-c1[i])*t) for i in range(3)) + (255,)
    gd.line([(x, 0), (x, H*SS)], fill=col)
mask = Image.new("L", (W*SS, H*SS), 0)
ImageDraw.Draw(mask).rounded_rectangle([0, 0, W*SS-1, H*SS-1], radius=12*SS, fill=255)
img.paste(grad, (0, 0), mask)
d = ImageDraw.Draw(img)
# play triangle
cx, cy, r = 30*SS, 30*SS, 15*SS
d.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(255, 255, 255, 255), width=2*SS)
d.polygon([(cx-5*SS, cy-8*SS), (cx-5*SS, cy+8*SS), (cx+9*SS, cy)], fill=(255, 255, 255, 255))
font = ImageFont.truetype(sys.argv[2] if len(sys.argv) > 2 else "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 19*SS)
d.text((52*SS, 30*SS), "Jellyfin", font=font, fill=(255, 255, 255, 255), anchor="lm")
img = img.resize((W, H), Image.LANCZOS)
img.save(out)
print("ok", img.size)
