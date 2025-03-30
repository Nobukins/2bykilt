// グローバル変数の明示的な設定
window.CommandSystem = {
    initialized: false,
    commands: [],
    activeTextarea: null,
    suggestionsContainer: null,
    currentTrigger: null,
    selectedIndex: -1,
    filterText: '',
    isShowingSuggestions: false
};

// 即時実行関数
(function() {
    async function fetchCommands() {
        console.log("🔄 Fetching command data...");
        try {
            const response = await fetch('/api/commands');
            if (response.ok) {
                const data = await response.json();
                console.log(`✅ Retrieved ${data.length} commands`);
                window.CommandSystem.commands = data;
                return data;
            } else {
                console.error("❌ Failed to fetch commands:", response.status);
                return [];
            }
        } catch (error) {
            console.error("❌ Error fetching commands:", error);
            return [];
        }
    }

    function setupTextareaMonitoring() {
        console.log("🔍 Monitoring textareas...");
        const textareas = document.querySelectorAll('textarea');
        textareas.forEach((textarea) => {
            if (textarea.getAttribute('data-command-monitor') === 'true') return;
            textarea.setAttribute('data-command-monitor', 'true');
            textarea.addEventListener('input', handleTextareaInput);
            textarea.addEventListener('keydown', handleTextareaKeydown);
            textarea.style.border = "2px dashed red"; // Visual feedback
        });
    }

    function handleTextareaInput(e) {
        const textarea = e.target;
        const text = textarea.value;
        const cursorPos = textarea.selectionStart;
        const lastChar = cursorPos > 0 ? text.charAt(cursorPos - 1) : "";

        console.log(`📝 Input detected:`, {
            cursorPos,
            lastChar,
            trigger: lastChar === "@" || lastChar === "/" ? "✅" : "❌"
        });

        // トリガー文字の検出
        if (lastChar === "@" || lastChar === "/") {
            console.log(`🎯 Trigger character detected: ${lastChar}`);
            window.CommandSystem.currentTrigger = lastChar;
            window.CommandSystem.activeTextarea = textarea;
            window.CommandSystem.filterText = '';
            window.CommandSystem.selectedIndex = -1;
            showSuggestions(textarea, cursorPos);
        } 
        // 提案表示中の入力処理
        else if (window.CommandSystem.isShowingSuggestions) {
            // カーソル位置がトリガー文字より前に移動した場合、提案を閉じる
            const triggerPos = findLastTriggerPosition(text, cursorPos);
            if (triggerPos === -1) {
                hideSuggestions();
                return;
            }

            // フィルターテキストを更新
            window.CommandSystem.filterText = text.substring(triggerPos + 1, cursorPos);
            updateSuggestions();
        }
    }

    function handleTextareaKeydown(e) {
        if (!window.CommandSystem.isShowingSuggestions) return;

        switch (e.key) {
            case 'ArrowUp':
                e.preventDefault();
                navigateSuggestion(-1);
                break;
            case 'ArrowDown':
                e.preventDefault();
                navigateSuggestion(1);
                break;
            case 'Enter':
                if (window.CommandSystem.selectedIndex >= 0) {
                    e.preventDefault();
                    selectCurrentSuggestion();
                }
                break;
            case 'Escape':
                e.preventDefault();
                hideSuggestions();
                break;
            case 'Tab':
                if (window.CommandSystem.isShowingSuggestions) {
                    e.preventDefault();
                    selectCurrentSuggestion();
                }
                break;
        }
    }

    function findLastTriggerPosition(text, cursorPos) {
        // カーソル位置より前の最後のトリガー文字の位置を見つける
        const textBeforeCursor = text.substring(0, cursorPos);
        const lastAtPos = textBeforeCursor.lastIndexOf('@');
        const lastSlashPos = textBeforeCursor.lastIndexOf('/');
        
        // 最後に見つかったトリガー文字の位置を返す
        const lastTriggerPos = Math.max(lastAtPos, lastSlashPos);
        
        // トリガー文字が見つからない、または空白で区切られている場合は-1を返す
        if (lastTriggerPos === -1) return -1;
        
        // トリガー文字の前に空白があるか、文字列の先頭の場合のみ有効
        const charBeforeTrigger = lastTriggerPos > 0 ? textBeforeCursor.charAt(lastTriggerPos - 1) : ' ';
        if (charBeforeTrigger === ' ' || charBeforeTrigger === '\n' || lastTriggerPos === 0) {
            return lastTriggerPos;
        }
        
        return -1;
    }

    function showSuggestions(textarea, cursorPos) {
        // 既存の提案コンテナを削除
        if (window.CommandSystem.suggestionsContainer) {
            window.CommandSystem.suggestionsContainer.remove();
        }

        // 新しい提案コンテナを作成
        const suggestionsContainer = document.createElement('div');
        suggestionsContainer.className = 'command-suggestions';
        suggestionsContainer.style.position = 'absolute';
        suggestionsContainer.style.zIndex = '10000';
        suggestionsContainer.style.backgroundColor = 'white';
        suggestionsContainer.style.border = '1px solid #ccc';
        suggestionsContainer.style.borderRadius = '4px';
        suggestionsContainer.style.boxShadow = '0 2px 8px rgba(0,0,0,0.2)';
        suggestionsContainer.style.maxHeight = '200px';
        suggestionsContainer.style.overflowY = 'auto';
        suggestionsContainer.style.width = '300px';

        // テキストエリアの位置に基づいて配置
        const rect = textarea.getBoundingClientRect();
        const lineHeight = parseInt(getComputedStyle(textarea).lineHeight) || 20;
        
        // カーソル位置の座標を計算（簡易的な実装）
        const textBeforeCursor = textarea.value.substring(0, cursorPos);
        const lines = textBeforeCursor.split('\n');
        const currentLine = lines.length;
        
        suggestionsContainer.style.top = `${rect.top + window.scrollY + (currentLine * lineHeight)}px`;
        suggestionsContainer.style.left = `${rect.left + window.scrollX}px`;

        // 提案リストを表示
        updateSuggestionsContent(suggestionsContainer);
        
        // DOMに追加
        document.body.appendChild(suggestionsContainer);
        window.CommandSystem.suggestionsContainer = suggestionsContainer;
        window.CommandSystem.isShowingSuggestions = true;
    }

    function updateSuggestions() {
        if (!window.CommandSystem.suggestionsContainer) return;
        updateSuggestionsContent(window.CommandSystem.suggestionsContainer);
    }

    function updateSuggestionsContent(container) {
        // フィルタリングされたコマンドリストを取得
        const filteredCommands = filterCommands(window.CommandSystem.filterText);
        
        // コンテナをクリア
        container.innerHTML = '';
        
        if (filteredCommands.length === 0) {
            const noResults = document.createElement('div');
            noResults.textContent = 'No commands found';
            noResults.style.padding = '8px 12px';
            noResults.style.color = '#999';
            container.appendChild(noResults);
            return;
        }
        
        // 提案リストを作成
        filteredCommands.forEach((command, index) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item';
            item.style.padding = '8px 12px';
            item.style.cursor = 'pointer';
            
            if (index === window.CommandSystem.selectedIndex) {
                item.classList.add('active');
                item.style.backgroundColor = '#e0e0e0';
            }
            
            // コマンド名と説明を表示
            const nameSpan = document.createElement('span');
            nameSpan.textContent = command.name;
            nameSpan.style.fontWeight = 'bold';
            
            const descSpan = document.createElement('span');
            descSpan.textContent = command.description ? ` - ${command.description}` : '';
            descSpan.style.color = '#666';
            
            item.appendChild(nameSpan);
            item.appendChild(descSpan);
            
            // クリックイベントを追加
            item.addEventListener('click', () => {
                window.CommandSystem.selectedIndex = index;
                selectCurrentSuggestion();
            });
            
            // マウスオーバーイベントを追加
            item.addEventListener('mouseover', () => {
                window.CommandSystem.selectedIndex = index;
                updateSuggestions();
            });
            
            container.appendChild(item);
        });
    }

    function filterCommands(filterText) {
        if (!window.CommandSystem.commands || window.CommandSystem.commands.length === 0) {
            return [];
        }
        
        if (!filterText) {
            return window.CommandSystem.commands;
        }
        
        // フィルターテキストに基づいてコマンドをフィルタリング
        return window.CommandSystem.commands.filter(cmd => 
            cmd.name.toLowerCase().includes(filterText.toLowerCase())
        );
    }

    function navigateSuggestion(direction) {
        const filteredCommands = filterCommands(window.CommandSystem.filterText);
        if (filteredCommands.length === 0) return;
        
        // 選択インデックスを更新
        let newIndex = window.CommandSystem.selectedIndex + direction;
        if (newIndex < 0) {
            newIndex = filteredCommands.length - 1;
        } else if (newIndex >= filteredCommands.length) {
            newIndex = 0;
        }
        
        window.CommandSystem.selectedIndex = newIndex;
        updateSuggestions();
        
        // 選択項目が見えるようにスクロール
        const container = window.CommandSystem.suggestionsContainer;
        const selectedItem = container.children[newIndex];
        if (selectedItem) {
            if (selectedItem.offsetTop < container.scrollTop) {
                container.scrollTop = selectedItem.offsetTop;
            } else if (selectedItem.offsetTop + selectedItem.offsetHeight > container.scrollTop + container.offsetHeight) {
                container.scrollTop = selectedItem.offsetTop + selectedItem.offsetHeight - container.offsetHeight;
            }
        }
    }

    function selectCurrentSuggestion() {
        const filteredCommands = filterCommands(window.CommandSystem.filterText);
        if (filteredCommands.length === 0 || window.CommandSystem.selectedIndex < 0) {
            hideSuggestions();
            return;
        }
        
        const selectedCommand = filteredCommands[window.CommandSystem.selectedIndex];
        const textarea = window.CommandSystem.activeTextarea;
        if (!textarea || !selectedCommand) return;
        
        // テキストエリアの現在の値を取得
        const text = textarea.value;
        const cursorPos = textarea.selectionStart;
        
        // トリガー文字の位置を見つける
        const triggerPos = findLastTriggerPosition(text, cursorPos);
        if (triggerPos === -1) {
            hideSuggestions();
            return;
        }
        
        // コマンドテンプレートを生成
        let commandTemplate = selectedCommand.name;
        
        // 必須パラメータがあれば追加
        if (selectedCommand.params) {
            const requiredParams = selectedCommand.params.filter(p => p.required);
            if (requiredParams.length > 0) {
                commandTemplate += ' ' + requiredParams.map(p => `${p.name}=`).join(' ');
            }
        }
        
        // テキストエリアの値を更新
        const newText = text.substring(0, triggerPos) + 
                        window.CommandSystem.currentTrigger + 
                        commandTemplate + 
                        text.substring(cursorPos);
        
        textarea.value = newText;
        
        // カーソル位置を更新
        const newCursorPos = triggerPos + window.CommandSystem.currentTrigger.length + commandTemplate.length;
        textarea.setSelectionRange(newCursorPos, newCursorPos);
        
        // 提案を閉じる
        hideSuggestions();
        
        // input イベントを発火させて変更を通知
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
    }

    function hideSuggestions() {
        if (window.CommandSystem.suggestionsContainer) {
            window.CommandSystem.suggestionsContainer.remove();
            window.CommandSystem.suggestionsContainer = null;
        }
        window.CommandSystem.isShowingSuggestions = false;
        window.CommandSystem.selectedIndex = -1;
        window.CommandSystem.filterText = '';
    }

    async function initCommandSystem() {
        if (window.CommandSystem.initialized) {
            console.log("⚠️ Command system already initialized");
            return;
        }

        console.log("🚀 Initializing command system...");
        await fetchCommands();
        setupTextareaMonitoring();
        window.CommandSystem.initialized = true;
        console.log("✅ Command system initialized");
        
        // ウィンドウクリックイベントを追加（提案リスト外をクリックしたら閉じる）
        document.addEventListener('click', (e) => {
            if (window.CommandSystem.isShowingSuggestions) {
                const container = window.CommandSystem.suggestionsContainer;
                if (container && !container.contains(e.target) && 
                    e.target !== window.CommandSystem.activeTextarea) {
                    hideSuggestions();
                }
            }
        });
    }

    if (document.readyState === 'complete') {
        setTimeout(initCommandSystem, 1000);
    } else {
        window.addEventListener('load', () => setTimeout(initCommandSystem, 1000));
    }
})();

// CSSスタイルを追加（一度だけ）
const style = document.createElement('style');
style.textContent = `
.command-suggestions {
    font-family: Arial, sans-serif;
    font-size: 14px;
    color: #333;
    background-color: white;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    max-height: 200px;
    overflow-y: auto;
    width: 300px;
}
.suggestion-item {
    padding: 8px 12px;
    cursor: pointer;
    transition: background-color 0.3s;
}
.suggestion-item:hover {
    background-color: #f0f0f0;
}
.suggestion-item.active {
    background-color: #e0e0e0;
}
`;
document.head.appendChild(style);
