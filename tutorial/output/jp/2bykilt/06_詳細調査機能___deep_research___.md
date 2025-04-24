# Chapter 6: 詳細調査機能 (`Deep Research`)


前の章[スクリプトベース自動化](05_スクリプトベース自動化_.md)では、`pytest`スクリプトと`llms.txt`を使って、決まった手順の作業を高速かつ正確に自動化する方法を学びました。これは、毎日のルーチンワークなどに非常に便利ですね。

しかし、もしあなたが「ある特定のテーマについて、関連する情報をウェブから徹底的に調べて、最新の動向や重要なポイントをまとめたレポートを作成してほしい」と考えたらどうでしょう？ これは単なる定型作業の自動化ではなく、より複雑で、深い調査と情報の整理・統合が必要なタスクです。

この章では、まさにそのような高度な要求に応えるための機能、**詳細調査機能 (`Deep Research`)** について学びます。

## 詳細調査機能 (`Deep Research`) とは？ なぜ必要？

あなたは、ある最新技術、例えば「強化学習を用いた大規模言語モデル（LLM）のトレーニング（RLHF）」について、その起源から最新の進歩、将来の展望までを包括的に調査し、レポートにまとめたいと考えたとします。

これを実現するには、

1.  まず、どのような情報を集めるべきか**調査計画**を立てる必要があります。
2.  次に、計画に基づいて適切なキーワードで何度も**ウェブ検索**を繰り返します。
3.  見つけたウェブサイトや論文（PDFなど）を読み込み、**重要な情報を抽出**します。
4.  集めた情報を整理し、重複を除き、**要点をまとめ**ます。
5.  最後に、収集・整理した情報に基づいて、論理的な構成で**レポートを作成**します。

これはまるで、**テーマを与えられた研究者**が行う作業そのものです。関連文献（ウェブサイト）を探し、必要な情報を抜き書きし、分析・考察を加えて、最終的に一つの研究レポートにまとめ上げます。

**詳細調査機能 (`Deep Research`)** は、この研究者のような一連の作業を自律的に実行してくれる機能です。あなたが調査したいテーマ（タスク）を与えるだけで、`2bykilt`が内部でLLMと[カスタムエージェント (`CustomAgent`)](02_カスタムエージェント___customagent___.md)を駆使して、調査からレポート作成までを行ってくれます。

この機能が必要となるのは、以下のような場合です：

*   特定のトピックについて、**網羅的かつ深く調査**したい。
*   複数の情報源から得た情報を**比較・整理・統合**したい。
*   調査結果を**構造化されたレポート**としてまとめたい。
*   複雑な調査プロセスを**自動化**して時間を節約したい。

`Deep Research`機能を使えば、あなたは調査のテーマ設定に集中でき、面倒な情報収集や整理、レポート作成の大部分を`2bykilt`に任せることができるのです。

## 主要な構成要素

`Deep Research`機能は、内部でいくつかのステップを経て調査とレポート作成を進めます。

```mermaid
graph TD
    A[ユーザー: 調査タスク指示] --> B{調査計画・クエリ生成 (LLM)};
    B -- 調査計画と検索クエリ --> C{ウェブ検索・情報抽出 (CustomAgent x N回)};
    C -- 収集した情報 --> D{情報記録・整理 (LLM)};
    D -- 整理された情報 --> B; subgraph 調査ループ
    B
    C
    D
    end
    D -- 最終的な全情報 --> E{レポート生成 (LLM)};
    E -- Markdownレポート --> F[ユーザー: 結果確認];

    style B fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#ccf,stroke:#333,stroke-width:2px
    style D fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#f9f,stroke:#333,stroke-width:2px
```

1.  **調査計画・クエリ生成 (LLM):**
    *   ユーザーが指定した調査タスクと、これまでの調査で収集した情報を基に、LLMが「次に何を調べるべきか」という**調査計画**を立て、具体的な**検索クエリ**（検索エンジンで使うキーワード）のリストを生成します。
