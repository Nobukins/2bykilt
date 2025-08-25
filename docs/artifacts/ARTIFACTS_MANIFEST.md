# Artifacts Manifest v2

最終更新: 2025-01-27

## 概要

2bykilt プロジェクトで生成される全ての Artifacts（成果物）の管理とマニフェスト定義です。動画・スクリーンショット・要素値・ログファイルなどの統一管理を実現します。

## Artifacts 分類

### 1. Recording Artifacts（録画成果物）
ブラウザ操作の記録データ
```yaml
recording_artifacts:
  video:
    format: webm
    quality: high
    fps: 30
    compression: vp9
    audio: optional
    
  screenshots:
    format: png
    quality: high
    compression: lossless
    timestamp: required
    
  traces:
    format: json
    include_network: true
    include_console: true
    include_timeline: true
```

### 2. Data Artifacts（データ成果物）
実行中に収集されるデータ
```yaml
data_artifacts:
  element_values:
    format: json
    schema_version: "2.1"
    encryption: optional
    
  form_data:
    format: json
    sanitized: true
    pii_removed: true
    
  api_responses:
    format: json
    headers_included: true
    body_truncated: false
```

### 3. Log Artifacts（ログ成果物）
実行ログとメタデータ
```yaml
log_artifacts:
  execution_logs:
    format: jsonl
    structured: true
    levels: [DEBUG, INFO, WARNING, ERROR]
    
  error_logs:
    format: jsonl
    stack_traces: true
    context_included: true
    
  audit_logs:
    format: jsonl
    immutable: true
    signed: optional
```

### 4. Report Artifacts（レポート成果物）
分析・レポート用データ
```yaml
report_artifacts:
  summary_reports:
    format: json
    schema_version: "1.0"
    charts_included: false
    
  metrics_reports:
    format: json
    time_series: true
    aggregations: included
    
  test_reports:
    format: junit_xml
    coverage_included: true
    screenshots_attached: true
```

## Manifest スキーマ

### 1. 基本構造
```json
{
  "manifest_version": "2.0",
  "created_at": "2025-01-27T12:34:56.789Z",
  "session_id": "sess_20250127_123456",
  "execution_id": "exec_abc123def456",
  "artifacts": {
    "recording": [],
    "data": [],
    "logs": [],
    "reports": []
  },
  "metadata": {
    "environment": "production",
    "user_agent": "Mozilla/5.0...",
    "screen_resolution": "1920x1080",
    "browser_version": "Chrome/121.0.0.0"
  },
  "checksums": {},
  "retention_policy": {
    "default_ttl_days": 30,
    "critical_ttl_days": 90
  }
}
```

### 2. Artifact エントリ構造
```json
{
  "id": "artifact_001",
  "type": "recording/video",
  "path": "recordings/2025/01/27/session_abc123/video.webm",
  "size_bytes": 15728640,
  "created_at": "2025-01-27T12:35:30.123Z",
  "duration_ms": 45000,
  "checksum": {
    "md5": "5d41402abc4b2a76b9719d911017c592",
    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "metadata": {
    "resolution": "1920x1080",
    "format": "webm",
    "codec": "vp9",
    "fps": 30
  },
  "access_control": {
    "visibility": "private",
    "encryption": true,
    "retention_days": 30
  },
  "tags": ["automation", "ui_test", "batch_processing"],
  "related_artifacts": ["artifact_002", "artifact_003"]
}
```

## 実装パターン

