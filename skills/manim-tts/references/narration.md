# ナレーションとアニメの尺合わせ

## 方針

台詞の wav を先に作って秒数を測り、その秒数にアニメを合わせる。
逆（アニメに合わせて喋らせる）はできないので、常に音声が主。

## 台詞のキャッシュ

レンダリングのたびに TTS を叩き直さないよう、台詞ごとに wav をキャッシュする。
**テキストと合成パラメータのハッシュ**を manifest に持ち、変えた行だけ再合成する。

```python
def _fingerprint(text: str, params: dict) -> str:
    blob = json.dumps({"text": text, **params}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]

def narrate(out_dir, key, text, **params):
    fp = _fingerprint(text, params)
    wav = Path(out_dir) / f"{key}.wav"
    manifest_path = Path(out_dir) / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    if manifest.get(key, {}).get("fingerprint") == fp and wav.exists():
        return wav                                   # 変わっていないので使い回す

    synth(text, wav, **params)
    manifest[key] = {"fingerprint": fp, "text": text, **params}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    return wav
```

**wav は `.gitignore` に入れ、manifest.json だけコミットする。**
manifest に台詞テキストと合成パラメータが全部入っているので、
clone してレンダリングすれば自動で再生成される。情報は失われない。
シーンが増えるたびに wav が積み上がるので、これをやらないとリポジトリが膨らむ。

## 尺の測り方

```python
import wave

def duration_sec(wav_path) -> float:
    with wave.open(str(wav_path), "rb") as w:
        return w.getnframes() / w.getframerate()
```

## Scene 側の API

```python
class NarratedScene(Scene):
    NARRATION_DIR = "assets/audio/narration"
    NARRATION_GAP = 0.25          # 台詞と台詞の間に入れる無音

    def say(self, key, text, **kw) -> float:
        """台詞を現在時刻に差し込み、秒数を返す。待ちは入れない。"""
        wav = narrate(self.NARRATION_DIR, key, text, **kw)
        self.add_sound(wav)
        return duration_sec(wav)

    def say_and_play(self, key, text, *animations, **kw) -> None:
        """台詞を流しながらアニメを再生し、台詞が終わるまで待つ。"""
        gap = kw.pop("gap", self.NARRATION_GAP)
        run_time = kw.pop("run_time", None)
        spoken = self.say(key, text, **kw)

        played = 0.0
        if animations:
            play_kw = {"run_time": run_time} if run_time is not None else {}
            self.play(*animations, **play_kw)
            played = run_time if run_time is not None else 1.0

        remaining = spoken - played + gap
        if remaining > 0:
            self.wait(remaining)

    def say_over(self, key, text, build, **kw) -> None:
        """台詞の尺いっぱいを使って一連のアニメを流す。

        build(budget) は与えられた秒数を使うアニメ列を再生し、使った秒数を返す。
        """
        gap = kw.pop("gap", self.NARRATION_GAP)
        spoken = self.say(key, text, **kw)
        used = build(spoken) or 0.0
        remaining = spoken - used + gap
        if remaining > 0:
            self.wait(remaining)
```

`say_over` の `build` は使った秒数を自分で積算して返す。
`run_time` を明示して同じ値を積むこと。ずれると台詞と絵が合わなくなる。

## シーンをテンプレート化する

同じ流れで題材だけ違う回が続くなら、シーンをコピペせず基底クラスにする。
**罠の対処を基底クラスに閉じ込められる**のが大きい。子で再発しない。

```python
class Lesson(NarratedScene):
    DATA: list = []
    TITLE: str = ""
    LINES: dict = {}          # キー -> 台詞

    def construct(self):
        ...共通の流れ...

class Lesson3(Lesson):
    DATA = [...]
    TITLE = "..."
    LINES = {"intro": "...", "step1": "...", ...}
```

## 新しい言葉は「こう呼ぶことにする」で導入する

視聴者は、聞いた文が**定義なのか、導かれた結果なのか**を判別できないと止まる。
定義だと分かれば「そう決めたのか」で受け流して先へ進めるが、結果だと思うと
「なぜそうなるのか」を自分で確かめ始めて、その間の説明が耳に入らなくなる。

だから**定義には必ず、定義だと分かる言い回しを付ける**。

    悪い: 「2行目の数字は、ノードに貼られたラベルなのだ。」
    良い: 「2行目の数字を、ノードのラベルと呼ぶことにするのだ。」

    悪い: 「これが底なのだ。」
    良い: 「これを底と呼ぶことにするのだ。」

定義に使う言い回しは「〜と呼ぶことにする」「〜と名付ける」「〜と書くことにする」
「〜と決める」。逆に、導かれた結果には「〜になるのだ」「〜が言えるのだ」を当てて、
定義と混ざらないようにする。