2.  **ウェブ検索・情報抽出 (CustomAgent x N回):**
    *   生成された各検索クエリについて、[カスタムエージェント (`CustomAgent`)](02_カスタムエージェント___customagent___.md)が起動されます。
    *   エージェントはウェブ検索を実行し、関連性の高そうなページにアクセスして情報を収集します。場合によっては、ページの内容を要約・抽出するための特別なアクション（例: `extract_content`）を実行することもあります。
3.  **情報記録・整理 (LLM):**
    *   各エージェントが収集してきた情報を、別のLLM（記録・整理役）が受け取ります。
    *   このLLMは、新しい情報が既存の記録と重複していないかを確認し、重要な情報を要約して、情報源（URL、タイトル）と共に記録します。この際、「この情報はレポートのどの部分で使えそうか」といった考察（`thinking`）も付与されます。
4.  **調査ループ:**
    *   ステップ1〜3を繰り返します。新しい情報が得られるたびに、次の調査計画とクエリ生成に反映されます。
    *   LLMが「もう十分に情報が集まった」と判断するか、設定された最大反復回数に達すると、ループは終了します。
5.  **レポート生成 (LLM):**
    *   調査ループで収集・整理された全ての情報を基に、最終的なレポートを作成するためのLLM（レポート作成役）が呼び出されます。
    *   このLLMは、情報を構造化し、論理的な流れで記述し、引用情報などを適切に含んだMarkdown形式のレポートを生成します。

この一連の流れを通じて、単一の指示から包括的な調査レポートが自動生成されるのです。

## 使ってみよう：RLHFに関するレポート作成

では、実際に[GradioウェブUI](01_gradioウェブui_.md)を使って、冒頭の例「強化学習を用いた大規模言語モデル（LLM）のトレーニング（RLHF）」に関するレポートを作成してみましょう。

1.  **UIの起動:**
    ターミナルで`2bykilt`プロジェクトのディレクトリに移動し、`python bykilt.py`を実行してUIを起動します。

2.  **タブの選択:**
    UI上部のタブから「**🧐 Deep Research**」をクリックします。

3.  **入力:**
    *   **Research Task:** 調査したい内容を入力します。今回は以下のように入力してみましょう。
        ```
        強化学習を用いた大規模言語モデルのトレーニング（RLHF）について、その起源、現在の進歩、将来の展望を、関連するモデルや技術の例を挙げて包括的に調査し、独自の洞察と分析を加えたレポートを作成してください。単なる既存文献の要約にとどまらない内容を期待します。
        ```
    *   **Max Search Iteration:** 調査ループの最大反復回数を指定します。反復回数が多いほど深く調査しますが、時間もかかります。デフォルトは`3`です。今回は`3`のままにしてみましょう。
    *   **Max Query per Iteration:** 1回の調査ループで生成・実行する検索クエリの最大数を指定します。デフォルトは`1`です。（複数にすると並列でエージェントが動きますが、複雑になるため最初は`1`がおすすめです）
    *   **LLM/Browser設定:** 「🔧 LLM Configuration」や「🌐 Browser Settings」タブの設定がここでも使用されます。必要に応じて確認・調整してください。（特に、性能の高いLLMを選択すると、レポートの質が向上する可能性があります）

4.  **実行:**
    「**▶️ Run Deep Research**」ボタンをクリックします。

5.  **実行の監視と結果確認:**
    *   実行が開始されると、バックエンドで調査プロセスが進行します。UI上には直接的なライブビューは表示されませんが、処理が進んでいることを示すメッセージが表示されることがあります。
    *   調査プロセスは、反復回数や調査内容によりますが、数分から数十分かかる場合があります。
    *   途中で調査を止めたい場合は、「**⏹️ Stop**」ボタンをクリックします。プロセスは安全なタイミングで停止します。
    *   調査とレポート生成が完了すると、「**Research Report**」エリアに生成されたMarkdown形式のレポートが表示されます。
    *   「**Download Research Report**」には、生成されたレポートのMarkdownファイルが表示され、ダウンロードできます。

