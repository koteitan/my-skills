# VOICEVOX

## セットアップ

Docker で動かすのが一番きれい。

```bash
docker pull voicevox/voicevox_engine:cpu-latest
docker run -d --name voicevox --restart unless-stopped \
  -p 127.0.0.1:50021:50021 voicevox/voicevox_engine:cpu-latest
curl -s http://127.0.0.1:50021/version
```

- localhost のみに bind する。ポート 50021 は 8000/8080 とぶつからない
- `--restart unless-stopped` でマシン再起動後も上がる
- GPU 版 (`nvidia-latest`) は `nvidia-container-toolkit` が要る。
  ナレーション用途なら CPU 版で数秒なので急がなくていい

## 合成

`/audio_query` で読み・アクセントを取り、必要なら調整して `/synthesis` に渡す。

```python
import json, urllib.parse, urllib.request
from pathlib import Path

HOST = "http://127.0.0.1:50021"

def _post(path, params, body=None):
    url = f"{HOST}{path}?{urllib.parse.urlencode(params)}"
    headers = {"Content-Type": "application/json"} if body else {}
    req = urllib.request.Request(url, data=body or b"", headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as res:
        return res.read()

def synth(text, out_path, speaker=3, speed=1.0, pitch=0.0, intonation=1.0):
    query = json.loads(_post("/audio_query", {"text": text, "speaker": speaker}))
    query["speedScale"] = speed
    query["pitchScale"] = pitch
    query["intonationScale"] = intonation
    wav = _post("/synthesis", {"speaker": speaker},
                json.dumps(query, ensure_ascii=False).encode("utf-8"))
    Path(out_path).write_bytes(wav)
```

出力は 24000Hz / 16bit / モノラルの wav。

## 話者の選び方

キャラクターとスタイルの一覧は API から取れる。id はスタイル単位。

```bash
curl -s http://127.0.0.1:50021/speakers | python3 -c "
import json,sys
for sp in json.load(sys.stdin):
    print(sp['name'])
    for st in sp['styles']:
        print(f\"  id={st['id']:<4} {st['name']}\")
"
```

## 台詞の書き方

- **数字は読み仮名で書く**。「2乗」より「にじょう」の方が安定する。
  「1」「2」も文脈によっては「イチ」「ニ」と書いた方が意図通りに読む
- 話速は 1.05 くらいが聞きやすい。既定の 1.0 は少し遅い
- 長い台詞は句点で切ると間が入って聞きやすくなる
- キャラクターを使うなら口調を統一する（語尾など）。
  台詞は manifest に残るので、後から一括で直せる形にしておくとよい

## WSL での再生

WSLg の PulseAudio ソケット経由で鳴る。`aplay` は入っていないことが多い。

```bash
paplay --server=unix:/mnt/wslg/PulseServer foo.wav
```

## ライセンス

**規約は2階建てで、両方を守る必要がある。**

1. VOICEVOX ソフトウェア利用規約 <https://voicevox.hiroshiba.jp/term/>
2. **使う音源（キャラクター）ごとの利用規約**。提供元が別で、内容も別

キャラクターごとに条件が違うので、**使う話者の規約を必ず個別に確認する**。
公式サイトの各キャラクターのページからリンクされている。

共通して効いてくる要点:

- 多くの音源は商用・非商用とも無料だが、**クレジット表記が必須**。
  表記の形式（`VOICEVOX:キャラクター名` など）は規約に例示がある
- **クレジットを出さない商用利用は有償契約**になることがある。
  1キャラクターあたり40万円（＋税）という設定の音源もある
- 動画サイトの場合は「説明画面や動画内のクレジットなど、ユーザーが気になって
  見にいった際にはわかる程度のところ」に記載する。
  **画面内に数秒出すだけでなく、概要欄にも書くのが確実**
- YouTube の広告収益・スーパーチャットは非商用の範囲とされる場合がある。
  ただし所属企業以外からのスポンサー案件は有償利用になることが多い
- **キャラクターのイラストや3Dモデルは音源とは別の規約**。
  公式配布素材は自由度が高いが、2次創作物は作者に個別確認が要る
- 禁止事項は概ね共通で、公序良俗違反、政治・宗教活動、
  特定の個人や団体を非難・批判または応援する目的、情報商材、
  嘘やフェイク、風俗営業等、反社会的勢力

規約側に「本ガイドラインに該当するかどうかの質問には原則答えない」と
明記されていることがある。自分で読んで判断する前提で運用する。
規約は更新されうるので、公開前に一度確認すること。
