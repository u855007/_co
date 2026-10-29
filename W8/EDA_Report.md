# IC 設計 EDA 學習與實踐報告

## 一、 什麼是 IC 設計的 EDA？

**EDA (Electronic Design Automation，電子設計自動化)** 是指利用電腦軟體來設計、模擬、驗證以及佈局電路（尤其是積體電路 IC）的技術。

由於現代晶片包含數以億計的電晶體，純手工設計已不可能實現。EDA 軟體將複雜的硬體設計過程轉化為數位化的流程，主要涵蓋以下階段：

1.  **電路設計 (Design Entry):** 使用硬體描述語言 (HDL, 如 Verilog, VHDL, 或 VeryL) 定義電路邏輯。
2.  **邏輯模擬與驗證 (Simulation & Verification):** 在實際製造前，透過軟體測試設計是否符合預期功能（例如：檢查 ALU 的加法是否正確）。
3.  **邏輯合成 (Synthesis):** 將高階的 HDL 代碼轉換為由邏輯閘（NAND, NOR, Flip-Flop）組成的網表 (Netlist)。
4.  **實體設計 (Physical Design / Place & Route):** 決定電晶體在晶圓上的實際位置以及金屬連線的走線。
5.  **簽核 (Sign-off):** 進行最終的時序分析 (STA) 與物理驗證 (DRC/LVS)，確保晶片能被成功製造且能穩定運行。

---

## 二、 AI 自製 EDA 與創新趨勢：`veryl2chip`

傳統 EDA 工具（如 Cadence, Synopsys）極其昂貴且封閉。`veryl2chip` 展現了一種開源且現代化的 AI 輔助 EDA 嘗試。

### 1. VeryL 語言的特性
`veryl2chip` 採用了 **VeryL** 語言。相比於傳統的 Verilog，VeryL 試圖解決以下痛點：
- **語法現代化：** 讓硬體描述更像現代程式語言，減少冗餘。
- **強型別檢查：** 在編譯階段發現更多錯誤，降低模擬時間。

### 2. 從代碼到晶片 (Code to Chip)
該工具鏈試圖實現自動化的流程：
- **自動化合成：** 將 VeryL 代碼直接映射到標準元件庫。
- **web-based 體驗：** 透過 [線上版本](https://ccc-eda.github.io/veryl2chip/web/dist/index.html) 降低門檻，讓開發者無需配置複雜的本地環境即可體驗 IC 設計流程。

---

## 三、 從基礎到實作：Nand2Tetris 與 Hack 電腦

對於初學者，直接進入工業級 EDA 會非常困難。**Nand2Tetris** (以及 `hack-computer` 專案) 提供了一條完美的學習路徑：**從一個 NAND 閘開始，構建出一台完整電腦。**

### 1. 學習階層
- **底層：** 從 NAND $\rightarrow$ XOR/OR/AND $\rightarrow$ Mux $\rightarrow$ ALU $\rightarrow$ CPU。
- **中層：** 使用 HDL (硬體描述語言) 定義元件連線。
- **頂層：** 編寫組合器 (Assembler) 與編譯器 (Compiler)，讓高階語言能在自製的 Hack 硬體上運行。

### 2. 實踐意義
透過 [hack-computer 網頁版](https://ccc-js.github.io/hack-computer/dist/hdl.html)，使用者可以直觀地看到：
- **邏輯映射：** 如何用簡單的邏輯閘組成複雜的算術邏輯單元 (ALU)。
- **模組化設計：** 將複雜的 CPU 分解為指令解碼器、暫存器和 ALU。

---

## 四、 綜合學習路徑建議

若要深入掌握 IC 設計，建議參考以下資源組合：

| 階段 | 推薦資源 | 目標 |
| :--- | :--- | :--- |
| **入門/概念** | `Nand2Tetris` / `hack-computer` | 理解電腦硬體如何從零構建，掌握 HDL 基礎。 |
| **理論深化** | 康乃爾大學 ECE5745 課程 | 學習專業的數位集成電路設計理論、時序分析與功耗優化。 |
| **工具實踐** | `veryl2chip` / `eda-books` | 嘗試現代開源 EDA 工具，學習從描述語言到電路合成的流程。 |
| **知識查閱** | `eda-books` 電子書 | 將實作中的疑問與理論對接，建立系統性的 EDA 知識體系。 |

## 五、 結論

EDA 是 IC 設計的靈魂。從 `Nand2Tetris` 的教育模擬，到 `veryl2chip` 的開源嘗試，我們可以看到 IC 設計正從「極少數人的頂端技術」轉向「更開放、自動化、AI 化」的方向。對於學習者而言，建議**先透過網頁版工具快速建立感性認識 $\rightarrow$ 透過課程建立理論體系 $\rightarrow$ 最後嘗試使用 EDA 工具進行實際設計**。
