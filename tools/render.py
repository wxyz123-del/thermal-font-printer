#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""thermal_font.py -- PD01 热敏打印机 · 可换字体文本渲染器

把一段文字渲染成 384 点宽、1-bit 的位图字节流（.bin），可直接喂给 bt_print。

用法
----
    python3 thermal_font.py OUT.bin TEXT.txt [选项]

选项
----
    --font PATH      中文字体（.ttf/.otf/.ttc）
    --latin PATH     拉丁字体（英文/数字），默认 DejaVuSans
    --size N         字号，默认 26
    --lh N           行距，默认 38
    --track F        字距（每字额外加多少点），默认 1.0
    --thresh N       二值化阈值 0-255：越大笔画越胖越黑，默认 180
    --xoff N         横向整体偏移（负 = 往左），默认 0；热敏机常见 -30 ~ -40
    --ruler          纸底打印刻度尺（用于校准偏移）
    --calib          打印校准对比页：同一句话 x 五档偏移，各带两条界限竖线

原理见 docs/字体.md。许可：GPL-3.0
"""
import argparse
from PIL import Image, ImageDraw, ImageFont

W = 384          # PD01 打印头宽度（点）
PAD = 8
NL = chr(10)
DEFAULT_CJK = '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
DEFAULT_LAT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def load(path, size):
    return ImageFont.truetype(path, size)


def has_glyph(font, ch):
    """这个字体里到底有没有这个字。没有则 getmask 返回空。"""
    try:
        m = font.getmask(ch)
        return m.size[0] > 0 and m.size[1] > 0
    except Exception:
        return False


def build_picker(cjk, latin):
    """逐字符挑字体：中文优先，缺字退拉丁，再不济退回中文字体（不出空框）。"""
    def pick(ch):
        if has_glyph(cjk, ch):
            return cjk
        if has_glyph(latin, ch):
            return latin
        return cjk
    return pick


def pack(img, h, thresh):
    """灰度图 -> 1-bit 位图字节流。每行 384/8 = 48 字节。"""
    src = img.load()
    res = Image.new('L', (W, h), 255)
    rp = res.load()
    for yy in range(h):
        for xx in range(W):
            rp[xx, yy] = 0 if src[xx, yy] < thresh else 255
    pix = res.convert('1').load()
    data = bytearray()
    for yy in range(h):
        for xb in range(W // 8):
            b = 0
            for bit in range(8):
                if pix[xb * 8 + bit, yy] == 0:
                    b |= (1 << bit)
            data.append(b)
    return bytes(data)


def wrap_lines(text, pick, measure, maxw, track):
    """按宽度换行。英文尽量在空格处断行，中文可任意断开。

    做法：边累加边记「最后一个可断点」。溢出时若有断点就回退到断点，
    否则（纯中文长串）才硬断。
    """
    out = []
    for raw in text.split(NL):
        s = raw.rstrip()
        if s.strip() == '':
            out.append(('', 0))
            continue
        cur = ''
        last_break = -1        # cur 里最后一个可断位置（空格之后）
        for ch in s:
            w = sum(measure(c, pick(c)) + track for c in cur + ch)
            if w <= maxw:
                cur += ch
                if ch in ' \t':
                    last_break = len(cur)
                continue
            if last_break > 0:
                head = cur[:last_break].rstrip()
                tail = cur[last_break:] + ch
                out.append((head, sum(measure(c, pick(c)) + track for c in head)))
                cur = tail
                last_break = -1
            else:
                out.append((cur, sum(measure(c, pick(c)) + track for c in cur)))
                cur = ch
            if cur and cur[-1] in ' \t':
                last_break = len(cur)
        out.append((cur, sum(measure(c, pick(c)) + track for c in cur)))
    return out


def render(text, cjk_path, latin_path, size, lh, track, thresh, xoff, ruler,
           align='center'):
    cjk = load(cjk_path, size)
    latin = load(latin_path, size)
    pick = build_picker(cjk, latin)
    probe = ImageDraw.Draw(Image.new('L', (10, 10)))

    def measure(ch, font):
        return probe.textlength(ch, font=font)

    maxw = W - PAD * 2 - 2 * abs(xoff)
    lines = wrap_lines(text, pick, measure, maxw, track)

    hbase = PAD * 2 + len(lines) * lh + (90 if ruler else 0)
    h = ((hbase + 7) // 8) * 8
    img = Image.new('L', (W, h), 255)
    d = ImageDraw.Draw(img)

    # align='block' 时：所有行统一左边界，取「最宽那行」来居中，避免参差不齐
    if align == 'block':
        widest = max((wc for _, wc in lines), default=0)
        base_x = int((W - widest) // 2) + xoff
    else:
        base_x = None

    y = PAD
    for s, wc in lines:
        x = base_x if base_x is not None else int((W - wc) // 2) + xoff
        for ch in s:
            f = pick(ch)
            d.text((x, y), ch, font=f, fill=0)
            x += measure(ch, f) + track
        y += lh

    if ruler:
        y += 10
        small = ImageFont.truetype(latin_path, 14)
        for xx in range(0, W, 12):
            is_long = (xx % 96 == 0)
            d.line([(xx, y), (xx, y + (34 if is_long else 18))], fill=0, width=1)
            if is_long:
                d.text((min(xx + 2, W - 30), y + 36), str(xx), font=small, fill=0)
        d.line([(0, h - 4), (W - 1, h - 4)], fill=0, width=1)

    return pack(img, h, thresh), h


def render_calib(text, cjk_path, latin_path, size, lh, track, thresh, offsets):
    """校准页：同一句话重复 N 次，每次用不同 xoff，并在该行下方画两条竖线
    标出这行字的左右端。挑「两条竖线离纸的左右边一样远」的那一行，
    它的偏移量就是这台机器该用的值。
    """
    cjk = load(cjk_path, size)
    latin = load(latin_path, size)
    pick = build_picker(cjk, latin)
    probe = ImageDraw.Draw(Image.new('L', (10, 10)))

    def measure(ch, font):
        return probe.textlength(ch, font=font)

    line = text.strip().split(NL)[0]
    labels = 'ABCDEFGH'
    block = lh + 18
    h = ((PAD * 2 + len(offsets) * block + 7) // 8) * 8
    img = Image.new('L', (W, h), 255)
    d = ImageDraw.Draw(img)

    y = PAD
    for i, off in enumerate(offsets):
        lab = labels[i] if i < len(labels) else str(i + 1)
        parts = [(lab, latin), ('  ', latin)] + [(c, pick(c)) for c in line]
        wc = sum(measure(c, f) + track for c, f in parts)
        x0 = int((W - wc) // 2 + off)
        x = x0
        for c, f in parts:
            d.text((x, y), c, font=f, fill=0)
            x += measure(c, f) + track
        yy = y + lh + 3
        d.line([(max(0, x0), yy), (max(0, x0), yy + 12)], fill=0, width=2)
        d.line([(min(W - 1, int(x0 + wc)), yy),
                (min(W - 1, int(x0 + wc)), yy + 12)], fill=0, width=2)
        y += block

    d.line([(0, h - 2), (W - 1, h - 2)], fill=0, width=1)
    return pack(img, h, thresh), h


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('text')
    ap.add_argument('--font', default=DEFAULT_CJK)
    ap.add_argument('--latin', default=DEFAULT_LAT)
    ap.add_argument('--size', type=int, default=26)
    ap.add_argument('--lh', type=int, default=38)
    ap.add_argument('--track', type=float, default=1.0)
    ap.add_argument('--thresh', type=int, default=180)
    ap.add_argument('--xoff', type=int, default=0)
    ap.add_argument('--ruler', action='store_true')
    ap.add_argument('--calib', action='store_true', help='打印偏移校准对比页')
    ap.add_argument('--align', default='center', choices=['center', 'block'],
                    help='center=逐行各自居中；block=按最宽行统一左边界（诗歌用）')
    a = ap.parse_args()

    text = open(a.text, encoding='utf-8').read()
    if a.calib:
        offs = [0, -24, -48, -72, -96]
        data, rows = render_calib(text, a.font, a.latin, a.size, a.lh,
                                  a.track, a.thresh, offs)
    else:
        data, rows = render(text, a.font, a.latin, a.size, a.lh,
                            a.track, a.thresh, a.xoff, a.ruler, a.align)
    open(a.out, 'wb').write(data)
    print('OK bytes=%d rows=%d xoff=%d font=%s' %
          (len(data), rows, a.xoff, a.font.split('/')[-1]))


if __name__ == '__main__':
    main()
