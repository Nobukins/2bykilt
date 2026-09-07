# 継続的セキュリティ実装手順書 (Continuous Security Implementation)

本ドキュメントは、本リポジトリ(アプリケーション)に対してエンタープライズ利用を想定した最低限の継続的セキュリティ(Continuous Security)基盤を OSS / 無料プランを中心に構築し、Pull Request 毎に自動で静的コード解析と依存関係/コンテナ脆弱性監査を実施しレポート/ゲート化するための計画・設計・実装・運用手順をまとめたものです。

## 目的

1. 静的コード解析 (SAST) の自動化と品質/セキュリティゲートの可視化
2. 依存パッケージおよびコンテナイメージの脆弱性検出 (SCA / Container Scan)
3. 脆弱性/品質課題のライフサイクル管理 (検出 → トリアージ → 対応 → 再チェック)
4. 将来の有料プラン / 外部統合 (例: SonarQube 商用版, Snyk, Wiz など) へ容易に拡張できる構成

## 選定方針 (OSS / Free Tier 優先)

| カテゴリ | 採用(初期) | 役割 | 代替 / 将来拡張例 |
|----------|-----------|------|--------------------|
| 静的コード解析(Python品質/バグ/セキュリティ) | SonarCloud Free (Public) / Self-host SonarQube Community | コードスメル・バグ・脆弱性・セキュリティホットスポット検出 | SonarQube Dev/Enterprise (Branch分析, SSO, セキュリティレポ拡張) |
| 依存関係脆弱性(SCA) | GitHub Dependabot + pip-audit | requirements.txt / transitive 依存の CVE 検出 | OSS Review Toolkit, OSV-Scanner, Snyk, JFrog Xray |
| コンテナ脆弱性 | Trivy (GitHub Action) | Dockerfile / イメージの脆弱性 & Misconfig | Grype, Anchore Enterprise, Snyk Container |
| シークレット検出 | Gitleaks (Action) | API Key / 秘密情報の誤コミット検出 | GitHub Secret Scanning (Publicは自動), TruffleHog |
| ライセンス監査 | Trivy (License), pip-licenses | OSSライセンス収集 | FOSSA, ClearlyDefined |
| SBOM 生成 | Syft or Trivy | SPDX / CycloneDX 出力 | Anchore Enterprise, DependencyTrack 連携 |
| レポート可視化 | GitHub PR コメント / Checks / Badges | 開発者ワークフロー統合 | Security Dashboard 外部(SonarQube Server, DefectDojo) |

## 全体アーキテクチャ (CI パイプライン概要)

Pull Request / main への push トリガで以下のジョブを並列/段階実行:

1. Setup (Python, cache)
2. Lint & Unit Test (pytest, coverage) ※品質ベースライン
3. SAST: SonarCloud / SonarQube Scanner
4. SCA: pip-audit + Dependabot (Dependabot はスケジュール)
5. Secret Scan: Gitleaks
6. Container Build & Scan: Trivy (vuln + config + SBOM)
7. SBOM 生成 (CycloneDX) & アーティファクト保管
8. 集約レポート: GitHub PR コメント (summary markdown) + 失敗ゲート (重大度閾値)

## 品質・セキュリティゲート基準(初期値の例)

- Unit Test 成功 & Coverage >= 60%
- Sonar (Quality Gate): Bugs = 0 (Blocker/Critical), Vulnerabilities = 0 (High以上), Security Hotspots Reviewed >= 50%
- pip-audit: High / Critical CVE 0 (存在時は Fail)
- Trivy (Image): HIGH/Critical 0 (許容期間: 7日迄に修正, 例外は CODEOWNERS 承認)
- Secret Scan: 発見 0

## シークレット / 外部サービス準備

