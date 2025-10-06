# Metrics Guide

最終更新: 2025-08-26

<!-- markdownlint-disable -->

## 概要

2bykilt プロジェクトのメトリクス計測とモニタリング標準を定義します。システム健全性の可視化と効果的な運用を実現します。

## メトリクス設計原則

### 1. 4つの黄金シグナル
- **Latency**: リクエスト処理時間
- **Traffic**: リクエスト量・スループット
- **Errors**: エラー率・失敗率
- **Saturation**: リソース使用率

### 2. ビジネスメトリクス
- 機能利用状況
- ユーザー行動パターン
- 品質指標

### 3. 技術メトリクス
- システムパフォーマンス
- リソース使用量
- 外部依存関係の状態

## メトリクス分類

### 1. Counter（カウンター）
累積値を追跡する指標
```python
from prometheus_client import Counter

# リクエスト総数
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 処理完了数
batch_jobs_completed = Counter(
    'batch_jobs_completed_total',
    'Total completed batch jobs',
    ['status', 'job_type']
)

# エラー発生数
errors_total = Counter(
    'errors_total',
    'Total errors',
    ['component', 'error_type', 'severity']
)
```

### 2. Gauge（ゲージ）
瞬間値を追跡する指標
```python
from prometheus_client import Gauge

# 現在のアクティブユーザー数
active_users = Gauge(
    'active_users',
    'Current number of active users'
)

# メモリ使用量
memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Memory usage in bytes',
    ['component']
)

# キュー内待機ジョブ数
queue_pending_jobs = Gauge(
    'queue_pending_jobs',
    'Number of pending jobs in queue',
    ['queue_name']
)
```

### ブラウザエンジン テレメトリー（2025-10-06追加）

CDP / Playwright エンジンのロールアウト状況を観測するため、Runner 側に標準メトリクスを追加しました。`METRICS_ENABLED=true` かつ `initialize_metrics()` が呼ばれている環境では自動で収集されます。

| メトリクス名 | 種別 | ラベル | 説明 |
|--------------|------|--------|------|
| `browser_engine.launch.total` | Counter | `engine`, `browser_type`, `headless`, `trace_enabled`, `sandbox_mode` | エンジン起動成功回数 |
| `browser_engine.launch.failure_total` | Counter | `engine`, `error_kind` | エンジン起動失敗回数 |
| `browser_engine.action.duration_ms` | Histogram | `engine`, `action`, `success` | アクション完了までの所要時間 (ms) |
| `browser_engine.action.success_total` | Counter | `engine`, `action` | アクション成功回数 |
| `browser_engine.action.failure_total` | Counter | `engine`, `action`, `error_kind` | アクション失敗回数 |
| `browser_engine.action.artifact_count` | Gauge | `engine`, `action` | 生成アーティファクト数 (スクリーンショット/トレース等) |
| `browser_engine.session.total_actions` | Gauge | `engine` | セッション内で実行した総アクション数 |
| `browser_engine.session.failed_actions` | Gauge | `engine` | セッション内で失敗したアクション数 |
| `browser_engine.session.avg_latency_ms` | Gauge | `engine` | セッション平均レイテンシ (ms) |
| `browser_engine.session.duration_ms` | Gauge | `engine` | セッション稼働時間 (ms) |
| `browser_engine.session.artifacts_captured` | Gauge | `engine` | セッション中に生成したアーティファクト数 |

#### 活用ヒント

- `engine=playwright|cdp` のラベルでフラグ切替の効果を比較できます。
- `error_kind` は例外クラス名やタイムアウト等を正規化した値です。失敗傾向の把握に利用してください。
- セッション系メトリクスは `shutdown` 時にのみ確定します。異常終了時でも値が残るよう、クリーンアップ処理は `finally` ブロックで送出しています。

### 3. Histogram（ヒストグラム）
分布を追跡する指標
```python
from prometheus_client import Histogram

# リクエスト処理時間
request_duration = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

# バッチ処理時間
batch_processing_duration = Histogram(
    'batch_processing_duration_seconds',
    'Batch processing duration in seconds',
    ['job_type', 'size_category'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0, 1800.0)
)

# ファイルサイズ
file_size_bytes = Histogram(
    'file_size_bytes',
    'File size in bytes',
    ['file_type'],
    buckets=(1024, 10240, 102400, 1048576, 10485760, 104857600)
)
```

