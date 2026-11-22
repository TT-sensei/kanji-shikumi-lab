# データの出典とライセンス

このアプリの漢字データは、役割ごとに3つの層に分けて管理しています。

## data/（外部データ由来）

| データ | 出典 | ライセンス | 使っている内容 |
|---|---|---|---|
| KanjiVG | KanjiVG project（https://kanjivg.tagaini.net） | CC BY-SA 3.0 | 漢字の分解（部品・位置・部首フラグ）と字形（SVGパス） |
| KANJIDIC2 | EDRDG（https://www.edrdg.org/wiki/index.php/KANJIDIC_Project） | CC BY-SA 4.0 | 部首番号（古典214部首）・画数 |

- SKIPコードは使用していません。
- KanjiVGの分解はそのまま正解とせず、教育用に確認し、必要な字は original/ 側のルールで上書きしています（上書き内容は tools/build_data.py の OVERRIDES に記録）。
- 構造分類（左と右／上と下／囲み・かまえ／一つの形／組み合わせ）は、KanjiVGの位置情報から下書きを自動生成し、確認したものです。

## original/（TT-sensei独自データ）

- 学年・読み（音読み／訓読み）・例文：TT-sensei の既存アプリ「かんじマスター」（kanjiapp）の自作データを正として使用。
- 唱え方・子ども向け説明・部首の名前と位置分類の表：このアプリのために独自に作成。

## app（プログラム）

- 画面・操作・学習機能のコード一式。データ層とは分離して管理します。

データ取得日：2026-11-22
