# Recordings 機能 FAQ とトラブルシューティング

最終更新: 2025-09-02  
関連 Issue: #302, #303, #305, #306

---

## 📖 FAQ（よくある質問）

### Q1. Recordings タブに何も表示されません

**A1. 以下の項目を確認してください：**

1. **RECORDING_PATH が正しく設定されているか**
   ```bash
   # 環境変数を確認
   echo $RECORDING_PATH
   
   # ディレクトリが存在するか確認
   ls -la "$RECORDING_PATH"
   ```

2. **録画ファイルが存在するか**
   ```bash
   # webm/mp4/gif ファイルを検索
   find "$RECORDING_PATH" -name "*.webm" -o -name "*.mp4" -o -name "*.gif"
   ```

3. **recursive_recordings_enabled フラグの設定**
   - デフォルト: `false`（`RECORDING_PATH` 直下のみスキャン）
   - サブディレクトリのファイルを表示したい場合: `config/feature_flags.yaml` で有効化
   ```yaml
   artifacts:
     recursive_recordings_enabled: true
   ```

4. **UI を再起動**
   - Feature Flags を変更した後は bykilt を再起動してください
   ```bash
   # Ctrl+C で停止後
   python bykilt.py
   ```

---

### Q2. GIF プレビューが表示されません（LLM 無効時）

**A2. 以下の項目を確認してください：**

1. **ENABLE_LLM が false に設定されているか**
   ```bash
   # 環境変数を確認
   echo $ENABLE_LLM
   # 期待値: false
   ```

2. **recordings_gif_fallback_enabled フラグが有効か**
   ```yaml
   # config/feature_flags.yaml
   artifacts:
     recordings_gif_fallback_enabled: true
   ```

3. **ffmpeg がインストールされているか**
   ```bash
   # ffmpeg のバージョンを確認
   ffmpeg -version
   
   # インストールされていない場合
   # macOS:
   brew install ffmpeg
   
   # Ubuntu/Debian:
   sudo apt-get install ffmpeg
   
   # Windows:
   # https://ffmpeg.org/download.html からダウンロードして PATH に追加
   ```

4. **ログで GIF 変換エラーを確認**
   ```bash
   # ログファイルを確認
   tail -f logs/action_runner_debug.log | grep -i "gif\|worker"
   ```

5. **手動で GIF が生成されているか確認**
   ```bash
   # 録画ファイルと同じディレクトリに .gif ファイルが生成されているはず
   ls -la "$RECORDING_PATH"/*.gif
   ```

---

### Q3. Recordings タブの読み込みが非常に遅いです

**A3. 以下の対策を試してください：**

1. **recursive_recordings_enabled を無効化**
   - 大量のサブディレクトリがある場合、スキャンに時間がかかります
   ```yaml
   artifacts:
     recursive_recordings_enabled: false  # 単一ディレクトリのみスキャン
   ```

2. **古いアーティファクトをアーカイブ**
   ```bash
   # 90日以上前のアーティファクトをアーカイブ
   mkdir -p artifacts/archive
   find artifacts/ -maxdepth 1 -type d -mtime +90 -exec mv {} artifacts/archive/ \;
   ```

3. **RECORDING_PATH を特定のセッションディレクトリに変更**
   ```bash
   # 最新セッションのみ表示
   export RECORDING_PATH="./artifacts/latest-session"
   ```

4. **定期的なクリーンアップ**
   ```bash
   # 古い GIF ファイルを削除（元の録画は保持）
   find "$RECORDING_PATH" -name "*.gif" -mtime +30 -delete
   ```

---

### Q4. GIF 変換が失敗します

**A4. 以下の項目を確認してください：**

1. **動画ファイルのサイズを確認**
   - 最大サイズ制限: 10MB（設定: `GIF_MAX_SIZE_MB` in `gif_fallback_worker.py`）
   ```bash
   # ファイルサイズを確認
   ls -lh "$RECORDING_PATH"/*.webm
   ```

