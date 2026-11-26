# 第 12 週 · Jack 編譯器

編譯器使用 Python 3.10 以上版本與標準函式庫。它會將 Jack 原始碼轉成可由 nand2tetris VM 模擬器執行的 `.vm` 檔案。

## 編譯

從 `_co` 根目錄執行，可傳入單一 `.jack` 檔案或含有多個類別的程式資料夾。

```powershell
python .\w12\JackCompiler.py .\11\Seven\Main.jack -o .\build\Seven
python .\w12\JackCompiler.py .\11\Pong -o .\build\Pong
```

省略 `-o` 時，`.vm` 檔與原始碼放在同一個資料夾。啟動 `.\tools\VMEmulator.bat` 後，載入編譯輸出的資料夾即可執行。

## 執行第 11 章的測試

從 `_co` 根目錄執行下列指令。測試需要 JDK 11 以上版本，會在暫存目錄編譯第 11 章的範例，並用專案附帶的 VM 模擬器執行。

```powershell
python .\w12\verify_project11.py
```

| 測試 | 驗證結果 |
| --- | --- |
| Seven | 畫面顯示 7 |
| ConvertToBin | `RAM[8001..8016]` 的 16 個位元都與輸入相符 |
| Square | 方塊能移動、放大、縮小和結束 |
| Average | 輸入 4、−2、10，畫面顯示平均值 4 |
| Pong | 擊球後畫面得分從 0 變為 1 |
| ComplexArrays | 五組輸出為 5、40、0、77、110 |

`jack_syntax.py` 將原始碼切成詞元並建立語法樹。`JackCompiler.py` 建立類別和副程式的符號表，再將物件、陣列、字串、運算與流程控制轉成 VM 指令。

[nand2tetris Project 11 規格](https://www.nand2tetris.org/project11)
