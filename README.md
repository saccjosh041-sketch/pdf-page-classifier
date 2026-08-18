# pdf-page-classifier

判斷一份 PDF 裡「每一頁」有哪些內容元素:**表格(table)**、**文字
(text)**、**圖片(image)**。這三種元素可以任意組合出現在同一頁,例如一頁
可能同時有表格、文字、圖片,也可能只有純文字。

提供兩個完全獨立、互不依賴的實作,各自用不同的版面分析引擎:

- `docling_classifier.py`:用 [Docling](https://github.com/docling-project/docling)
- `paddleocr_classifier.py`:用 [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)(PP-StructureV3 / PP-DocLayout)

兩支程式碼互相沒有共用任何東西,可以只裝其中一個來用,也可以兩個都跑再自
己比對結果。

## 輸出格式

每支程式執行後,會把結果印到標準輸出(stdout),是一個 JSON 陣列,每個
元素代表一頁:

```json
[
  {
    "page_number": 1,
    "type": "table+text+image",
    "table_confidence": 0.94
  },
  {
    "page_number": 2,
    "type": "text",
    "table_confidence": null
  }
]
```

- **`type`**:這頁偵測到的元素組合,用 `+` 連接,固定順序是
  `table` → `text` → `image`(不會出現 `text+table` 這種顛倒順序)。如果
  這頁三種都沒偵測到,值會是 `"none"`。
- **`table_confidence`**:這頁裡表格偵測的平均信心分數(0~1),只有在
  底層引擎有提供分數時才會是數字,否則是 `null`。目前 Docling 這個版本
  沒有在表格物件上提供信心分數(永遠是 `null`),PaddleOCR 有。

### 三種元素的判斷方式

| 元素 | 判斷依據 |
|---|---|
| `table` | 這頁偵測到至少一個表格 |
| `text`  | 這頁偵測到任何文字內容(不管是不是在表格裡面) |
| `image` | 這頁偵測到至少一個非表格的視覺區塊(照片、圖表、印章等) |

PaddleOCR 的對應規則,是直接讀它實際使用的 `PP-DocLayout_plus-L` 模型自
己 `config.json` 裡定義的 20 個分類去分組,不是憑經驗猜的:
`table` 對應模型的 `table` 類別;`image` 對應
`image`/`chart`/`seal`(真正屬於圖像類的);其餘 16 類(標題、內文、頁首、
頁尾、參考文獻、公式…)全部歸為 `text`,因為它們本質上都是文字內容。

## 安裝

Docling 依賴 PyTorch、PaddleOCR 依賴 PaddlePaddle,兩者都是體積大、版本
要求嚴格的機器學習框架,**同時裝在同一個環境很容易版本衝突**。強烈建議
分別建立獨立的虛擬環境。

**Docling:**

```bash
python -m venv .venv-docling
.venv-docling\Scripts\pip install -r requirements-docling.txt
```

**PaddleOCR**(`paddlepaddle` 一定要照下面順序、從官方 index 先裝好,單靠
`requirements-paddleocr.txt` 裝不起來):

```bash
python -m venv .venv-paddleocr
.venv-paddleocr\Scripts\pip install setuptools wheel
.venv-paddleocr\Scripts\pip install paddlepaddle -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
.venv-paddleocr\Scripts\pip install -r requirements-paddleocr.txt
```

（以上是 Windows PowerShell 語法;macOS/Linux 把 `.venv-xxx\Scripts\pip`
換成 `.venv-xxx/bin/pip` 即可。）

## 使用方式

```bash
.venv-docling\Scripts\python docling_classifier.py your.pdf > result.json
.venv-paddleocr\Scripts\python paddleocr_classifier.py your.pdf > result.json
```

第一次執行時,兩者都會另外從網路下載模型檔(Docling 從 HuggingFace,
PaddleOCR 從它自己的模型庫),需要一點時間,之後就會用本機快取,不用重
下載。

## 已知限制

- **Python 版本**:PaddlePaddle 的官方 wheel 通常會落後最新的 Python 版本
  一段時間。如果 `pip install paddlepaddle` 找不到相容版本,改用
  Python 3.11~3.13,不要用剛發布沒多久的新版本。
- **Windows 系統地區設定不是 UTF-8 時**:兩支程式開頭都有自我偵測機制,
  如果偵測到目前不是 UTF-8 mode,會自動用 `-X utf8` 重新啟動自己一次。
  這是為了避免 Python 的 `open()` 預設用系統 codepage(例如繁體中文
  Windows 常見的 Big5/cp950)去解碼模型下載下來的設定檔,一旦檔案裡有
  一般的 UTF-8 字元(例如 em dash)就會直接噴 `UnicodeDecodeError`
  崩潰。這個修正是自動的,不需要手動處理。
- **這台機器沒裝 C++ 編譯器(MSVC)時**:`docling_classifier.py` 已經關掉
  PyTorch 的 `torch.compile`(`TORCHDYNAMO_DISABLE=1`)。如果不關,PyTorch
  會在每次做表格結構辨識時嘗試 JIT 編譯,因為找不到編譯器而失敗,對一份
  幾百頁的文件會不斷重試,實測甚至會把整個行程弄崩潰。
- **路徑盡量用純英數字**:Docling 底層的原生 PDF 解析函式庫,在路徑含有
  非 ASCII 字元(例如中文資料夾名稱)時,曾經出現找不到模型檔案的問題。
  建議把這兩支程式放在純英數字的路徑下執行。
- **兩者都沒有做 OCR**(OCR 相關的子功能都被明確關閉),這是版面/結構偵
  測,不是文字辨識。掃描頁(沒有文字層、整頁是圖片)一樣會被正常分類,
  依據的是視覺版面,不是文字內容——很典型的掃描頁通常會被判成只有
  `image`。
