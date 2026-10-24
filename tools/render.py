#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# render_final.py <out.bin> <文本> [字号=26] [行距=38] [字距=1.0] [阈值=180] [X偏移=-36]
import sys
from PIL import Image, ImageDraw, ImageFont
CJK = '/usr/share/fonts/truetype/ayu/SourceHanSerifCN-Regular.otf'
SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
W = 384
PAD = 8
XOFF = -36
fsz = int(sys.argv[3]) if len(sys.argv) > 3 else 26
lh  = int(sys.argv[4]) if len(sys.argv) > 4 else 38
tr  = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
th  = int(sys.argv[6]) if len(sys.argv) > 6 else 180
XOFF = int(sys.argv[7]) if len(sys.argv) > 7 else XOFF
fc = ImageFont.truetype(CJK, fsz); fs = ImageFont.truetype(SYM, fsz)
def has(f, ch):
    try:
        m = f.getmask(ch); return m.size[0] > 0 and m.size[1] > 0
    except Exception: return False
def pick(ch):
    if has(fc, ch): return fc
    if has(fs, ch): return fs
    return fc
d0 = ImageDraw.Draw(Image.new('L',(10,10)))
maxw = W - PAD*2 - 2*abs(XOFF)
lines = []
for raw in open(sys.argv[2], encoding='utf-8').read().split('\n'):
    s = raw.rstrip()
    if s.strip() == '':
        lines.append(('', 0)); continue
    cur = ''
    for ch in s:
        w = sum(d0.textlength(c, font=pick(c)) + tr for c in cur + ch)
        if w <= maxw: cur += ch
        else:
            wc = sum(d0.textlength(c, font=pick(c)) + tr for c in cur)
            lines.append((cur, wc)); cur = ch
    wc = sum(d0.textlength(c, font=pick(c)) + tr for c in cur)
    lines.append((cur, wc))
H = ((PAD*2 + len(lines)*lh + 7)//8)*8
img = Image.new('L', (W, H), 255); d = ImageDraw.Draw(img)
y = PAD
for s, wc in lines:
    x = int((W - wc)//2) + XOFF
    for ch in s:
        f = pick(ch)
        d.text((x, y), ch, font=f, fill=0)
        x += d0.textlength(ch, font=f) + tr
    y += lh
p0 = img.load()
res = Image.new('L', (W, H), 255); rp = res.load()
for yy in range(H):
    for xx in range(W):
        rp[xx, yy] = 0 if p0[xx, yy] < th else 255
pix = res.convert('1').load()
data = bytearray()
for yy in range(H):
    for xb in range(W//8):
        b = 0
        for bit in range(8):
            if pix[xb*8+bit, yy] == 0: b |= (1<<bit)
        data.append(b)
open(sys.argv[1],'wb').write(bytes(data))
print('OK bytes=%d rows=%d xoff=%d' % (len(data), H, XOFF))