これで、指定したテーマに関する調査レポートが自動的に作成されました！生成されたレポートの内容を確認し、必要に応じて手直しを加えることができます。

## 内部の仕組み：Deep Researchはどのように動く？

ユーザーが「▶️ Run Deep Research」ボタンを押した後、`2bykilt`の内部ではどのような処理が行われているのでしょうか？

### ステップ・バイ・ステップの流れ

1.  **UIからの入力:** ユーザーは調査タスクと設定（反復回数など）を入力し、実行ボタンを押します。
2.  **バックエンド呼び出し:** Gradio UIは、これらの情報をバックエンドの `run_deep_search` 関数 (`bykilt.py`内) に渡します。
3.  **`deep_research` 関数の実行:** `run_deep_search` 関数は、受け取った情報を使って `src/utils/deep_research.py` 内の `deep_research` 関数を呼び出します。ここからが調査の本体です。
4.  **調査ループ開始:** `deep_research` 関数内で、指定された最大反復回数 (`max_search_iterations`) に達するまで、または生成される検索クエリがなくなるまでループ処理が始まります。
5.  **計画とクエリ生成:**
    *   現在の反復回数、ユーザーの初期指示、過去のクエリ履歴、これまでに記録された情報 (`history_infos`) をプロンプトとして組み立てます。
    *   このプロンプトを**調査計画LLM**に送信します。
    *   LLMは、調査計画 (`plan`) と次の検索クエリリスト (`queries`) を含むJSONを返します。
    *   返されたクエリが空リスト `[]` であれば、ループを終了します。
6.  **ウェブ検索エージェントの実行:**
    *   生成された各検索クエリ (`queries`) に対して、[カスタムエージェント (`CustomAgent`)](02_カスタムエージェント___customagent___.md)のインスタンスが作成されます。
    *   各エージェントは、割り当てられたクエリでウェブ検索を行い、関連情報を収集します。この際、必要に応じてページ内容を抽出するカスタムアクション（`extract_content`など、`deep_research.py`内で定義・登録されているもの）を使用することがあります。
    *   各エージェントの実行結果（収集したテキスト情報）が `query_results` として集められます。
    *   （`_global_agent_state.is_stop_requested()` をチェックし、停止要求があればループを中断します。）
7.  **情報記録:**
    *   各エージェントの実行結果 (`query_results`) を一つずつ処理します。
    *   現在のユーザー指示、現在の調査計画、現在のクエリ、エージェントの収集結果、そしてこれまでの記録情報 (`history_infos`) をプロンプトとして組み立てます。
    *   このプロンプトを**情報記録LLM**に送信します。
    *   LLMは、新しい情報を要約し、情報源（URL、タイトル）、そして考察（`thinking`）を付与したJSON形式のリスト (`new_record_infos`) を返します。この際、既存の情報との重複を避けるように指示されています。
    *   返された `new_record_infos` を全体の記録情報 `history_infos` に追加します。
    *   （`_global_agent_state.is_stop_requested()` をチェックし、停止要求があればループを中断します。）
8.  **ループ終了とレポート生成:**
    *   調査ループが終了した後、`deep_research` 関数は `generate_final_report` 関数を呼び出します。
    *   `generate_final_report` 関数は、最終的に蓄積された全記録情報 (`history_infos`) とユーザーの初期指示をプロンプトとして組み立てます。
    *   このプロンプトを**レポート生成LLM**に送信します。
    *   LLMは、情報を整理・構造化し、Markdown形式の最終レポート (`report_content`) を生成します。
    *   生成されたレポートはファイル (`final_report.md`) にも保存されます。
9.  **結果の返却:** `deep_research` 関数は、生成されたレポート内容 (`report_content`) とファイルパスを `run_deep_search` 関数に返します。
10. **UIへの表示:** `run_deep_search` 関数は、受け取ったレポート内容とファイルパスをGradio UIに返し、それぞれ「Research Report」エリアと「Download Research Report」に表示させます。

