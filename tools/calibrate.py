#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# render_off.py <out.bin> <字体> <字号> <行距> <字距> <阈值> <X偏移> <文本> <是否画刻度>
import sys
from PIL import Image, ImageDraw, ImageFont
SYM = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
W = 384; PAD = 8
out, CJK = sys.argv[1], sys.argv[2]
fsz, lh, tr, th = int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), int(sys.argv[6])
xoff = int(sys.argv[7])
txt = open(sys.argv[8], encoding='utf-8').read()
ruler = (len(sys.argv) > 9 and sys.argv[9] == '1')
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
maxw = W - PAD*2 - abs(xoff)
lines = []
for raw in txt.split('\n'):
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
Hbase = PAD*2 + len(lines)*lh
H = ((Hbase + (90 if ruler else 0) + 7)//8)*8
img = Image.new('L', (W, H), 255); d = ImageDraw.Draw(img)
y = PAD
for s, wc in lines:
    x = max(0, (W - wc)//2 + xoff)
    for ch in s:
        d.text((x, y), ch, font=pick(ch), fill=0)
        x += d.textlength(ch, font=pick(ch)) + tr
    y += lh
if ruler:
    y += 10
    fsm = ImageFont.truetype(SYM, 14)
    # 从 0 到 383 每 24 点一条短刻线，长度按位置递增便于识别
    for xx in range(0, W, 12):
        long = (xx % 96 == 0)
        d.line([(xx, y), (xx, y + (34 if long else 18))], fill=0, width=1)
        if long:
            d.text((min(xx+2, W-30), y+36), str(xx), font=fsm, fill=0)
    d.line([(0, H-4), (W-1, H-4)], fill=0, width=1)
pix0 = img.load()
res = Image.new('L', (W, H), 255); rp = res.load()
for yy in range(H):
    for xx in range(W):
        rp[xx, yy] = 0 if pix0[xx, yy] < th else 255
pix = res.convert('1').load()
data = bytearray()
for yy in range(H):
    for xb in range(W//8):
        b = 0
        for bit in range(8):
            if pix[xb*8+bit, yy] == 0: b |= (1<<bit)
        data.append(b)
open(out,'wb').write(bytes(data))
print('OK bytes=%d rows=%d xoff=%d' % (len(data), H, xoff))