### 4. Summary（サマリー）
分位数を追跡する指標
```python
from prometheus_client import Summary

# APIレスポンス時間
api_response_time = Summary(
    'api_response_time_seconds',
    'API response time in seconds',
    ['endpoint', 'method']
)

# LLM応答時間
llm_response_time = Summary(
    'llm_response_time_seconds',
    'LLM response time in seconds',
    ['provider', 'model']
)
```

## ビジネスメトリクス

### 1. 機能利用状況
```python
class FeatureUsageMetrics:
    """機能利用状況メトリクス"""
    
    def __init__(self):
        # 機能別利用回数
        self.feature_usage = Counter(
            'feature_usage_total',
            'Total feature usage',
            ['feature_name', 'user_type', 'environment']
        )
        
        # セッション時間
        self.session_duration = Histogram(
            'session_duration_seconds',
            'User session duration',
            ['user_type'],
            buckets=(60, 300, 600, 1800, 3600, 7200)
        )
        
        # 機能成功率
        self.feature_success_rate = Counter(
            'feature_operations_total',
            'Total feature operations',
            ['feature_name', 'status']
        )
        
    def track_feature_usage(self, feature_name: str, user_type: str, environment: str):
        """機能利用記録"""
        self.feature_usage.labels(
            feature_name=feature_name,
            user_type=user_type,
            environment=environment
        ).inc()
        
    def track_session_end(self, duration_seconds: float, user_type: str):
        """セッション終了記録"""
        self.session_duration.labels(user_type=user_type).observe(duration_seconds)
        
    def track_feature_result(self, feature_name: str, success: bool):
        """機能実行結果記録"""
        status = "success" if success else "failure"
        self.feature_success_rate.labels(
            feature_name=feature_name,
            status=status
        ).inc()
```

### 2. 品質指標
```python
class QualityMetrics:
    """品質指標メトリクス"""
    
    def __init__(self):
        # テスト成功率
        self.test_results = Counter(
            'test_results_total',
            'Total test results',
            ['test_suite', 'result']
        )
        
        # Code coverage
        self.code_coverage = Gauge(
            'code_coverage_percent',
            'Code coverage percentage',
            ['component']
        )
        
        # デプロイ成功率
        self.deployment_results = Counter(
            'deployment_results_total',
            'Total deployment results',
            ['environment', 'result']
        )
        
        # 品質ゲート通過率
        self.quality_gate_results = Counter(
            'quality_gate_results_total',
            'Quality gate results',
            ['gate_type', 'result']
        )
        
    def record_test_result(self, test_suite: str, passed: int, failed: int):
        """テスト結果記録"""
        self.test_results.labels(test_suite=test_suite, result="passed").inc(passed)
        self.test_results.labels(test_suite=test_suite, result="failed").inc(failed)
        
    def update_coverage(self, component: str, coverage_percent: float):
        """カバレッジ更新"""
        self.code_coverage.labels(component=component).set(coverage_percent)
```

## システムメトリクス

### 1. パフォーマンス指標
```python
class PerformanceMetrics:
    """パフォーマンス指標"""
    
    def __init__(self):
        # CPU使用率
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['component']
        )
        
        # メモリ使用率
        self.memory_usage = Gauge(
            'memory_usage_percent',
            'Memory usage percentage',
            ['component']
        )
        
        # ディスク使用率
        self.disk_usage = Gauge(
            'disk_usage_percent',
            'Disk usage percentage',
            ['mount_point']
        )
        
        # ネットワーク I/O
        self.network_io = Counter(
            'network_io_bytes_total',
            'Network I/O bytes',
            ['direction', 'interface']
        )
        
        # データベース接続プール
        self.db_connections = Gauge(
            'database_connections',
            'Database connections',
            ['pool_name', 'state']
        )
        
    def update_system_stats(self, stats: Dict[str, Any]):
        """システム統計更新"""
        self.cpu_usage.labels(component="system").set(stats.get("cpu_percent", 0))
        self.memory_usage.labels(component="system").set(stats.get("memory_percent", 0))
        
        for mount, usage in stats.get("disk_usage", {}).items():
            self.disk_usage.labels(mount_point=mount).set(usage)
```