### シーケンス図

この複雑な流れを、主要な登場人物に絞って簡単なシーケンス図で見てみましょう。

```mermaid
sequenceDiagram
    participant User as ユーザー
    participant GradioUI as Gradio UI
    participant Backend as バックエンド (bykilt.py)
    participant DeepResearch as deep_research.py
    participant PlanLLM as 計画LLM
    participant Agent as Web検索Agent
    participant RecordLLM as 記録LLM
    participant ReportLLM as レポートLLM

    User->>GradioUI: 調査タスク入力、実行
    GradioUI->>Backend: run_deep_search(タスク, 設定)
    Backend->>DeepResearch: deep_research(タスク, LLM, ...)

    loop 調査ループ (最大反復回数まで or クエリがなくなるまで)
        DeepResearch->>PlanLLM: 計画とクエリ生成依頼 (履歴情報含む)
        PlanLLM-->>DeepResearch: 調査計画, 検索クエリリスト
        alt クエリリストが空
            DeepResearch-->> Backend: ループ終了
            break
        end
        par 各検索クエリについて並列実行 (max_query_per_iter > 1 の場合)
            DeepResearch->>Agent: CustomAgent実行 (クエリ指示)
            Agent-->>DeepResearch: 収集した情報
        end
        DeepResearch->>RecordLLM: 情報記録依頼 (収集情報, 履歴情報含む)
        RecordLLM-->>DeepResearch: 新規記録情報 (JSONリスト)
        DeepResearch->>DeepResearch: 全体記録情報を更新
    end

    DeepResearch->>ReportLLM: レポート生成依頼 (全記録情報)
    ReportLLM-->>DeepResearch: Markdownレポート
    DeepResearch-->>Backend: レポート内容, ファイルパス
    Backend-->>GradioUI: レポート表示、ダウンロードファイル設定
    GradioUI-->>User: 結果確認
```

### コードでの実装

関連するコードの主要な部分を見てみましょう。内部実装は複雑なため、ここでは構造と主要な関数呼び出しに焦点を当てます。

1.  **UIからの呼び出し起点 (`bykilt.py`)**

    ```python
    # --- File: bykilt.py ---
    async def run_deep_search(research_task, max_search_iteration_input, max_query_per_iter_input, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key, use_vision, use_own_browser, headless):
        from src.utils.deep_research import deep_research # deep_research関数をインポート
        global _global_agent_state
        _global_agent_state.clear_stop() # 停止フラグをリセット

        # LLMクライアントを初期化
        llm = utils.get_llm_model(
            provider=llm_provider, model_name=llm_model_name, num_ctx=llm_num_ctx,
            temperature=llm_temperature, base_url=llm_base_url, api_key=llm_api_key,
        )
        # メインの調査関数を呼び出す
        markdown_content, file_path = await deep_research(
            research_task, llm, _global_agent_state, # タスク、LLM、停止状態を渡す
            max_search_iterations=max_search_iteration_input,
            max_query_num=max_query_per_iter_input,
            use_vision=use_vision, headless=headless,
            use_own_browser=use_own_browser
        )
        # 結果をUIに返す
        return markdown_content, file_path, gr.update(value="Stop", interactive=True), gr.update(interactive=True)

    # ... (create_ui 関数内で research_button.click に run_deep_search を設定) ...
    research_button.click(
        fn=run_deep_search,
        inputs=[research_task_input, max_search_iteration_input, max_query_per_iter_input, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key, use_vision, use_own_browser, headless],
        outputs=[markdown_output_display, markdown_download, stop_research_button, research_button]
    )
    stop_research_button.click(fn=stop_research_agent, inputs=[], outputs=[stop_research_button, research_button])
    ```
    *   Gradio UIの「▶️ Run Deep Research」ボタンがクリックされると、`run_deep_search`関数が呼び出されます。
    *   必要なLLMクライアントを準備し、`src/utils/deep_research.py` の `deep_research` 関数を `await` で呼び出して、調査プロセスを開始します。
    *   `_global_agent_state` を渡すことで、調査中に停止ボタンが押されたことを検知できるようにしています。