**表記そのものにも名前を付ける。** 「見方を変える」「別の書き方をする」と言っても、
何がどう変わったのかを指し示せない。名前があれば、あとから何度でも呼び戻せる。

    悪い: 「ここで見方を変えるのだ。実はこれは、もう木になっているのだ。」
    良い: 「上下2段に分けて描くこの書き方を、2段記法と呼ぶことにするのだ。」
          「もうひとつ書き方を用意するのだ。ラベル記法と呼ぶことにするのだ。」

「見方」「動く」のような、その分野で定義されていない言葉で説明しないこと。
言われた側は何を指しているのか決められない。

## 盛り上げるために、正しくないことを言わない

「刈ったのに、むしろ大きくなった」のような煽りは、その体系で「大きい」が
別の意味に定義されているとき、視聴者に嘘を教えることになる。あとで
「実は小さくなっていました」と訂正する羽目になり、そこまでの理解が崩れる。

言うのは**そのまま見えている事実**だけにする。

    悪い: 「刈ったのに、ヒドラはむしろ大きくなるのだ。」（順序の上では小さくなっている）
    良い: 「刈ると、数列の長さは増えるのだ。」

## マーキングは、その単語を言い終わった瞬間に始める

図に印を付ける、光らせる、線を引くといった動きは、
**それを指す単語を言い終わった丁度その瞬間**に始める。

- 喋りながら同時に動かすと、耳と目が別のものを追うことになって頭に入らない
- かといって文が全部終わるまで待つと、どの言葉の話か分からなくなる

合わせる先は**文の終わりではなく単語の終わり**。

    台詞: 「祖先ではない列には、バツを付けるのだ。この列は、もう見ないのだ。」
    悪い : 言い始めた瞬間からバツが出る
    悪い : 2文とも言い終わってからバツが出る
    良い : 「バツを付ける」を言い終わった瞬間にバツが出る

台詞に複数の指示が入っているなら、**それぞれの単語の直後に**分けて動かす。

    「ひとつ上のノードの祖先を確認して、」  -> 「確認して」の直後に祖先をハイライト
    「祖先ではない列にバツを付けるのだ。」  -> 「バツを付ける」の直後にバツ

### 間を空けるかどうかで作り方が変わる

**間を空けない**（喋りながら絵を動かす）なら、台詞は**1本の wav のまま**にして、
途中の時刻を求めて合わせる。文を切ると文末の抑揚が落ちる。

**間を空ける**（絵が動き終わるまで台詞を待たせる）なら、
**フレーズごとに独立した発話として合成する**。

1本で合成したものの途中に無音を差し込んではいけない。
続きの発話として合成された音声を途中で切ることになり、
前後が不自然にぶつ切れになる。前を向いたまま止まったように聞こえる。

    悪い : 全文を合成 -> 「左にあって、」の位置に無音を挿入
    良い : 「親は、自分より左にあって、」だけを独立して合成

独立した発話なら、それ自体で完結した抑揚が付くので、止まっても不自然にならない。

```python
def say_then(self, key, text, *animations, **kw):
    """台詞を最後まで言い切ってから、アニメを始める。"""
    pause = kw.pop("pause", 0.2)
    run_time = kw.pop("run_time", 1.0)
    spoken = self.say(key, text, **kw)
    self.wait(spoken)
    if animations:
        self.play(*animations, run_time=run_time)
    if pause > 0:
        self.wait(pause)
```

### 途中の時刻の求め方

TTS が返すモーラ長から逆算できる。

```python
def phrase_offset(text, prefix, speaker, speed):
    """text を喋ったとき、prefix を言い終わるまでの秒数。"""
    full = _query(text, speaker)
    n = len(_moras(_query(prefix, speaker)))
    head = sum(_mora_len(m) for m in _moras(full)[:n])
    return (full["prePhonemeLength"] + head) / speed
```

```python
def say_marks(self, key, text, marks, **kw):
    """marks は (cue, アニメの列, 尺)。cue は text の先頭からの一部。"""
    spoken = self.say(key, text, **kw)
    now = 0.0
    for cue, animations, run_time in marks:
        at = 0.0 if cue is None else phrase_offset(text, cue, ...)
        if at > now:
            self.wait(at - now); now = at
        if animations:
            self.play(*animations, run_time=run_time); now += run_time
    remaining = spoken - now + gap
    if remaining > 0:
        self.wait(remaining)
```

cue に台詞の全文を渡せば「言い終わってから」になる。
計算した尺と実際の wav の長さを比べて、誤差が小さいことを一度確かめておくとよい。

## 消すのは、説明が終わってから

**いちばん出やすい不具合。** 説明の途中で物を消してしまうと、
そのあとの言葉が指すものが画面に無く、視聴者は確かめられない。

