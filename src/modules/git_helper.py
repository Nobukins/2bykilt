import subprocess
import os
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

def check_git_installed():
    """Gitがインストールされているか確認"""
    try:
        subprocess.run(["git", "--version"], check=True, capture_output=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        logger.error("Gitがインストールされていません")
        return False

def should_update_repository(repo_dir, update_interval=3600):
    """Check if repository needs update (based on time since last pull)"""
    last_update_file = os.path.join(repo_dir, ".last_update")
    if not os.path.exists(last_update_file):
        return True
        
    with open(last_update_file) as f:
        try:
            last_update = float(f.read().strip())
            return (time.time() - last_update) > update_interval
        except:
            return True

def update_last_pull_time(repo_dir):
    """Update the timestamp of the last pull"""
    last_update_file = os.path.join(repo_dir, ".last_update")
    with open(last_update_file, "w") as f:
        f.write(str(time.time()))

def clone_or_pull_repository(repo_url, target_dir, update_interval=3600):
    """リポジトリをクローンまたは更新する"""
    if not check_git_installed():
        logger.error("Gitがインストールされていないため、操作を実行できません")
        return False
    
    target_dir = Path(target_dir)
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    
    if (target_dir / ".git").exists():
        # Repository exists, check if we should update it
        if should_update_repository(target_dir, update_interval):
            logger.info(f"リポジトリを更新中: {repo_url}")
            result = subprocess.run(["git", "pull"], cwd=str(target_dir), capture_output=True)
            if result.returncode == 0:
                update_last_pull_time(target_dir)
                return True
            else:
                logger.error(f"リポジトリの更新に失敗しました: {result.stderr.decode()}")
                return False
        else:
            logger.info(f"リポジトリは最近更新されています: {repo_url}")
            return True
    else:
        # Repository doesn't exist, clone it
        target_dir.mkdir(exist_ok=True)
        logger.info(f"リポジトリをクローン中: {repo_url}")
        result = subprocess.run(["git", "clone", repo_url, str(target_dir)], capture_output=True)
        if result.returncode == 0:
            update_last_pull_time(target_dir)
            return True
        else:
            logger.error(f"リポジトリのクローンに失敗しました: {result.stderr.decode()}")
            return False

def checkout_version(repo_dir, version):
    """Checkout specific tag, branch or commit"""
    if not version:
        return True
        
    logger.info(f"バージョンをチェックアウト中: {version}")
    result = subprocess.run(
        ["git", "checkout", version],
        cwd=str(repo_dir),
        capture_output=True
    )
    
    if result.returncode == 0:
        return True
    else:
        logger.error(f"バージョン {version} のチェックアウトに失敗しました: {result.stderr.decode()}")
        return False
