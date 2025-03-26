// コマンドサジェスト機能
const DEBUG = true;  // デバッグモードを有効化

function debugLog(...args) {
    if (DEBUG) {
        console.log('[CommandSuggest]', ...args);
    }
}

document.addEventListener('DOMContentLoaded', function() {
    debugLog('コマンドサジェスト機能の初期化を開始します');
    // UIが完全にロードされるのを待つ
    setTimeout(initCommandSuggestions, 2000); // タイミングをさらに長く調整
});

async function initCommandSuggestions() {
    debugLog('コマンドサジェスト機能を初期化しています...');
    let commands = [];

    try {
        debugLog('APIリクエスト試行: /api/commands');
        const response = await fetch('/api/commands');
        if (!response.ok) {
            throw new Error(`APIエラー: ${response.status}`);
        }
        commands = await response.json();
        debugLog('コマンド情報を取得しました:', commands.length + '件', commands);
    } catch (error) {
        console.error('APIリクエスト失敗:', error);
        if (window.embeddedCommands) {
            commands = window.embeddedCommands;
            debugLog('埋め込みデータから', commands.length, '件のコマンドを使用');
        }
    }

    if (!commands || commands.length === 0) {
        debugLog('警告: コマンドが取得できませんでした。機能は無効化されます。');
        return;
    }

    // 複数の方法でテキストエリアを検索
    const findTaskInput = () => {
        debugLog('テキストエリア検索を開始');
        let candidates = [];
        const textareas = document.querySelectorAll('textarea');
        
        debugLog(`テキストエリア合計: ${textareas.length}件`);
        
        // すべてのテキストエリアの情報をログ出力
        textareas.forEach((textarea, idx) => {
            const placeholderText = textarea.placeholder || '';
            const labelEl = textarea.closest('.gradio-group')?.querySelector('label');
            const labelText = labelEl ? labelEl.textContent : '';
            
            debugLog(`テキストエリア[${idx}] placeholder="${placeholderText}" label="${labelText}"`);
            
            // 条件に一致するテキストエリアを候補に追加
            if ((labelText && (labelText.includes('Task') || labelText.includes('タスク'))) ||
                (placeholderText && (
                    placeholderText.includes('task') || 
                    placeholderText.includes('command') ||
                    placeholderText.includes('Enter your task')
                ))) {
                candidates.push(textarea);
                debugLog(`テキストエリア[${idx}]は候補に追加されました`);
            }
        });
        
        // 最も適切な候補を選択（ヒューリスティック）
        if (candidates.length > 0) {
            // まず表示されている要素のみをフィルタリング
            const visibleCandidates = candidates.filter(el => {
                const style = window.getComputedStyle(el);
                return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
            });
            
            // 表示されている要素があればそれを使う、なければ最初の候補
            return visibleCandidates.length > 0 ? visibleCandidates[0] : candidates[0];
        }
        
        // 候補がなければ、最後の手段としてid/class名で推測
        for (let i = 0; i < textareas.length; i++) {
            const classes = textareas[i].className;
            if (classes.includes('task') || classes.includes('prompt')) {
                debugLog(`クラス名による検出: テキストエリア[${i}]`);
                return textareas[i];
            }
        }
        
        return null;
    };

    let taskInput = findTaskInput();
    if (!taskInput) {
        debugLog('タスク入力欄が見つかりません。再試行します...');
        let retryCount = 0;
        const maxRetries = 20; // 最大再試行回数
        
        const retryInterval = setInterval(() => {
            retryCount++;
            taskInput = findTaskInput();
            
            if (taskInput) {
                clearInterval(retryInterval);
                debugLog(`タスク入力欄を検出しました（遅延: ${retryCount}回目）`);
                setupCommandSuggestions(taskInput, commands);
            } else if (retryCount >= maxRetries) {
                clearInterval(retryInterval);
                debugLog('最大再試行回数に達しました。タスク入力欄の検出に失敗しました。');
            }
        }, 500);
    } else {
        debugLog('タスク入力欄を検出しました（初回）');
        setupCommandSuggestions(taskInput, commands);
    }
}

