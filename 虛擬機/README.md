# nand2tetris 第 7、8 章 VM 翻譯器

`VMTranslator.py` 將 VM 指令翻成可在 Hack CPU 上執行的組合語言。使用 Python 3.8 以上版本即可，僅需標準函式庫。下列 PowerShell 指令從專案根目錄 `_co` 執行。

## 第 7 章：翻譯並執行 SimpleAdd

```powershell
python .\虛擬機\VMTranslator.py .\07\StackArithmetic\SimpleAdd\SimpleAdd.vm
.\tools\CPUEmulator.bat .\07\StackArithmetic\SimpleAdd\SimpleAdd.tst
```

翻譯結果是同目錄的 `SimpleAdd.asm`。測試腳本將堆疊指標設為 256。程式執行 `7 + 8` 後，`RAM[256]` 的值應為 15，`SP` 應為 257。執行 CPU 模擬器需要 Java。

## 第 8 章：翻譯多檔案遞迴程式

```powershell
python .\虛擬機\VMTranslator.py .\08\FunctionCalls\FibonacciElement
.\tools\CPUEmulator.bat .\08\FunctionCalls\FibonacciElement\FibonacciElement.tst
```

傳入資料夾時，翻譯器會合併該層所有 `.vm` 檔，輸出 `FibonacciElement\FibonacciElement.asm`。此例從 `Sys.init` 呼叫 `Main.fibonacci(4)`，測試預期在 `RAM[261]` 讀到 3。

## 支援指令

| 類別 | 指令或記憶區段 |
| --- | --- |
| 堆疊運算 | `add`、`sub`、`neg`、`eq`、`gt`、`lt`、`and`、`or`、`not` |
| 記憶體存取 | `push`、`pop`，支援 `local`、`argument`、`this`、`that`、`pointer`、`temp`、`static`。`constant` 支援 `push` |
| 流程控制 | `label`、`goto`、`if-goto`，各函式可使用同名標籤 |
| 函式 | `function`、`call`、`return`，支援巢狀呼叫與遞迴 |

預設 `--bootstrap auto` 會檢查輸入是否定義 `Sys.init`。有定義時，程式先設定 `SP = 256` 並呼叫 `Sys.init`。其餘情況由測試腳本設定起始狀態。可用 `--bootstrap always` 要求輸入提供 `Sys.init`，或用 `--bootstrap never` 交由外部程式初始化。

## 參考

- [課程範例與測試程式](https://github.com/ccc115a/co/tree/main/nand2tetris/08)
- [nand2tetris Project 7](https://www.nand2tetris.org/project07)
- [nand2tetris Project 8](https://www.nand2tetris.org/project08)