### 1. Artifact Manager
```python
import json
import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

class ArtifactManager:
    """Artifact 管理"""
    
    def __init__(self, base_path: str = "artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.base_path / "manifest.json"
        self.manifest = self._load_manifest()
        
    def register_artifact(
        self,
        artifact_type: str,
        file_path: str,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None,
        retention_days: int = None
    ) -> str:
        """Artifact 登録"""
        
        artifact_id = self._generate_artifact_id()
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Artifact file not found: {file_path}")
        
        # ファイル情報収集
        stat = file_path.stat()
        checksums = self._calculate_checksums(file_path)
        
        artifact_entry = {
            "id": artifact_id,
            "type": artifact_type,
            "path": str(file_path.relative_to(self.base_path)),
            "size_bytes": stat.st_size,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "checksum": checksums,
            "metadata": metadata or {},
            "access_control": {
                "visibility": "private",
                "encryption": False,
                "retention_days": retention_days or 30
            },
            "tags": tags or [],
            "related_artifacts": []
        }
        
        # MIME type 推定
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type:
            artifact_entry["metadata"]["mime_type"] = mime_type
        
        # Manifest 更新
        category = self._get_artifact_category(artifact_type)
        if category not in self.manifest["artifacts"]:
            self.manifest["artifacts"][category] = []
        
        self.manifest["artifacts"][category].append(artifact_entry)
        self._save_manifest()
        
        return artifact_id
    
    def get_artifact(self, artifact_id: str) -> Optional[Dict[str, Any]]:
        """Artifact 取得"""
        for category in self.manifest["artifacts"].values():
            for artifact in category:
                if artifact["id"] == artifact_id:
                    return artifact
        return None
    
    def list_artifacts(
        self,
        artifact_type: str = None,
        tags: List[str] = None,
        created_after: datetime = None
    ) -> List[Dict[str, Any]]:
        """Artifact 一覧取得"""
        results = []
        
        for category in self.manifest["artifacts"].values():
            for artifact in category:
                # フィルタリング
                if artifact_type and not artifact["type"].startswith(artifact_type):
                    continue
                    
                if tags and not any(tag in artifact["tags"] for tag in tags):
                    continue
                    
                if created_after:
                    created = datetime.fromisoformat(artifact["created_at"].rstrip("Z"))
                    if created < created_after:
                        continue
                
                results.append(artifact)
        
        return results
    
    def cleanup_expired_artifacts(self) -> List[str]:
        """期限切れ Artifact クリーンアップ"""
        expired_ids = []
        now = datetime.utcnow()
        
        for category_name, category in self.manifest["artifacts"].items():
            remaining_artifacts = []
            
            for artifact in category:
                created = datetime.fromisoformat(artifact["created_at"].rstrip("Z"))
                retention_days = artifact["access_control"]["retention_days"]
                expiry_date = created + timedelta(days=retention_days)
                
                if now > expiry_date:
                    # ファイル削除
                    file_path = self.base_path / artifact["path"]
                    try:
                        if file_path.exists():
                            file_path.unlink()
                        expired_ids.append(artifact["id"])
                    except Exception as e:
                        logger.error(f"Failed to delete artifact {artifact['id']}: {e}")
                        remaining_artifacts.append(artifact)
                else:
                    remaining_artifacts.append(artifact)
            
            self.manifest["artifacts"][category_name] = remaining_artifacts
        
        if expired_ids:
            self._save_manifest()
        
        return expired_ids
    
    def _calculate_checksums(self, file_path: Path) -> Dict[str, str]:
        """チェックサム計算"""
        checksums = {}
        
        with open(file_path, 'rb') as f:
            content = f.read()
            
        checksums["md5"] = hashlib.md5(content).hexdigest()
        checksums["sha256"] = hashlib.sha256(content).hexdigest()
        
        return checksums
    
    def _generate_artifact_id(self) -> str:
        """Artifact ID 生成"""
        import uuid
        return f"artifact_{uuid.uuid4().hex[:12]}"
    
    def _get_artifact_category(self, artifact_type: str) -> str:
        """Artifact カテゴリ判定"""
        if artifact_type.startswith("recording/"):
            return "recording"
        elif artifact_type.startswith("data/"):
            return "data" 
        elif artifact_type.startswith("log/"):
            return "logs"
        elif artifact_type.startswith("report/"):
            return "reports"
        else:
            return "other"
```

### 2. Recording Artifact Handler
```python
class RecordingArtifactHandler:
    """録画 Artifact ハンドラー"""
    
    def __init__(self, artifact_manager: ArtifactManager):
        self.artifact_manager = artifact_manager
        
    def save_video_recording(
        self,
        video_path: str,
        duration_ms: int,
        resolution: str = "1920x1080",
        fps: int = 30
    ) -> str:
        """動画録画保存"""
        metadata = {
            "duration_ms": duration_ms,
            "resolution": resolution,
            "fps": fps,
            "format": "webm",
            "codec": "vp9"
        }
        
        return self.artifact_manager.register_artifact(
            artifact_type="recording/video",
            file_path=video_path,
            metadata=metadata,
            tags=["recording", "video"],
            retention_days=30
        )
    
    def save_screenshot(
        self,
        screenshot_path: str,
        page_url: str,
        viewport_size: str = "1920x1080"
    ) -> str:
        """スクリーンショット保存"""
        metadata = {
            "page_url": page_url,
            "viewport_size": viewport_size,
            "format": "png",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        return self.artifact_manager.register_artifact(
            artifact_type="recording/screenshot",
            file_path=screenshot_path,
            metadata=metadata,
            tags=["recording", "screenshot"],
            retention_days=7
        )
    
    def save_trace_data(
        self,
        trace_path: str,
        include_network: bool = True,
        include_console: bool = True
    ) -> str:
        """トレースデータ保存"""
        metadata = {
            "format": "json",
            "include_network": include_network,
            "include_console": include_console,
            "browser": "chromium"
        }
        
        return self.artifact_manager.register_artifact(
            artifact_type="recording/trace",
            file_path=trace_path,
            metadata=metadata,
            tags=["recording", "trace", "debug"],
            retention_days=14
        )
```