2. **動画ファイルが破損していないか確認**
   ```bash
   # ffmpeg で動画を再生テスト
   ffmpeg -i "$RECORDING_PATH/Tab-01-recording_001.webm" -f null -
   ```

3. **リトライ回数を確認**
   - ワーカーは最大 3 回自動リトライします
   - ログで `Retry X/3` を確認
   ```bash
   tail -f logs/action_runner_debug.log | grep -i "retry"
   ```

4. **手動で GIF 変換をテスト**
   ```bash
   # 同じ設定で手動変換
   ffmpeg -i input.webm -vf "fps=10,scale=640:-1:flags=lanczos,palettegen" palette.png
   ffmpeg -i input.webm -i palette.png -filter_complex "fps=10,scale=640:-1:flags=lanczos[x];[x][1:v]paletteuse" output.gif
   ```

---

### Q5. UI プロファイルで RECORDING_PATH を設定できますか？

**A5. はい、Browser Settings タブで設定できます：**

1. **Browser Settings タブを開く**
2. **RECORDING_PATH フィールドに入力**
   - 例: `./artifacts/my-session`
3. **保存して実行**

**優先順位**（高い順）：
1. UI設定（Browser Settings）
2. 環境変数 `RECORDING_PATH`
3. デフォルト: `./record_videos`

**確認方法**：
- ログファイルで `recording_path_resolved` イベントを確認
```bash
grep "recording_path_resolved" logs/action_runner_debug.log
```

---

### Q6. Recordings タブと Artifacts タブの違いは？

**A6. 用途と対象ファイルが異なります：**

| 項目 | Recordings タブ | Artifacts タブ |
|------|----------------|----------------|
| **目的** | 録画ファイルのプレビュー専用 | すべてのアーティファクト管理 |
| **対象ファイル** | `.webm`, `.mp4`, `.gif` | 録画、スクリーンショット、マニフェスト、ログなど |
| **プレビュー** | 動画/GIF プレビュー | ファイルパス一覧のみ |
| **Feature Flags** | `recursive_recordings_enabled`<br>`recordings_gif_fallback_enabled` | （なし） |
| **推奨ユースケース** | 過去セッションのビデオ確認 | 全アーティファクトのファイル管理 |

---

## 🔧 トラブルシューティング

### 問題: ffmpeg not available エラー

**症状**：
```
ERROR: ffmpeg not available, GIF conversion will be skipped
```

**原因**：
- ffmpeg がシステムにインストールされていない
- ffmpeg が PATH に含まれていない

**解決方法**：