function setupCommandSuggestions(textarea, commands) {
    debugLog('サジェスト機能をセットアップ中:', textarea);
    
    // 既存のコンテナを削除
    let suggestionsContainer = document.querySelector('.command-suggestions');
    if (suggestionsContainer) {
        suggestionsContainer.remove();
        debugLog('既存のサジェストコンテナを削除しました');
    }

    // 新しいコンテナを作成
    suggestionsContainer = document.createElement('div');
    suggestionsContainer.className = 'command-suggestions';
    suggestionsContainer.style.display = 'none';
    document.body.appendChild(suggestionsContainer);
    
    // グローバル変数で現在のトリガー位置を追跡
    window.currentTriggerPos = -1;

    // 入力イベント処理
    const inputHandler = function() {
        const text = this.value;
        const cursorPos = this.selectionStart;
        
        debugLog(`入力検出: カーソル位置=${cursorPos}, テキスト長=${text.length}`);
        
        // @または/の入力を検出
        const lastAtPos = text.lastIndexOf('@', cursorPos - 1);
        const lastSlashPos = text.lastIndexOf('/', cursorPos - 1);
        
        const triggerPos = Math.max(lastAtPos, lastSlashPos);
        debugLog(`トリガー文字位置: @ at ${lastAtPos}, / at ${lastSlashPos}, 最終=${triggerPos}`);
        
        if (triggerPos !== -1 && triggerPos < cursorPos) {
            const inputCommand = text.substring(triggerPos + 1, cursorPos);
            debugLog(`入力コマンド文字列: "${inputCommand}"`);
            
            // スペースがなければコマンド入力中
            if (!inputCommand.includes(' ')) {
                window.currentTriggerPos = triggerPos;
                debugLog('コマンド入力検出:', inputCommand, 'at position:', triggerPos);
                showSuggestions(inputCommand, triggerPos, textarea, suggestionsContainer, commands);
                return;
            }
        }
        
        hideSuggestions(suggestionsContainer);
    };

    // キーボードイベント処理
    const keydownHandler = function(e) {
        if (suggestionsContainer.style.display === 'none') return;
        
        const items = suggestionsContainer.querySelectorAll('.suggestion-item');
        if (items.length === 0) return;
        
        let activeItem = suggestionsContainer.querySelector('.suggestion-item.active');
        let activeIndex = -1;
        
        if (activeItem) {
            for (let i = 0; i < items.length; i++) {
                if (items[i] === activeItem) {
                    activeIndex = i;
                    break;
                }
            }
        }
        
        debugLog(`キーボードイベント: ${e.key}, アクティブインデックス: ${activeIndex}`);
        
        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (activeItem) activeItem.classList.remove('active');
                activeIndex = (activeIndex + 1) % items.length;
                items[activeIndex].classList.add('active');
                items[activeIndex].scrollIntoView({block: 'nearest'});
                break;
                
            case 'ArrowUp':
                e.preventDefault();
                if (activeItem) activeItem.classList.remove('active');
                activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
                items[activeIndex].classList.add('active');
                items[activeIndex].scrollIntoView({block: 'nearest'});
                break;
                
            case 'Enter':
                if (activeItem) {
                    e.preventDefault();
                    const cmdName = activeItem.dataset.command;
                    debugLog(`Enter キーによるコマンド選択: ${cmdName}`);
                    const cmd = commands.find(c => c.name === cmdName);
                    if (cmd) {
                        insertCommand(cmd, textarea, suggestionsContainer);
                    }
                }
                break;
                
            case 'Escape':
                e.preventDefault();
                hideSuggestions(suggestionsContainer);
                break;
        }
    };

    // フォーカス喪失時に候補を非表示
    const blurHandler = function() {
        setTimeout(() => hideSuggestions(suggestionsContainer), 200);
    };

    // 既存のイベントリスナーを削除してからバインド
    textarea.removeEventListener('input', inputHandler);
    textarea.removeEventListener('keydown', keydownHandler);
    textarea.removeEventListener('blur', blurHandler);
    
    textarea.addEventListener('input', inputHandler);
    textarea.addEventListener('keydown', keydownHandler);
    textarea.addEventListener('blur', blurHandler);
    
    // Gradioの再描画対策（要素が再生成された場合に対応）
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'childList' && mutation.removedNodes.length > 0) {
                for (let i = 0; i < mutation.removedNodes.length; i++) {
                    const node = mutation.removedNodes[i];
                    if (node === textarea || node.contains(textarea)) {
                        debugLog('監視対象のテキストエリアが削除されました。再セットアップを試みます...');
                        setTimeout(initCommandSuggestions, 500);
                        observer.disconnect();
                        return;
                    }
                }
            }
        });
    });
    
    observer.observe(document.body, { childList: true, subtree: true });
    
    debugLog('サジェスト機能のセットアップ完了');
    
    // 動作確認のために直接呼び出してみる
    setTimeout(() => {
        debugLog('コマンドリスト表示機能をテスト中...');
        showSuggestions('', -1, textarea, suggestionsContainer, commands);
    }, 1000);
}