台詞が「これを消すのだ」と言った瞬間に消したくなるが、
たいていその後の数秒で、消したものの性質を語り続けている。

    台詞: 「刈るのは、いちばん右の列なのだ。上下まとめて刈るのだ」
          「どちらもゼロなのだ。だから親がいなくて、ただ消えるだけなのだ」
    絵  : 台詞の1秒目で消えてしまう
          -> 「いちばん右の列」「上下まとめて」「どちらもゼロ」が確かめられない

必ず3段階に分ける。

1. **まず印を付けて知らせる**（色を変える、光らせる、囲む）
2. **それを見ながら聞くべき説明が全部終わるまで残す**
3. **終わってから消す**

実装上は、印を付ける処理と消す処理をメソッドに分け、
呼ぶ場所を離す。ひとつの関数にまとめると必ず早すぎる。

```python
def mark_cut(self):
    """消す対象に印を付ける。まだ消さない。"""
    self.play(target.animate.set_color(CHILD_COLOR).scale(1.4))
    self.play(Flash(target, color=CHILD_COLOR))

def remove_cut(self):
    """印を付けたものを消す。参照する説明が終わってから呼ぶ。"""
    self.play(FadeOut(self.cut_parts, shift=UP * 0.6))
    self.diagram.drop(self.cut_index)
```

```python
self.say_over("cut", LINES["cut"], lambda b: self.mark_cut())   # 印だけ
self.say_over("explain", LINES["explain"], ...)                 # 見ながら聞く
self.remove_cut()                                               # ここで消す
```

補助線、ハイライト、×印なども同じ。
**消す前に、そのあとの台詞を読み返して、指すものが残っているか確かめる。**

## 台本を1本に繋げるとき

分割してレンダリングしても最終的に1本に繋ぐなら、台詞の書き方が変わる。

- 「前回の動画では」は誤り。**「さっきの例では」**が正しい
- 各パートは終わった感じを出さず、次に繋がるように終わる
- **最初のパートだけ始まる感じ、最後のパートだけ終わる感じ**にする
- まとめのパートで、前のパートで説明済みの内容を説明し直さない。適用するだけ

分割動画として作ったものを後で繋ぐと、この4点が確実に破綻する。
繋ぐ予定なら最初からそう書く。

## 冒頭の掴みは最後に作る

導入の掴みは、動画が全部できてから
**いちばん面白いところを切り抜いて**充てるとよい。
先に書くと、何が面白かったかが分からないまま決め打ちになる。
台本を書く段階では空欄にしておく。

## 音量を整える

TTS の素の出力は小さいので、持ち上げてから天井で抑える。
フレーム単位で必要な減衰量を出し、隣と min を取って標本ごとに補間する。

```python
def limit(x, sr, gain_db=10.0, ceiling_db=-3.0, frame_ms=10.0):
    """x は (標本数, チャンネル数) の float。"""
    x = x * (10.0 ** (gain_db / 20.0))
    n, ch = x.shape
    T = max(1, int(round(sr * frame_ms / 1000.0)))
    nframes = int(np.ceil(n / T))
    if nframes * T - n:
        x = np.concatenate([x, np.zeros((nframes * T - n, ch))])
    frames = x.reshape(nframes, T, ch)

    # チャンネルは連動させる。左右で別の倍率をかけると定位が動く。
    peak = np.max(np.abs(frames), axis=(1, 2))
    level = 20.0 * np.log10(np.maximum(peak, 1e-12))
    frame_gain = np.where(level > ceiling_db, ceiling_db - level, 0.0)

    # 端は 0 dB を隣とみなす。frame_gain <= 0 なので min はそのまま自分になる。
    prev = np.minimum(np.concatenate([[0.0], frame_gain[:-1]]), frame_gain)
    nxt = np.minimum(frame_gain, np.concatenate([frame_gain[1:], [0.0]]))

    t = np.arange(T) / T
    curve = prev[:, None] * (1.0 - t)[None, :] + nxt[:, None] * t[None, :]
    return (frames * (10.0 ** (curve / 20.0))[:, :, None]).reshape(-1, ch)[:n]
```

なぜこれで天井を超えないか。フレーム r の中の倍率は
`min(g[r-1], g[r])` と `min(g[r], g[r+1])` の間を動き、どちらも `g[r]` 以下。
線形補間はその2値の間に収まるので、フレーム内のどの標本も `g[r]` 以下しか掛からない。
`g[r]` はそのフレームのピークを天井へ落とす量なので、超過しない。

境界で不連続にならないのは、フレーム r の終端の値 `min(g[r], g[r+1])` が
フレーム r+1 の始端の値と同じ式になるため。

映像を再エンコードせずに音声だけ入れ替えられる。

```bash
ffmpeg -i in.mp4 -i limited.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k out.mp4
```
