# 機能提案: git-scriptのURL評価制限緩和（許可ドメイン設定機能）

## 概要

git-scriptを利用する際、現在はgithub.com以外のGitリポジトリURLを許容しない仕様になっています。この制限を緩和し、環境変数またはUIから独自ドメイン（社内GitLab、GitHub Enterprise、その他Gitホスティングサービス）を許可リストに追加できる機能を実装します。これにより、エンタープライズ環境やローカル開発、SaaS利用など様々なユースケースに対応可能となります。

## 目的

- **ユーザーにとっての価値**: 社内GitLabやGitHub Enterpriseなど、独自ドメインのGitリポジトリからスクリプトを直接実行できるようになり、利便性が大幅に向上
- **プロジェクトにとっての価値**: エンタープライズ環境での採用障壁を取り除き、多様な運用環境に対応
- **技術的な改善点**: セキュリティを維持しつつ柔軟性を向上、設定可能な許可リスト方式で安全性を確保

## 背景 / 現状の課題

### 現状
- `src/script/git_script_resolver.py`内の複数箇所で`github.com`のみをハードコードで許可
  - `_is_safe_git_url()`: L298 - `https://github.com/` または `git@github.com:` のみ許可
  - `_resolve_from_git()`: L397 - `'github.com' not in parsed_url.netloc` チェック
  - `validate_git_script_info()`: L482 - `parsed_url.netloc != 'github.com'` チェック

### 課題
1. **エンタープライズ環境での制約**: 社内GitLabやGitHub Enterpriseが使用できない
2. **開発環境での制約**: ローカルGitサーバーでのテストができない
3. **他Gitホスティングサービスの非対応**: BitBucket、GitLab.comなどが利用不可
4. **拡張性の欠如**: 新しいGitホスティングサービスへの対応に都度コード修正が必要

### 影響
- エンタープライズユーザーがgit-script機能を利用できず、2bykiltの価値が制限される
- セキュリティポリシー上、外部github.comへの接続が制限されている環境で利用不可
- 開発時のテスト効率が低下

## 提案内容（機能仕様）

### 1. 環境変数による許可ドメイン設定

**実装内容**:
```bash
# 環境変数での設定例
GIT_SCRIPT_ALLOWED_DOMAINS="github.com,gitlab.example.com,github.enterprise.local"
```

- カンマ区切りで複数ドメインを指定可能
- `github.com`はデフォルトで常に許可（後方互換性）
- 空文字列の場合はデフォルト（github.comのみ）

**技術的アプローチ**:
- `config/base/core.yaml`に新セクション追加
- 環境変数`GIT_SCRIPT_ALLOWED_DOMAINS`で上書き可能
- `ConfigManager`経由でアクセス

### 2. UIからの動的許可ドメイン追加

**実装内容**:
- Gradio UI「🔧 Settings」タブ内に新セクション「Git Script Domains」追加
- テキストエリアで許可ドメインリストを編集・保存
- 現在の許可ドメイン一覧を表示
- 追加・削除・リセット機能

**UI要素**:
```python
# 疑似コード
gr.Markdown("### 🔐 Git Script Allowed Domains")
gr.Textbox(
    label="Allowed Domains (comma-separated)",
    placeholder="github.com,gitlab.example.com",
    value=current_domains,
    info="Domains allowed for git-script URL validation"
)
gr.Button("Save Domains")
gr.Button("Reset to Default")
gr.Markdown("**Current**: github.com, gitlab.example.com")
```

**技術的アプローチ**:
- 設定はランタイムで保存（セッション単位またはファイル永続化）
- Feature Flagで機能の有効/無効を制御可能

### 3. git_script_resolverのリファクタリング

**変更箇所**:

#### A. `_is_safe_git_url()` メソッド（L293-308）
**変更前**:
```python
def _is_safe_git_url(self, url: str) -> bool:
    if not url.startswith(('https://github.com/', 'git@github.com:')):
        return False
```