### 2. 外部依存関係
```python
class DependencyMetrics:
    """外部依存関係メトリクス"""
    
    def __init__(self):
        # API呼び出し
        self.api_calls = Counter(
            'external_api_calls_total',
            'Total external API calls',
            ['provider', 'endpoint', 'status']
        )
        
        # API応答時間
        self.api_response_time = Histogram(
            'external_api_response_time_seconds',
            'External API response time',
            ['provider', 'endpoint'],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0)
        )
        
        # 接続可用性
        self.service_availability = Gauge(
            'external_service_availability',
            'External service availability',
            ['service_name']
        )
        
        # レート制限状況
        self.rate_limit_status = Gauge(
            'api_rate_limit_remaining',
            'Remaining API rate limit',
            ['provider', 'endpoint']
        )
        
    def record_api_call(self, provider: str, endpoint: str, status: str, duration: float):
        """API呼び出し記録"""
        self.api_calls.labels(
            provider=provider,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.api_response_time.labels(
            provider=provider,
            endpoint=endpoint
        ).observe(duration)
        
    def update_service_health(self, service_name: str, is_healthy: bool):
        """サービス健全性更新"""
        self.service_availability.labels(service_name=service_name).set(1 if is_healthy else 0)
```

## カスタムメトリクス実装

### 1. デコレータパターン
```python
import time
from functools import wraps
from typing import Callable, Any

def track_execution_time(metric_name: str, labels: Dict[str, str] = None):
    """実行時間追跡デコレータ"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            labels_dict = labels or {}
            labels_dict.update({
                'function': func.__name__,
                'module': func.__module__
            })
            
            try:
                result = func(*args, **kwargs)
                labels_dict['status'] = 'success'
                return result
            except Exception as e:
                labels_dict['status'] = 'error'
                labels_dict['error_type'] = type(e).__name__
                raise
            finally:
                duration = time.time() - start_time
                execution_time_metric.labels(**labels_dict).observe(duration)
                
        return wrapper
    return decorator

# 使用例
@track_execution_time('batch_processing_time', {'component': 'batch_processor'})
def process_batch_file(file_path: str):
    """バッチファイル処理"""
    pass
```

### 2. コンテキストマネージャー
```python
from contextlib import contextmanager
import time

@contextmanager
def measure_operation(operation_name: str, **labels):
    """操作測定コンテキスト"""
    start_time = time.time()
    labels.update({'operation': operation_name})
    
    # 操作開始カウント
    operation_starts.labels(**labels).inc()
    
    try:
        yield
        # 成功カウント
        operation_results.labels(status='success', **labels).inc()
    except Exception as e:
        # エラーカウント
        operation_results.labels(
            status='error',
            error_type=type(e).__name__,
            **labels
        ).inc()
        raise
    finally:
        # 実行時間記録
        duration = time.time() - start_time
        operation_duration.labels(**labels).observe(duration)

# 使用例
with measure_operation('file_upload', user_type='premium'):
    upload_file(file_data)
```

## アラート設定

### 1. 閾値ベースアラート
```yaml
# alerts.yml
groups:
  - name: system_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m])) > 2.0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High request latency"
          description: "95th percentile latency is {{ $value }}s"
          
      - alert: LowAvailability
        expr: avg(external_service_availability) < 0.95
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "External service availability low"
          description: "Service availability is {{ $value }}"
```

### 2. 異常検知アラート
```python
class AnomalyDetector:
    """異常検知"""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.historical_data = {}
        
    def check_anomaly(self, metric_name: str, current_value: float) -> bool:
        """異常検知"""
        if metric_name not in self.historical_data:
            self.historical_data[metric_name] = []
            
        history = self.historical_data[metric_name]
        
        if len(history) >= self.window_size:
            mean = sum(history) / len(history)
            variance = sum((x - mean) ** 2 for x in history) / len(history)
            std_dev = variance ** 0.5
            
            # 2σ外れ値を異常とする
            if abs(current_value - mean) > 2 * std_dev:
                return True
                
        # 履歴に追加
        history.append(current_value)
        if len(history) > self.window_size:
            history.pop(0)
            
        return False
```

## ダッシュボード設計