1. SonarCloud を使用する場合: <https://sonarcloud.io> に GitHub アカウントでログイン → Organization 作成 → プロジェクト Import → Token 発行 ( `SONAR_TOKEN` )
2. Self-host SonarQube の場合: Docker 立ち上げ (参考: <https://docs.sonarsource.com/sonarqube/>) → Project Key & Token 取得
3. GitHub リポジトリ Settings → Secrets and variables → Actions:
   - SONAR_TOKEN
   - (必要に応じ) SONAR_HOST_URL (Self-host 時)
4. Gitleaks / Trivy は追加シークレット不要 (Private Registry 利用時は REGISTRY_USER/PASSWORD 等)

## 実装手順

### 1. ディレクトリ/ファイル追加

- .github/workflows/security-ci.yml (メイン CI)
- .github/workflows/dependabot.yml (Dependabot 設定 *既定テンプレが無ければ*)
- .gitleaks.toml (ルール調整)
- sonar-project.properties (Sonar 設定: self-host or sonarcloud)

### 2. ワークフロー定義例 (概要)

(後述の実際の YAML を参照)
Jobs:

- prepare: Python セットアップ, cache, install
- test: pytest + coverage.xml 生成 (upload artifact)
- sonar: needs: test → Sonar Scanner 実行 (レポート品質ゲート)
- sca: pip-audit 実行
- secret: gitleaks 実行
- container-scan: Docker build → Trivy vuln/config/lic → SBOM 生成
- summarize: すべてのジョブ結果を収集し PR コメント

### 3. Sonar 設定

sonar-project.properties の最小例:

```
sonar.projectKey=your_org_2bykilt
sonar.organization=your_org
sonar.projectName=2bykilt
sonar.sources=.
sonar.language=py
sonar.python.version=3.11
sonar.tests=tests
sonar.python.coverage.reportPaths=coverage.xml
sonar.sourceEncoding=UTF-8
```

SonarCloud 利用時は organization を合わせる。Secret に SONAR_TOKEN を登録。

### 4. GitHub Actions YAML (詳細案)

後続ステップで `security-ci.yml` を追加実装。（本計画後に実際のファイルを生成）

### 5. Dependabot 設定例

dependabot.yml 例:

```
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "daily"
    open-pull-requests-limit: 5
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### 6. 脆弱性スキャン (pip-audit)

`pip-audit -r requirements.txt --format json` を実行し High/Critical 存在で失敗。

### 7. コンテナスキャン / SBOM

Trivy:

- `trivy image --scanners vuln,config,secret,license --format table --exit-code 1 --severity HIGH,CRITICAL <image>`
- SBOM: `trivy image --format cyclonedx --output sbom.cdx.json <image>`

### 8. PR サマリ自動コメント

Actions の `peter-evans/create-or-update-comment` などで markdown 集約。
含める項目:

- Coverage
- Sonar Quality Gate 状態 (リンク)
- pip-audit 結果要約
- Trivy 高重大度件数
- Secret Scan 結果

### 9. 運用フロー

1. 毎 PR: レポート確認 → 失敗時修正 or 例外申請 (ISSUE テンプレ)
2. 毎週: Dependabot PR レビュー & マージ
3. 毎月: Quality Gate 基準見直し (Coverage 閾値 +5% など)
4. 四半期: ツール選定再評価 / 拡張 (SAST 追加ルール, IaC Scan 等)

### 10. 拡張候補と評価

| 項目 | 拡張案 | 期待効果 | 代替しない場合との差異 |
|------|--------|----------|-------------------------|
| IaC スキャン | Checkov / tfsec | Terraform/K8s 設定ミス検出 | インフラ層リスク未検出 |
| ランタイム保護 | Falco | 実行時侵害検知 | ビルド時のみの静的保証 |
| DAST | OWASP ZAP (Action) | 動的アプリ脆弱性 (XSS 等) | コード上で気付けない脆弱性残存 |
| LLM Prompt Security | semgrep + カスタムルール | LLM 呼び出し部の入力検証 | 生成AI特有リスク未可視化 |
| SBOM 管理 | DependencyTrack | 継続的モニタリング | CVE 公開後追従遅延 |

優先度付け: まず IaC (存在する場合) → DAST → SBOM継続監視。

### 11. 改善サイクル (効率性向上判定基準)

- False Positive 削減率 (ルール調整前後での無視件数)
- 修正リードタイム (検出→修正まで日数)
- Coverage 推移 (月次)
- Quality Gate Fail 再発率 (<15% 維持)

### 12. セキュリティデータ公開の留意点

- Public Repo で SonarCloud 利用時: コードメタデータが SonarCloud 公開領域に載る (プライバシ/機密コードなしを確認)
- SBOM はサプライチェーンリスク可視化だが、内部パッケージ名が露出するため公開配布は判断フロー必須
- Secret 検出ルール緩和は安易に行わない (偽陰性増加)

### 13. 手順チェックリスト (初期導入)

- [ ] SonarCloud プロジェクト作成 & SONAR_TOKEN 登録
- [ ] workflows/security-ci.yml 追加
- [ ] dependabot.yml 追加
- [ ] gitleaks 設定追加
- [ ] Trivy Action 実行確認
- [ ] PR で品質ゲートコメント表示
- [ ] 重大度閾値でビルド失敗動作確認

### 14. ローカル検証 Tips

```
pip install pip-audit
pip-audit -r requirements.txt
brew install trivy
trivy fs .
pytest --cov=src --cov-report=xml
sonar-scanner -Dsonar.token=$SONAR_TOKEN
```

### 15. 今後の高度化 (例)

- SARIF 連携 (Code Scanning alerts) で pip-audit/Trivy/Gitleaks 出力を GitHub Security タブ集中管理
- OpenSSF Scorecard GitHub Action 追加
- Semgrep 導入 (フレームワーク固有セキュリティルール)
- Pre-commit Hook で軽量 secret / lint チェック

---

本計画に基づき、次ステップとして GitHub Actions ワークフローと関連設定ファイルをリポジトリに追加してください。追加後、本書の「13. チェックリスト」に沿って動作検証を行ってください。

---

## 16. 2026-07 モダナイズ (実装済み)

「15. 今後の高度化」の項目を含む全面見直しを 2026-07 に実施。現行アーキテクチャは以下の通り。

### 現行コンポーネント一覧

| レイヤ | ツール | ワークフロー | 実行タイミング | ゲート |
|--------|--------|--------------|----------------|--------|
| SAST (品質+セキュリティ) | SonarCloud (`sonarqube-scan-action@v6`) | security-ci.yml | PR / push | Quality Gate (advisory) |
| SAST (セキュリティ特化) | CodeQL `python` + `actions` (security-extended) | codeql.yml | PR / push / 週次 | Code Scanning アラート |
| SCA (フル依存解決) | pip-audit + 正規化 + ポリシー閾値 | security-ci.yml | PR / push | `security/security_policy.yaml` (critical/high = 0) |
| SCA (PR 差分) | `dependency-review-action` | security-ci.yml | PR | HIGH 以上でブロック |
| SCA (自動更新) | Dependabot (pip + github-actions, 週次グループ化) | .github/dependabot.yml | 週次 + 随時 (security update) | — |
| Deep Scan | Trivy fs (vuln + misconfig) → SARIF | supply-chain.yml | push / 週次 | report-only |
| SBOM | Syft (SPDX + CycloneDX) + GitHub dependency snapshot | supply-chain.yml | push / release / 週次 | — (リリース時アセット添付) |
| Secret | gitleaks | security-ci.yml | PR / push | 検出 0 必須 |
| Workflow 監査 | zizmor → SARIF | security-ci.yml | PR / push | report-only (段階的に強化) |
| サプライチェーン姿勢 | OpenSSF Scorecard → SARIF + 公開バッジ | scorecard.yml | push / 週次 | report-only |

### 抑止 (Suppression) 運用の変更

- `security/suppressions.yaml` の `expires_at` を **normalizer が強制** するようになった (期限切れ = 抑止無効化 → 脆弱性が再浮上しゲート判定対象に戻る)。
- 抑止は「期限付きリスク受容」であり恒久免除ではない。期限前に依存アップグレード可否を再評価し、不可の場合のみ理由を更新して延長する。

### 能動的検知の集約先

pip-audit 以外 (CodeQL / Trivy / zizmor / Scorecard) の検出は SARIF として **GitHub Security タブ → Code scanning** に集約される。週次でトリアージし、真陽性は Issue 化して `docs/roadmap/ISSUE_DEPENDENCIES.yml` の管理サイクルに載せること。

### リポジトリ設定側で有効化すべき項目 (ファイルでは管理不可)

- Settings → Code security: **Secret scanning + Push protection** を有効化
- Settings → Code security: **Private vulnerability reporting** を有効化 (`.github/SECURITY.md` が受付先を案内)
- Branch protection: `2bykilt` に対し security-ci の必須チェック (`test` は現状 `continue-on-error: true` のため通過扱いになる点に注意 — 厳格化する場合は当該行を削除)

### 次の高度化候補 (未実装)

- 全 Actions の **commit SHA ピン留め** (Dependabot github-actions 更新と併用。zizmor の `unpinned-uses` 検出を fail 化する前提条件)
- `step-security/harden-runner` による runner egress 監視
- Dockerfile 追加時: supply-chain.yml にイメージビルド + Trivy image scan + `actions/attest-build-provenance` による SLSA provenance / SBOM attestation
- zizmor / Trivy の report-only → ブロッキング昇格 (誤検知トリアージ完了後)