**変更後**:
```python
def _is_safe_git_url(self, url: str) -> bool:
    allowed_domains = self._get_allowed_domains()
    
    # Check HTTPS URLs
    if url.startswith('https://'):
        parsed = urlparse(url)
        if parsed.netloc not in allowed_domains:
            return False
    # Check SSH URLs
    elif url.startswith('git@'):
        domain = url.split('@')[1].split(':')[0]
        if domain not in allowed_domains:
            return False
    else:
        return False
    
    # Security checks remain the same
    dangerous_chars = [';', '&', '|', ...]
    if any(char in url for char in dangerous_chars):
        return False
    return True
```

#### B. `_resolve_from_git()` メソッド（L397）
**変更前**:
```python
if 'github.com' not in parsed_url.netloc:
    logger.error(f"Not a GitHub URL: {git_url}")
    return None
```

**変更後**:
```python
allowed_domains = self._get_allowed_domains()
if parsed_url.netloc not in allowed_domains:
    logger.error(f"Domain not in allowed list: {git_url} (allowed: {allowed_domains})")
    return None
```

#### C. `validate_git_script_info()` メソッド（L482）
**変更前**:
```python
if parsed_url.netloc != 'github.com':
    return False, f"Not a valid GitHub URL: {git_url}"
```

**変更後**:
```python
allowed_domains = self._get_allowed_domains()
if parsed_url.netloc not in allowed_domains:
    return False, f"Domain not in allowed list: {git_url} (allowed: {allowed_domains})"
```

#### D. 新規ヘルパーメソッド
```python
def _get_allowed_domains(self) -> Set[str]:
    """Get list of allowed Git domains from config"""
    try:
        from src.config_manager import ConfigManager
        config = ConfigManager()
        
        # Get from config (with env var override)
        domains_str = config.get('git_script.allowed_domains', 'github.com')
        domains = {d.strip() for d in domains_str.split(',') if d.strip()}
        
        # Always include github.com for backwards compatibility
        domains.add('github.com')
        
        return domains
    except Exception as e:
        logger.warning(f"Failed to load allowed domains, using default: {e}")
        return {'github.com'}
```

### 4. 設定ファイル更新

**`config/base/core.yaml` に追加**:
```yaml
git_script:
  # Allowed domains for git-script URL validation
  # Can be overridden by GIT_SCRIPT_ALLOWED_DOMAINS env var
  allowed_domains: "github.com"
  
  # Whether to allow custom domains via UI
  # Can be disabled for security-critical environments
  allow_custom_domains_ui: true
```

**`config/feature_flags.yaml` に追加**:
```yaml
flags:
  # ... existing flags ...
  
  git_script_custom_domains:
    description: "git-script カスタムドメイン許可機能を有効化 (#255)"
    default: true
    type: boolean
```

### 5. 実装方針

- [x] **段階1**: 設定ファイル・環境変数による静的ドメイン許可リスト実装
  - `config/base/core.yaml`に設定追加
  - `git_script_resolver.py`リファクタリング（3箇所）
  - `_get_allowed_domains()`ヘルパーメソッド追加
  - 単体テスト追加
  
- [ ] **段階2**: UIからの動的ドメイン追加機能
  - Gradio UI「🔧 Settings」タブに新セクション追加
  - ドメイン追加・削除・リセット機能
  - セッション永続化（JSON設定ファイル）
  
- [ ] **段階3**: 検証・ドキュメント整備
  - E2Eテスト追加（複数ドメインでのgit-script実行）
  - README更新（環境変数設定例）
  - セキュリティガイド更新

## Acceptance Criteria（受け入れ基準）

### 必須
- [x] 環境変数`GIT_SCRIPT_ALLOWED_DOMAINS`で複数ドメインを指定可能
- [x] github.com以外のドメイン（例: gitlab.example.com）からgit-scriptが実行可能
- [x] github.comはデフォルトで常に許可される（後方互換性）
- [x] 許可されていないドメインからのgit-scriptは明確なエラーメッセージで拒否
- [x] 既存のgit-script機能に回帰がない（github.comの動作は変わらない）

### オプション（段階2）
- [ ] UI「🔧 Settings」からドメイン追加・削除が可能
- [ ] 現在の許可ドメイン一覧がUI上で確認可能
- [ ] 設定変更がセッション間で永続化される

### 品質
- [x] `git_script_resolver.py`の単体テストが追加され、全てパス
- [ ] E2Eテストで複数ドメインケースを検証
- [x] カバレッジが低下しない（現在59%以上を維持）
- [x] ドキュメント（README.md、セキュリティガイド）更新