### 3. Data Artifact Handler
```python
class DataArtifactHandler:
    """データ Artifact ハンドラー"""
    
    def __init__(self, artifact_manager: ArtifactManager):
        self.artifact_manager = artifact_manager
        
    def save_element_values(
        self,
        data: Dict[str, Any],
        page_url: str,
        selector_map: Dict[str, str] = None
    ) -> str:
        """要素値データ保存"""
        
        # データをファイルに保存
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = self.artifact_manager.base_path / f"element_values_{timestamp}.json"
        
        element_data = {
            "schema_version": "2.1",
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "page_url": page_url,
            "selector_map": selector_map or {},
            "values": self._sanitize_element_data(data)
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(element_data, f, indent=2, ensure_ascii=False)
        
        metadata = {
            "page_url": page_url,
            "element_count": len(data),
            "schema_version": "2.1",
            "sanitized": True
        }
        
        return self.artifact_manager.register_artifact(
            artifact_type="data/element_values",
            file_path=str(file_path),
            metadata=metadata,
            tags=["data", "elements", "automation"],
            retention_days=14
        )
    
    def save_form_data(
        self,
        form_data: Dict[str, Any],
        form_id: str,
        page_url: str
    ) -> str:
        """フォームデータ保存"""
        
        # PII データ除去
        sanitized_data = self._remove_pii_data(form_data)
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_path = self.artifact_manager.base_path / f"form_data_{timestamp}.json"
        
        form_artifact = {
            "schema_version": "1.0",
            "captured_at": datetime.utcnow().isoformat() + "Z",
            "form_id": form_id,
            "page_url": page_url,
            "data": sanitized_data,
            "pii_removed": True
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(form_artifact, f, indent=2, ensure_ascii=False)
        
        metadata = {
            "form_id": form_id,
            "page_url": page_url,
            "field_count": len(form_data),
            "pii_removed": True
        }
        
        return self.artifact_manager.register_artifact(
            artifact_type="data/form_data",
            file_path=str(file_path),
            metadata=metadata,
            tags=["data", "form", "user_input"],
            retention_days=7
        )
    
    def _sanitize_element_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """要素データサニタイズ"""
        sanitized = {}
        sensitive_patterns = ['password', 'secret', 'token', 'key']
        
        for key, value in data.items():
            if any(pattern in key.lower() for pattern in sensitive_patterns):
                sanitized[key] = "***SANITIZED***"
            elif isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "...TRUNCATED"
            else:
                sanitized[key] = value
                
        return sanitized
    
    def _remove_pii_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """PII データ除去"""
        pii_fields = [
            'ssn', 'social_security', 'passport', 'license',
            'birth_date', 'phone', 'address', 'email'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if any(pii in key.lower() for pii in pii_fields):
                sanitized[key] = "***PII_REMOVED***"
            else:
                sanitized[key] = value
                
        return sanitized
```

## 統合例