2.  **メインの調査ループ (`src/utils/deep_research.py`)**

    ```python
    # --- File: src/utils/deep_research.py ---
    import asyncio
    # ... 他のインポート ...
    from src.agent.custom_agent import CustomAgent
    from src.controller.custom_controller import CustomController
    from browser_use.agent.views import ActionResult
    # ...

    async def deep_research(task, llm, agent_state=None, **kwargs):
        # ... (初期設定、保存ディレクトリ作成など) ...
        max_query_num = kwargs.get("max_query_num", 3)
        # ... (ブラウザ、コントローラーの準備) ...
        controller = CustomController() # カスタムコントローラーを使用

        # ページ内容抽出用のカスタムアクションを定義・登録
        @controller.registry.action('Extract page content to get the pure markdown.')
        async def extract_content(browser: BrowserContext):
            # ... (Jina Readerを使ってMarkdownコンテンツを抽出する処理) ...
            return ActionResult(extracted_content=msg)

        search_system_prompt = f""" ... (調査計画LLM用のシステムプロンプト) ... """
        search_messages = [SystemMessage(content=search_system_prompt)]
        record_system_prompt = """ ... (情報記録LLM用のシステムプロンプト) ... """
        record_messages = [SystemMessage(content=record_system_prompt)]

        search_iteration = 0
        max_search_iterations = kwargs.get("max_search_iterations", 10)
        history_query = [] # 過去のクエリ履歴
        history_infos = [] # 記録された情報

        try:
            while search_iteration < max_search_iterations: # 調査ループ
                search_iteration += 1
                logger.info(f"Start {search_iteration}th Search...")
                # ... (プロンプト準備) ...

                # 1. 計画とクエリ生成LLM呼び出し
                ai_query_msg = llm.invoke(search_messages[:1] + search_messages[1:][-1:])
                # ... (応答のパース、計画とクエリ取得) ...
                query_tasks = ai_query_content["queries"]
                if not query_tasks: break # クエリがなければ終了
                # ... (クエリ履歴に追加) ...

                # 2. ウェブ検索エージェント実行
                #    (CustomAgentインスタンスを作成し、並列または逐次実行)
                agents = [CustomAgent(task=q_task, llm=llm, ..., controller=controller) for q_task in query_tasks]
                query_results = await asyncio.gather(*[agent.run(...) for agent in agents])

                # 停止チェック
                if agent_state and agent_state.is_stop_requested(): break

                # 3. 情報記録LLM呼び出し
                for i in range(len(query_tasks)):
                    # ... (プロンプト準備: クエリ結果、履歴情報など) ...
                    record_prompt = f"..."
                    record_messages.append(HumanMessage(content=record_prompt))
                    ai_record_msg = llm.invoke(record_messages[:1] + record_messages[-1:])
                    # ... (応答パース、新規記録情報取得) ...
                    new_record_infos = json.loads(record_content)
                    history_infos.extend(new_record_infos) # 全体記録に追加

                # 停止チェック
                if agent_state and agent_state.is_stop_requested(): break

            logger.info("Finish Searching, Start Generating Report...")
            # 4. レポート生成
            return await generate_final_report(task, history_infos, save_dir, llm)

        except Exception as e:
            # エラーハンドリング、部分的なレポート生成を試みる
            return await generate_final_report(task, history_infos, save_dir, llm, str(e))
        finally:
            # ブラウザのクリーンアップなど
            # ...
    ```
    *   `deep_research` 関数が全体のオーケストレーションを担当します。
    *   ループ内で、計画LLM、`CustomAgent`（複数回）、記録LLMを順番に呼び出します。
    *   `CustomAgent` には `CustomController` を渡しており、必要に応じて `extract_content` のようなカスタムアクションが利用されます。
    *   停止状態 (`agent_state`) をチェックし、早期にループを抜けることができます。
    *   ループ終了後、`generate_final_report` 関数を呼び出して最終レポートを作成します。

