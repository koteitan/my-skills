# manim の罠と対処

いずれもエラーを出さずに壊れる。レンダリングは成功するので、
フレームを目視するまで気付けない種類のもの。

## 1. FadeOut は VGroup の子を消せない

### 症状

`FadeOut` で消した mobject が、後のアニメーションで**何事もなかったように復活する**。
消えた直後のフレームでは正しく消えているので、その区間だけ見ても気付けない。

### 原因

`FadeOut.clean_up_from_scene()` はこう動く。

1. `self.interpolate(0)` で mobject を**開始状態に戻す**（不透明度も位置も元通り）
2. `scene.remove(self.mobject)` で画面から外す

対象が `scene.mobjects` の直下にあれば 2 で消える。だが
**追加済み VGroup の子だと `remove` が効かない**。
親がまだ描画されるので、1 で不透明度が戻った子がそのまま再表示される。

### 対処

フェードのあとに親グループから明示的に外す。
グループ側に外す操作をまとめておくと、使う側で忘れない。

```python
class Diagram(VGroup):
    def drop(self, i: int) -> None:
        """要素 i を親グループから外す。

        FadeOut は scene.remove するだけで VGroup の子は消せないので、
        フェードのあとにこれを呼ばないと復活する。
        """
        self.dots.remove(self.dots[i])
        self.labels.remove(self.labels[i])
        if self.edges[i] is not None:
            self.edge_group.remove(self.edges[i])
            self.edges[i] = None
```

```python
self.play(FadeOut(diagram.part(i), shift=UP * 0.6))
diagram.drop(i)
```

末尾の要素を外すなら添字がずれないので後続が安全。
途中を外す場合は添字の付け替えに注意する。

### 関連

同じ理由で、**追加済み VGroup の子に `ReplacementTransform` を使うのも危険**。
変換元が親に残ったまま描画され続ける。対処はどちらか。

- 変換元を別のトップレベル mobject として持つ（`.copy()` して使う）
- グループ全体を1回で変換する

## 2. 強調でスケールしたまま複製する

### 症状

複製して増やした mobject だけ、他より大きい。

### 原因

```python
self.play(dots[i].animate.set_color(HL).scale(1.5))   # 強調
...
ghost = group.copy()                                   # 1.5倍のままコピーされる
```

強調のための拡大を戻さずに `.copy()` すると、拡大が複製先に焼き付く。

### 対処

複製の直前に必ず戻す。倍率は定数にしておくと戻し忘れと数値ずれを防げる。

```python
HILIGHT = 1.5
...
self.play(dots[i].animate.scale(HILIGHT))       # かける
self.play(dots[i].animate.scale(1 / HILIGHT))   # 戻す
```

## 3. MathTex に日本語を入れる

### 症状

```
ValueError: latex error converting to dvi
```

### 原因

manim の既定 TeX テンプレートに CJK の設定が無い。
`MathTex(r"\text{合計} = 3")` のように日本語を混ぜると LaTeX が落ちる。

### 対処

**日本語は `Text()`、数式は `MathTex()`** と分ける。混ぜたいときは `VGroup` で並べる。

```python
note = Text(f"合計 = {a} + {b} = {c}", font_size=25)   # OK
note = MathTex(rf"\text{{合計}} = {c}")                 # 落ちる
```

`Text()` は Pango 経由なのでフォント指定なしで日本語が出る。

### 見つけにくい形

**画面に出していない mobject でも LaTeX は走る**。
作っただけで `self.play` に渡していない `MathTex` があると、
「使っていないのに落ちる」ので原因が分かりにくい。
落ちたら、その場で表示していない `MathTex` も疑う。

## 4. LaTeX の環境ごとの上限

`pmatrix` などの amsmath 行列環境は、**既定で10列まで**（`MaxMatrixCols`）。
それを超えると `Extra alignment tab has been changed to \cr` で落ちる。
列数が動的に決まるなら、列数制限のない `array` を使う。

```python
cols = "c" * len(values)
body = r"\left(\begin{array}{" + cols + "}" + " & ".join(...) + r"\end{array}\right)"
```

manim の既定テンプレートは差し替えにくいので、
プリアンブルをいじるより素の LaTeX 構文で回避する方が早い。

## 5. 変化の前後で配置を別々に計算する

### 症状

図を変化させたとき、**動かしていない部分だけ位置がずれる**。

### 原因

描画クラスが「自分が受け取ったデータの最大値」から配置を決めていると、
変化前（最大値が小さい）と変化後（最大値が大きい）で基準が変わる。

```python
class Diagram(VGroup):
    def __init__(self, values, ...):
        span = max(values)                  # 自分のデータだけを見ている
        base_y = CENTER - span * dy / 2
```

### 対処

配置の基準を**外から渡せる**ようにして、前後で同じ値を使う。

```python
class Diagram(VGroup):
    def __init__(self, values, ref_span=None, ...):
        """ref_span は配置を決める基準。変化の前後で同じ値を渡さないとずれる。"""
        span = max(values) if ref_span is None else ref_span
```

```python
ref = max(before + after)
src = Diagram(before, ref_span=ref)
tgt = Diagram(after,  ref_span=ref)
```

横方向も同じ。要素数が増えるなら**増えた後の幅で間隔を決め、
増える分の余白を空けておく**と、変化のときに全体が動かずに済む。

## 6. 並列コレクションを足すと添字の刻みが変わる

ノードに数字を添えるなど、**既存のコレクションと並ぶものを後から足す**と、
それらを平坦に詰めた VGroup を刻み幅で引いていたコードが黙って壊れる。

```python
# before: (幹, ノード) の2つ組
g.add(self.stems[i], self.dots[i])
dots = [g[2 * i + 1] for i in range(n)]

# after: (幹, ノード, 数字) の3つ組になり、上の 2*i+1 は数字を指してしまう
g.add(self.stems[i], self.dots[i], self.numbers[i])
dots = [g[3 * i + 1] for i in range(n)]
```

刻みで引く設計にするなら、**並び順を docstring に明記する**。
可能なら添字ではなく名前付きのアクセサを用意する方が壊れにくい。

## 7. アニメの実尺と申告値がずれる

「アニメが使った秒数」を自前で積算してナレーションと合わせる場合、
`self.play(..., run_time=X)` の X と積算値が食い違うと少しずつずれる。

- `run_time` を必ず明示し、同じ値を積算する
- 条件分岐で `self.play` を飛ばす場合、積算も飛ばす
- ループ内の `self.play` は回数×run_time を積む

```python
def build(budget):
    elapsed = 0.0
    for item in items:
        self.play(Indicate(item), run_time=0.35)
        elapsed += 0.35
    self.play(..., run_time=0.4)
    elapsed += 0.4
    return elapsed
```