## 参照（本 Issue 作成にあたって参照したガイドライン）

- [x] AGENT_PROMPT_GUIDE.md: 1 Issue = 1 実装単位、段階的PR推奨
- [x] HOW_TO_PROMPT_TO_AGENT.md: 依存解決ルール確認
- [x] ROADMAP.md: Phase 2に該当（runner拡張）
- [x] CONTRIBUTING.md: PR テンプレ・Docs 更新ルール確認
- [x] labeling-guidelines.md: 適切なラベル付与確認

## 依存関係

### 依存する Issue（このIssueを開始する前に完了が必要）
- なし（独立した機能拡張）

### このIssueに依存する Issue（このIssue完了後に開始可能になる）
- なし（将来的にgit-script関連の拡張で参照される可能性）

## 実装上の注意点 / リスク

### セキュリティ
⚠️ **重要**: ドメイン許可リスト方式により、セキュリティリスクを最小化

1. **URL検証強化**
   - ドメイン許可リストチェック（必須）
   - 既存のセキュリティチェック維持（危険文字、長さ制限）
   - SSH URLも同様に検証

2. **デフォルト動作**
   - github.comのみ許可（現状維持）
   - 明示的な設定がない限り他ドメインは拒否

3. **エンタープライズ環境**
   - Feature Flagで`allow_custom_domains_ui`を無効化可能
   - 環境変数のみで制御する運用も可能（UIを無効化）

### パフォーマンス
- 設定読み込みのオーバーヘッドは最小（起動時1回 + キャッシュ）
- ドメインチェックはO(1)操作（Setでの検索）

### 互換性
✅ **完全な後方互換性**
- デフォルト動作は変更なし（github.comのみ）
- 既存の環境変数・設定ファイルに影響なし
- 新機能はオプトイン方式

### リスク

1. **設定ミスによる誤った許可**
   - **対策**: UIで設定時に警告メッセージ表示
   - **対策**: ドメイン形式の基本バリデーション（正規表現）

2. **内部ネットワークへの意図しないアクセス**
   - **対策**: プライベートIPアドレス範囲を別途ブロック可能にする（将来拡張）
   - **対策**: ドキュメントでセキュリティベストプラクティスを明記

3. **認証情報の漏洩リスク**
   - **対策**: 既存のGit認証マネージャー（`GitAuthManager`）を活用
   - **対策**: SSHキー、トークンは環境変数またはGit credentialから取得

## ラベリング（推奨）

- `type:enhancement` ✅（既に付与済み）
- `area:runner` （git-script機能はrunner領域）
- `priority:P2` （利便性向上、エンタープライズ対応）
- `size:M` （3ファイル修正 + テスト + ドキュメント）
- `phase:2` （Phase 2: 機能拡張フェーズ）

## 実装計画サマリー

### 変更ファイル一覧
1. `config/base/core.yaml` - 設定追加
2. `config/feature_flags.yaml` - Feature Flag追加
3. `src/script/git_script_resolver.py` - ロジック修正（3箇所 + ヘルパー）
4. `tests/unit/test_git_script_resolver.py` - 単体テスト追加
5. `README.md` - 環境変数設定例追加
6. `docs/SECURITY.md` - セキュリティガイド更新

### テストケース
- [ ] github.comからのgit-script実行（既存、回帰テスト）
- [ ] カスタムドメイン（gitlab.example.com）からの実行成功
- [ ] 許可されていないドメインからの実行拒否
- [ ] 複数ドメインの同時許可
- [ ] 環境変数による設定上書き
- [ ] デフォルト設定（github.comのみ）の動作確認

## その他

### 参考実装例
他のOSSプロジェクトでも同様のアプローチ採用:
- GitHub Actions: `GITHUB_SERVER_URL`環境変数でGHESをサポート
- GitLab CI: `CI_SERVER_HOST`でドメイン指定
- Jenkins Git Plugin: 複数Gitホストの許可リスト機能

### 将来の拡張可能性
- [ ] ドメインごとの認証設定（Issue #256候補）
- [ ] SSHポート番号のカスタマイズ（Issue #257候補）
- [ ] ドメインホワイトリスト・ブラックリスト併用（Issue #258候補）