3.  **最終レポート生成 (`src/utils/deep_research.py`)**

    ```python
    # --- File: src/utils/deep_research.py ---
    async def generate_final_report(task, history_infos, save_dir, llm, error_msg=None):
        try:
            logger.info("Attempting to generate final report...")
            writer_system_prompt = """ ... (レポート生成LLM用のシステムプロンプト) ... """
            # ... (プロンプト準備: ユーザー指示、全記録情報) ...
            report_prompt = f"User Instruction:{task} \n Search Information:\n {history_infos_}"
            report_messages = [SystemMessage(content=writer_system_prompt), HumanMessage(content=report_prompt)]

            # レポート生成LLM呼び出し
            ai_report_msg = llm.invoke(report_messages)
            # ... (応答からレポート内容を抽出、Markdown形式に整形) ...
            report_content = ai_report_msg.content
            report_content = re.sub(...) # Markdown整形
            report_content = report_content.strip()

            # エラーがあればレポート冒頭に追記
            if error_msg:
                report_content = f"## ⚠️ Research Incomplete ...\n{error_msg}\n\n{report_content}"

            # レポートをファイルに保存
            report_file_path = os.path.join(save_dir, "final_report.md")
            with open(report_file_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            logger.info(f"Save Report at: {report_file_path}")
            return report_content, report_file_path

        except Exception as report_error:
            # レポート生成自体が失敗した場合
            logger.error(f"Failed to generate report: {report_error}")
            return f"Error generating report: {str(report_error)}", None
    ```
    *   `generate_final_report` 関数は、収集された全情報 (`history_infos`) を使って、レポート生成用のLLMを呼び出します。
    *   LLMからの応答を整形し、ファイルに保存して、レポート内容とファイルパスを返します。
    *   調査中にエラーが発生していた場合、その旨をレポートの冒頭に追記します。

このように、`Deep Research` 機能は、複数のLLM呼び出しと複数回の `CustomAgent` 実行を組み合わせ、調査計画、情報収集、情報整理、レポート作成という一連のプロセスを自律的に実行しています。

## まとめ

この章では、`2bykilt`の高度な機能である**詳細調査機能 (`Deep Research`)** について学びました。

*   特定のテーマについて、ユーザーの指示に基づいて**自律的に調査**を進める機能であること。
*   内部では、**調査計画・クエリ生成(LLM) → ウェブ検索・情報抽出(CustomAgent) → 情報記録・整理(LLM)** というサイクルを繰り返し、最後に**レポート生成(LLM)** を行うこと。
*   [GradioウェブUI](01_gradioウェブui_.md)の「🧐 Deep Research」タブから簡単に利用でき、複雑な調査タスクを自動化して**Markdown形式のレポート**を得られること。
*   途中で調査を**停止**することも可能であること。

この機能を活用することで、あなたは情報収集やレポート作成の時間を大幅に節約し、より本質的な分析や考察に集中できるようになるでしょう。

---

これで、`2bykilt`チュートリアルの主要な機能を一通り学び終えました。最初の章[GradioウェブUI](01_gradioウェブui_.md)から始まり、[カスタムエージェント (`CustomAgent`)](02_カスタムエージェント___customagent___.md)、[LLM連携とプロンプト生成](03_llm連携とプロンプト生成_.md)、[ブラウザ制御とカスタムアクション](04_ブラウザ制御とカスタムアクション_.md)、[スクリプトベース自動化](05_スクリプトベース自動化_.md)、そしてこの章の[詳細調査機能 (`Deep Research`)](06_詳細調査機能___deep_research___.md)まで、`2bykilt`がどのように動作し、ウェブ操作を自動化するかを理解できたはずです。

これらの知識を基に、ぜひあなた自身のタスク自動化や調査に`2bykilt`を活用してみてください！

---

Generated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)