1. **インストール**
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get update && sudo apt-get install -y ffmpeg
   
   # Windows
   # https://ffmpeg.org/download.html からダウンロード
   # 展開後、C:\ffmpeg\bin\ を環境変数 PATH に追加
   ```

2. **PATH 確認**
   ```bash
   # インストール確認
   which ffmpeg
   ffmpeg -version
   ```

3. **bykilt を再起動**
   ```bash
   python bykilt.py
   ```

---

### 問題: GIF 変換が途中で止まる

**症状**：
- Recordings タブに「変換中...」と表示されたまま
- GIF ファイルが生成されない

**原因**：
- ffmpeg プロセスのハング
- ディスク容量不足
- 動画ファイルの破損

**解決方法**：

1. **ログで詳細を確認**
   ```bash
   tail -100 logs/action_runner_debug.log | grep -A 5 "GifFallbackWorker"
   ```

2. **ディスク容量確認**
   ```bash
   df -h
   ```

3. **ffmpeg プロセスを手動終了**
   ```bash
   # macOS/Linux
   pkill -9 ffmpeg
   
   # Windows
   taskkill /F /IM ffmpeg.exe
   ```

4. **bykilt を再起動**
   ```bash
   python bykilt.py
   ```

5. **問題の動画ファイルを削除またはスキップ**
   ```bash
   # 破損している可能性のあるファイルを移動
   mkdir -p artifacts/problematic
   mv "$RECORDING_PATH"/Tab-XX-*.webm artifacts/problematic/
   ```

---

### 問題: 再帰スキャンでサブディレクトリのファイルが表示されない

**症状**：
- `recursive_recordings_enabled=true` に設定したが、サブディレクトリのファイルが表示されない

**原因**：
- Feature Flag の読み込みタイミング
- キャッシュの影響

**解決方法**：

1. **Feature Flag 設定を再確認**
   ```yaml
   # config/feature_flags.yaml
   artifacts:
     recursive_recordings_enabled: true
   ```

2. **環境変数でオーバーライド**
   ```bash
   export ARTIFACTS_RECURSIVE_RECORDINGS_ENABLED=true
   python bykilt.py
   ```

3. **ファイル構造を確認**
   ```bash
   # サブディレクトリに録画ファイルが存在するか確認
   find "$RECORDING_PATH" -name "*.webm" -o -name "*.mp4"
   ```

4. **ログでスキャン結果を確認**
   ```bash
   grep -i "scan\|recording" logs/action_runner_debug.log | tail -20
   ```

---

### 問題: LLM 有効時も GIF が生成される

**症状**：
- `ENABLE_LLM=true` なのに GIF ファイルが生成される
- ディスク容量が圧迫される

**原因**：
- `recordings_gif_fallback_enabled=true` が設定されている
- ワーカーが起動条件を正しく判定していない

**解決方法**：

1. **Feature Flag を無効化**
   ```yaml
   # config/feature_flags.yaml
   artifacts:
     recordings_gif_fallback_enabled: false
   ```

2. **既存 GIF ファイルを削除（オプション）**
   ```bash
   # 元の録画ファイルは削除しないように注意
   find "$RECORDING_PATH" -name "*.gif" -delete
   ```

3. **bykilt を再起動**
   ```bash
   python bykilt.py
   ```

---

## 📚 関連ドキュメント

- **README.md**: [🎥 Recordings 機能](../README.md#-recordings-機能)
- **Feature Flags**: [FLAGS.md](./feature_flags/FLAGS.md#recordings-機能関連フラグ-issue-302--306)
- **GIF Worker 実装**: `src/workers/gif_fallback_worker.py`
- **テスト**: `tests/workers/test_gif_fallback_worker.py`

---

## 🐛 問題が解決しない場合

以下の情報を添えて Issue を作成してください：

1. **環境情報**
   ```bash
   # Python バージョン
   python --version
   
   # OS バージョン
   uname -a  # macOS/Linux
   systeminfo | findstr /B /C:"OS Name" /C:"OS Version"  # Windows
   
   # ffmpeg バージョン
   ffmpeg -version
   ```

2. **設定情報**
   ```bash
   # 環境変数
   echo $ENABLE_LLM
   echo $RECORDING_PATH
   echo $ARTIFACTS_RECURSIVE_RECORDINGS_ENABLED
   echo $ARTIFACTS_RECORDINGS_GIF_FALLBACK_ENABLED
   
   # Feature Flags
   cat config/feature_flags.yaml | grep -A 3 "artifacts:"
   ```

3. **ログファイル**
   ```bash
   # 直近のエラーログを添付
   tail -100 logs/action_runner_debug.log
   ```

4. **再現手順**
   - 具体的な操作手順
   - 期待される動作と実際の動作
   - スクリーンショットやエラーメッセージ

---

## 📋 チェックリスト（トラブルシューティング）

- [ ] `RECORDING_PATH` が正しく設定されている
- [ ] 録画ファイル（.webm / .mp4）が存在する
- [ ] `ENABLE_LLM` が意図した値（true / false）に設定されている
- [ ] `config/feature_flags.yaml` の設定が正しい
- [ ] ffmpeg がインストールされている（GIF 機能使用時）
- [ ] bykilt を再起動した（設定変更後）
- [ ] ログファイルでエラーを確認した
- [ ] ディスク容量が十分にある
- [ ] 古いアーティファクトをアーカイブした（パフォーマンス問題時）

---

**「魔法の力が思うように発揮されない時、この書を開け。道は必ず開ける」**
