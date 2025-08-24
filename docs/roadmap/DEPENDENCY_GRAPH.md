```mermaid
%% Auto-generated dependency graph
%% Edge方向: dependency --> dependent
graph LR

%% Subgraphs by critical_path_rank (higher = earlier in chain)
subgraph R5[Rank 5]
  32["32 Run/Job ID 基盤"]
  65["65 マルチ環境設定ローダ"]
end
subgraph R4[Rank 4]
  28["28 録画ファイル保存パス統一"]
  64["64 フィーチャーフラグ"]
end
subgraph R3[Rank 3]
  25["25 git_script 解決改善 (partial, PR#27)"]
  30["30 録画タイプ不整合是正"]
  31["31 統一ログ設計"]
  35["35 アーティファクト manifest v2"]
  46["46 タイムアウト & キャンセル"]
  63["63 llms.txt スキーマ"]
end
subgraph R2[Rank 2]
  33["33 スクショユーティリティ"]
  36["36 アーティファクト一覧 API"]
  37["37 動画保持期間"]
  39["39 CSV バッチコア"]
  44["44 git_script 不具合修正"]
  47["47 並列実行キュー"]
  53["53 cdp-use 追加タイプ調査"]
  56["56 統一 JSON Lines ロギング実装"]
  58["58 メトリクス基盤"]
  62["62 サンドボックス機能制限"]
end
subgraph R1["Rank 1 (Leaves)"]
  34["34 要素値キャプチャ"]
  38["38 録画回帰テスト"]
  40["40 CSV D&D UI"]
  41["41 バッチ進捗サマリ"]
  42["42 バッチ部分リトライ"]
  43["43 ENABLE_LLM パリティ"]
  45["45 git_script 認証/プロキシ"]
  48["48 環境変数バリデーション"]
  49["49 ユーザースクリプト拡張基盤"]
  50["50 ディレクトリ名変更"]
  51["51 Windows プロファイル永続化"]
  52["52 サンドボックス allow/deny"]
  54["54 cdp-use 抽象レイヤ"]
  55["55 browser_control pytest パス修正"]
  57["57 ログ保持/ローテーション"]
  59["59 Run メトリクス API"]
  60["60 シークレットマスキング拡張"]
  61["61 依存セキュリティスキャン最適化"]
  66["66 ドキュメント第1弾"]
  67["67 ドキュメント第2弾"]
end

%% Edges (depends --> dependent)
32 --> 28
32 --> 31
32 --> 33
32 --> 35
32 --> 46
32 --> 54
32 --> 56
32 --> 58
32 --> 39
32 --> 62

28 --> 30
30 --> 37
30 --> 38
37 --> 38

33 --> 38
33 --> 34
35 --> 34
35 --> 36
35 --> 38
36 --> 38

31 --> 56
56 --> 57
56 --> 60
56 --> 41

39 --> 40
39 --> 41
39 --> 42

46 --> 47
47 --> 51

53 --> 54
58 --> 59
62 --> 52

65 --> 64
65 --> 63
65 --> 43
65 --> 48
64 --> 63
64 --> 43
64 --> 49
63 --> 66
66 --> 67

25 --> 44
25 --> 45
25 --> 49
25 --> 50
44 --> 45

%% Styling definitions (Mermaid syntax uses colon)
classDef highrisk fill:#ffe6e6,stroke:#d40000,stroke-width:2px,color:#000;
classDef progress fill:#e6f4ff,stroke:#0366d6,stroke-width:2px,color:#000;

%% Class assignments
class 31,46,49,54,62 highrisk;
class 25 progress;

%% Legend (pseudo nodes)
subgraph Legend[Legend]
  L1[水色: progress付き Issue]
  L2[薄赤: High Risk]
  L3["Edge: 依存(左) → 従属(右)"]
end
style Legend fill:#fafafa,stroke:#ccc,stroke-dasharray:3 3;
```