### 1. 概要ダッシュボード
```json
{
  "dashboard": {
    "title": "2bykilt System Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[1m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph", 
        "targets": [
          {
            "expr": "rate(errors_total[1m])",
            "legendFormat": "{{component}} {{error_type}}"
          }
        ]
      },
      {
        "title": "Response Time P95",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(request_duration_seconds_bucket[5m]))",
            "legendFormat": "{{endpoint}}"
          }
        ]
      }
    ]
  }
}
```

### 2. 詳細ダッシュボード
```json
{
  "dashboard": {
    "title": "Batch Processing Details",
    "panels": [
      {
        "title": "Job Queue Length",
        "type": "gauge",
        "targets": [
          {
            "expr": "queue_pending_jobs",
            "legendFormat": "{{queue_name}}"
          }
        ]
      },
      {
        "title": "Processing Duration",
        "type": "heatmap",
        "targets": [
          {
            "expr": "rate(batch_processing_duration_seconds_bucket[5m])",
            "legendFormat": "{{le}}"
          }
        ]
      }
    ]
  }
}
```

## 実装例

### 1. メトリクス収集器
```python
import psutil
import threading
import time
from prometheus_client import start_http_server, CollectorRegistry

class MetricsCollector:
    """メトリクス収集器"""
    
    def __init__(self, port: int = 8000, interval: int = 10):
        self.port = port
        self.interval = interval
        self.registry = CollectorRegistry()
        self.running = False
        
        # メトリクス初期化
        self._init_metrics()
        
    def _init_metrics(self):
        """メトリクス初期化"""
        self.system_metrics = PerformanceMetrics()
        self.business_metrics = FeatureUsageMetrics()
        self.quality_metrics = QualityMetrics()
        
    def start(self):
        """収集開始"""
        # HTTPサーバー起動
        start_http_server(self.port, registry=self.registry)
        
        # バックグラウンド収集開始
        self.running = True
        collection_thread = threading.Thread(target=self._collection_loop)
        collection_thread.daemon = True
        collection_thread.start()
        
    def stop(self):
        """収集停止"""
        self.running = False
        
    def _collection_loop(self):
        """収集ループ"""
        while self.running:
            try:
                self._collect_system_metrics()
                time.sleep(self.interval)
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                
    def _collect_system_metrics(self):
        """システムメトリクス収集"""
        # CPU使用率
        cpu_percent = psutil.cpu_percent()
        self.system_metrics.cpu_usage.labels(component="system").set(cpu_percent)
        
        # メモリ使用率
        memory = psutil.virtual_memory()
        self.system_metrics.memory_usage.labels(component="system").set(memory.percent)
        
        # ディスク使用率
        for partition in psutil.disk_partitions():
            try:
                disk_usage = psutil.disk_usage(partition.mountpoint)
                usage_percent = (disk_usage.used / disk_usage.total) * 100
                self.system_metrics.disk_usage.labels(
                    mount_point=partition.mountpoint
                ).set(usage_percent)
            except PermissionError:
                pass
```

### 2. 統合メトリクス管理
```python
class MetricsManager:
    """統合メトリクス管理"""
    
    def __init__(self):
        self.collectors = {}
        self.enabled = True
        
    def register_collector(self, name: str, collector: Any):
        """コレクター登録"""
        self.collectors[name] = collector
        
    def emit_metric(self, metric_type: str, name: str, value: float, labels: Dict[str, str] = None):
        """メトリクス出力"""
        if not self.enabled:
            return
            
        labels = labels or {}
        
        try:
            if metric_type == "counter":
                self._emit_counter(name, value, labels)
            elif metric_type == "gauge":
                self._emit_gauge(name, value, labels)
            elif metric_type == "histogram":
                self._emit_histogram(name, value, labels)
        except Exception as e:
            logger.error(f"Failed to emit metric {name}: {e}")
            
    def get_metrics_summary(self) -> Dict[str, Any]:
        """メトリクス要約取得"""
        summary = {}
        for name, collector in self.collectors.items():
            if hasattr(collector, 'get_metrics'):
                summary[name] = collector.get_metrics()
        return summary
```

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-26 | 初期ドラフト作成 | Copilot Agent |

---

効果的なメトリクス計測により、システムの健全性とビジネス価値を可視化してください。