### 1. Session Artifact Collector
```python
class SessionArtifactCollector:
    """セッション Artifact 収集"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.artifact_manager = ArtifactManager()
        self.recording_handler = RecordingArtifactHandler(self.artifact_manager)
        self.data_handler = DataArtifactHandler(self.artifact_manager)
        self.collected_artifacts = []
        
    def start_session(self):
        """セッション開始"""
        self.artifact_manager.manifest["session_id"] = self.session_id
        self.artifact_manager.manifest["created_at"] = datetime.utcnow().isoformat() + "Z"
        
    def collect_page_artifacts(
        self,
        page_url: str,
        screenshot_path: str = None,
        element_values: Dict[str, Any] = None
    ):
        """ページ Artifact 収集"""
        artifacts = []
        
        # スクリーンショット
        if screenshot_path:
            artifact_id = self.recording_handler.save_screenshot(
                screenshot_path, page_url
            )
            artifacts.append(artifact_id)
            
        # 要素値
        if element_values:
            artifact_id = self.data_handler.save_element_values(
                element_values, page_url
            )
            artifacts.append(artifact_id)
            
        self.collected_artifacts.extend(artifacts)
        return artifacts
        
    def finalize_session(self) -> Dict[str, Any]:
        """セッション終了"""
        summary = {
            "session_id": self.session_id,
            "total_artifacts": len(self.collected_artifacts),
            "artifacts_by_type": self._get_artifact_type_summary(),
            "total_size_bytes": self._calculate_total_size(),
            "session_duration": self._calculate_session_duration()
        }
        
        # サマリーレポート保存
        self._save_session_summary(summary)
        
        return summary
    
    def _get_artifact_type_summary(self) -> Dict[str, int]:
        """Artifact 種別サマリー"""
        type_counts = {}
        for artifact_id in self.collected_artifacts:
            artifact = self.artifact_manager.get_artifact(artifact_id)
            if artifact:
                artifact_type = artifact["type"]
                type_counts[artifact_type] = type_counts.get(artifact_type, 0) + 1
        return type_counts
```

### 2. Artifact Export
```python
class ArtifactExporter:
    """Artifact エクスポート"""
    
    def __init__(self, artifact_manager: ArtifactManager):
        self.artifact_manager = artifact_manager
        
    def export_session_archive(
        self,
        session_id: str,
        output_path: str,
        include_videos: bool = True,
        include_data: bool = True
    ) -> str:
        """セッション Artifact アーカイブ作成"""
        import zipfile
        
        artifacts = self.artifact_manager.list_artifacts(
            tags=["session:" + session_id]
        )
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            
            # Manifest 追加
            manifest_data = {
                "session_id": session_id,
                "exported_at": datetime.utcnow().isoformat() + "Z",
                "artifacts": artifacts
            }
            zipf.writestr("manifest.json", json.dumps(manifest_data, indent=2))
            
            # Artifact ファイル追加
            for artifact in artifacts:
                artifact_type = artifact["type"]
                
                # フィルタリング
                if not include_videos and artifact_type.startswith("recording/video"):
                    continue
                if not include_data and artifact_type.startswith("data/"):
                    continue
                    
                file_path = self.artifact_manager.base_path / artifact["path"]
                if file_path.exists():
                    zipf.write(file_path, artifact["path"])
                    
        return output_path
    
    def generate_artifact_report(self, output_format: str = "json") -> str:
        """Artifact レポート生成"""
        
        all_artifacts = []
        for category in self.artifact_manager.manifest["artifacts"].values():
            all_artifacts.extend(category)
            
        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_artifacts": len(all_artifacts),
            "total_size_bytes": sum(a["size_bytes"] for a in all_artifacts),
            "artifacts_by_type": {},
            "retention_summary": {},
            "oldest_artifact": None,
            "newest_artifact": None
        }
        
        # 統計計算
        for artifact in all_artifacts:
            # 種別別集計
            artifact_type = artifact["type"]
            if artifact_type not in report["artifacts_by_type"]:
                report["artifacts_by_type"][artifact_type] = {
                    "count": 0,
                    "total_size": 0
                }
            report["artifacts_by_type"][artifact_type]["count"] += 1
            report["artifacts_by_type"][artifact_type]["total_size"] += artifact["size_bytes"]
            
            # 日付統計
            created_at = artifact["created_at"]
            if not report["oldest_artifact"] or created_at < report["oldest_artifact"]:
                report["oldest_artifact"] = created_at
            if not report["newest_artifact"] or created_at > report["newest_artifact"]:
                report["newest_artifact"] = created_at
        
        if output_format == "json":
            return json.dumps(report, indent=2)
        else:
            # 他の形式サポート予定
            return json.dumps(report, indent=2)
```

## 運用ガイドライン

### 1. 保存ポリシー
- 録画データ: 30日間保持
- スクリーンショット: 7日間保持
- 要素値データ: 14日間保持
- エラーログ: 90日間保持

### 2. セキュリティ配慮
- PII データの自動除去
- 機密情報のマスキング
- アクセス制御の実装
- 暗号化オプション

### 3. パフォーマンス最適化
- 大容量ファイルの圧縮
- 古いファイルの自動削除
- インデックス作成
- 並列処理対応

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 2.0.0 | 2025-01-27 | 初期ドラフト作成 | Copilot Agent |

---

統一された Artifact 管理により、効率的なデータ活用と運用を実現してください。