function showSuggestions(inputText, triggerPos, textarea, container, commands) {
    // 最初から全部表示し、入力があればフィルタリング
    let filtered = commands;
    if (inputText.length > 0) {
        const exactMatches = commands.filter(cmd => 
            cmd.name.toLowerCase().startsWith(inputText.toLowerCase())
        );
        
        const partialMatches = commands.filter(cmd => 
            !cmd.name.toLowerCase().startsWith(inputText.toLowerCase()) &&
            cmd.name.toLowerCase().includes(inputText.toLowerCase())
        );
        
        filtered = [...exactMatches, ...partialMatches];
    }

    if (filtered.length === 0) {
        debugLog('フィルタリング結果: 候補なし');
        hideSuggestions(container);
        return;
    }

    debugLog('フィルタリングされた候補:', filtered.length + '件');
    
    // 位置調整
    const rect = textarea.getBoundingClientRect();
    debugLog('テキストエリア位置:', rect);
    
    container.style.top = `${rect.top + 30}px`;
    container.style.left = `${rect.left + 20}px`;
    container.innerHTML = '';

    filtered.forEach(cmd => {
        const item = document.createElement('div');
        item.className = 'suggestion-item';
        item.dataset.command = cmd.name;

        const nameSpan = document.createElement('span');
        nameSpan.innerHTML = `<strong>${cmd.name}</strong>`;
        item.appendChild(nameSpan);

        if (cmd.description) {
            const descSpan = document.createElement('span');
            descSpan.className = 'suggestion-desc';
            descSpan.textContent = cmd.description.substring(0, 40) + 
                (cmd.description.length > 40 ? '...' : '');
            item.appendChild(descSpan);
        }

        item.addEventListener('click', () => {
            debugLog(`コマンド選択: ${cmd.name} (クリック)`);
            insertCommand(cmd, textarea, container);
        });

        container.appendChild(item);
    });

    const firstItem = container.querySelector('.suggestion-item');
    if (firstItem) firstItem.classList.add('active');
    
    // グローバル変数にtriggerPosを保存
    window.currentTriggerPos = triggerPos;
    debugLog(`サジェスト表示: トリガー位置=${triggerPos}, 候補数=${filtered.length}`);
    
    container.style.display = 'block';
}

function hideSuggestions(container) {
    if (container) {
        container.style.display = 'none';
        debugLog('サジェストを非表示');
    }
}

function insertCommand(cmd, textarea, container) {
    const text = textarea.value;
    const triggerPos = window.currentTriggerPos;
    
    debugLog(`コマンド挿入: ${cmd.name}, トリガー位置=${triggerPos}`);
    
    if (triggerPos === -1 || triggerPos >= text.length) {
        debugLog('警告: 無効なトリガー位置です');
        return;
    }
    
    // コマンド部分を置き換え
    let newText = text.substring(0, triggerPos + 1) + cmd.name + ' ';
    
    // 必須パラメータのプレースホルダーを追加
    const requiredParams = cmd.params ? cmd.params.filter(p => p.required) : [];
    if (requiredParams.length > 0) {
        newText += requiredParams.map(p => `${p.name}=`).join(' ');
    }
    
    // カーソル位置以降のテキストを追加
    newText += text.substring(textarea.selectionStart);
    
    debugLog('新しいテキスト:', newText);
    textarea.value = newText;
    
    // カーソルを適切な位置に設定
    const newCursorPos = triggerPos + 1 + cmd.name.length + 1 + 
        (requiredParams.length > 0 ? 
            requiredParams.reduce((acc, p) => acc + p.name.length + 1, 0) : 0);
    
    textarea.focus();
    textarea.selectionStart = textarea.selectionEnd = newCursorPos;
    hideSuggestions(container);
    debugLog(`コマンドを挿入しました: ${cmd.name}, 新カーソル位置=${newCursorPos}`);
}
