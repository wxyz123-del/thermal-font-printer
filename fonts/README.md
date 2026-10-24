# 字体说明（本目录不含字体文件）

出于版权考虑，本仓库**不存放任何字体文件**。请自行获取。

## 挑选原则

一台热敏机只认位图，所以任何 `.ttf` / `.otf` / `.ttc` 都能用，关键看两点：

1. **笔画粗细**。热敏纸只有纯黑纯白，笔画过细的字（细体、描边体）打出来会碎，小字号尤甚。
   小票场景下，**笔画偏粗的字体**读起来最稳。
2. **字库是否完整**。很多「可爱风」字体只做了常用字，甚至只做了拉丁字母。
   上手前建议先验一下（见下方脚本）。

## 怎么验一个字体带不带汉字

```python
from PIL import ImageFont
f = ImageFont.truetype('YourFont.ttf', 40)
for ch in '测试字云我你他ABC123':
    print(ch, f.getmask(ch).size)   # 尺寸含 0 就是缺字
```

或者用 fontTools 更精细地看码表：

```python
from fontTools.ttLib import TTFont
cm = TTFont('YourFont.ttf').getBestCmap()
han = [k for k in cm if 0x4E00 <= k <= 0x9FFF]
print('CJK 个数:', len(han), '总码位:', len(cm))
```

> 经验：`getmask()` 宽度为 0 或极小，就是缺字；缺字时渲染器会退回备选字体，
> 备选也没有就画成空白框——**那是字体的问题，不是打印机的问题**。

## 推荐的开源字体

| 字体 | 授权 | 特点 |
|---|---|---|
| 思源宋体 / Source Han Serif | OFL | 横细竖粗，像印刷 |
| 思源黑体 / Source Han Sans | OFL | 干净，最通用 |
| 霞鹜文楷 / LXGW WenKai | OFL | 圆润，像手写，适合情话 |
| 文鼎明体 / AR PL UMing | 见包内协议 | 老式宋体味 |
| 文鼎楷体 / AR PL UKai | 见包内协议 | 楷书手写感 |
| Noto CJK | OFL | 覆盖最全 |

Debian/Ubuntu 一行装完：

```bash
apt-get install -y fonts-arphic-uming fonts-arphic-ukai \
                   fonts-noto-cjk fonts-lxgw-wenkai
fc-list :lang=zh
```

## 中英混排建议

- 中文用一个确定含汉字的字体（思源、Noto、文楷都行）。
- 英文/数字可以另配一个瘦一点的字体（更好看），渲染器会逐字自动选择。
- 只含英文字母的字体（常见于手写体）**单独用中文会全部空白**，务必配着走。
