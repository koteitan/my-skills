# 出力の検証

このワークフローの不具合は「レンダリングは成功するが中身が違う」型ばかりで、
**目視と実測をするまで気付けない**。

## 音声が本当に入っているか

manim のキャッシュ再利用で `add_sound` が飛ばされると、
エラーも警告も出ないまま一部の台詞だけが消える。映像は正しい。

### やってはいけない測り方

`silencedetect` の無音合計と wav の合計時間を引き算する方法は**使えない**。

```bash
# これは当てにならない
ffmpeg -i out.mp4 -af "silencedetect=noise=-45dB:d=0.4" -f null /dev/null
```

台詞の中の文と文の間の無音も数えるので、正常な動画でも数秒の差が出て偽陽性になる。
逆に台詞が重なっている場合も同じ数値になるので、欠落と重なりを区別できない。

### 正しい測り方

**各台詞の予定位置で、実際の音量を測る。**

まず `say()` に環境変数で有効になるトレースを仕込む。

```python
def say(self, key: str, text: str, **kw) -> float:
    wav = narrate(self.NARRATION_DIR, key, text, **kw)
    dur = duration_sec(wav)
    if os.environ.get("NARRATION_DEBUG"):
        t = self.time      # Scene.time は renderer.time のプロパティ
        print(f"[say] {key:<14} t={t:7.2f}  dur={dur:5.2f}  -> {t + dur:7.2f}")
    self.add_sound(wav)
    return dur
```

```bash
NARRATION_DEBUG=1 manim -ql --disable_caching scenes/foo.py Scene 2>&1 | grep '^\[say\]'
```

この時点で重なりや抜けがあれば、スケジュール自体の不具合。

```
[say] intro          t=   0.00  dur= 6.91  ->    6.91
[say] step1          t=   7.13  dur= 1.77  ->    8.90
[say] step2          t=   9.20  dur= 8.02  ->   17.22
```

つぎに、その位置に音があるか測る。前後の無音を避けて中央50%だけ見る。

```python
import subprocess, wave, array, math

def load(mp4, tmp="chk.wav"):
    subprocess.run(["ffmpeg","-y","-v","quiet","-i",str(mp4),"-vn","-ac","1",
                    "-ar","8000","-acodec","pcm_s16le",tmp], check=True)
    with wave.open(tmp) as f:
        return array.array("h", f.readframes(f.getnframes())), f.getframerate()

def rms(buf, sr, a, b):
    i, j = max(0, int(a*sr)), min(len(buf), int(b*sr))
    return 0.0 if j <= i else math.sqrt(sum(v*v for v in buf[i:j]) / (j - i))

buf, sr = load("out.mp4")
missing = [k for k, t, d in schedule if rms(buf, sr, t + d*0.25, t + d*0.75) < 60]
```

`rms < 60`（16bit PCM）なら実質無音。台詞が入っていれば数百〜数千になる。

## 絵が正しいか

フレームを抜いて実際に見る。最終フレームと、変化の途中の何点か。

```bash
ffmpeg -y -v error -sseof -1.4 -i out.mp4 -vframes 1 frame.png   # 最終フレーム
ffmpeg -y -v error -ss 30    -i out.mp4 -vframes 1 frame.png     # 30秒地点
```

細部が判断できないときは切り出して拡大する。

```bash
ffmpeg -y -v error -i frame.png -vf "crop=500:120:180:300,scale=1000:240" zoom.png
```

## レンダリングが成功した本数を数える

複数シーンをまとめて焼くとき、**一部だけ落ちても後段は動いてしまう**。
配布やコピーの処理は既存の古いファイルを拾うので、
「全部OK」と表示されても実際には焼き直されていないことがある。

シーンごとに成功数を数えて、期待値と突き合わせる。

```bash
n=$(manim -ql --disable_caching -a scenes/foo.py 2>&1 | grep -ciE "^\s*INFO\s+Rendered")
echo "$f -> $n scenes"
```

リファクタリング直後は特に危ない。変数名の付け替え漏れなどで
一部のシーンだけ実行時エラーになっても、全体の終了コードには出ない。

## 検証スクリプトの偽の合格に注意

**検査対象が0件のまま「全部OK」と出る**のが一番危ない。

manim のログからシーン名を `Rendered (\w+)` で拾おうとして、
manim 自身が出す `'comment=Rendered with` という行に引っかかり、
シーン名を `with` と誤認して全シーンが空になったことがある。それでも合格と表示された。

対策:

- **検査件数を必ず表示し、期待値と一致するか確認する**
- 件数が合わなければ異常終了する

```python
print(f"検査: {checked}/{expected}")
if checked != expected or not allok:
    sys.exit(1)
```

- ログを正規表現で拾うときは前後の文脈込みで一意にする
  （`Rendered (\w+)` ではなく `INFO\s+Rendered\s+(\w+)`）
