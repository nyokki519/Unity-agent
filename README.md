# Unity SEO Growth Agent

Unity公式HPの検索パフォーマンスを週次で取得し、前週比較・検索語分析・URL Inspection・改善候補・施策履歴をMarkdownにまとめます。有料サービス、外部AI API、検索順位を見た短期の自動書き換えは使用しません。

## 実行

Python 3.11以上。既存のクラウドチェックアウトを利用し、追加worktreeは作成しません。

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m seo_growth.cli --ledger state/ledger.json run --redact-queries
```

`out/` にJSONとMarkdown、`state/ledger.json`に検索語を含まない判断・観察履歴を保存します。API未認証でも公開HTTP診断と「未取得」のレポートを作成します。ゼロ件に置換しません。接続必須の監視には `run --require-gsc` を指定します。

## Search Console認証（人間による初回設定）

1. Google CloudでGoogle Search Console APIを有効化します。
2. サービスアカウントを作成し、そのメールアドレスをSearch Consoleの **URLプレフィックス** `https://nyokki519.github.io/unityHP/` のユーザーに追加します（フル権限）。所有権確認HTMLは既存のまま維持します。
3. 認証JSONをこのリポジトリのGitHub Actions secret **GSC_CREDENTIALS_JSON** に設定します。値をGit、チャット、公開レポートへ記載しないでください。ローカルは `GOOGLE_APPLICATION_CREDENTIALS` にファイルパスを設定します。Google ADCに対応します。
4. Actions → SEO Growth weekly → Run workflowで確認します。`gscStatus: available` が成功条件です。API未有効・権限不足・接続失敗を区別してレポートに残します。

認証ファイルはrunnerの一時領域に0600で保存し、成果物には含めません。API OAuthスコープは `webmasters.readonly` のみです。既に所有権確認済みでも、API用認証・ユーザー権限は別に必要です。

## 週次自動化と安全な改善

毎週月曜08:45 JST（GitHub側の遅延はあり得ます）に実行します。Googleの日付はPacificで、最終データの3日遅延を置いた同じ長さの7日間を比較します。プロパティ集計をクエリ一覧の合算で代用しません。匿名化検索語や上位行制限、50,000行の取得上限、出力100行の制限を明示します。

十分な表示回数のある低CTRページを改善候補にし、同一候補は28日間再提案を抑制します。施策適用後も最低28日の観察期間を置きます。前後比較は季節性等の影響があり、因果効果の証明ではありません。

施策の登録例（実際の適用日・commitへ置換）：

```bash
.venv/bin/python -m seo_growth.cli --ledger state/ledger.json record-measure \
  --id homepage-seo-2026-10 --date 2026-10-11 \
  --summary '初期HTML・構造化データ・参加ガイドの改善' \
  --commit '<実際のHP commit>' --page 'https://nyokki519.github.io/unityHP/'
```

任意の **SEO_HP_TOKEN**（unityHPのcontents/PR書き込みに限定したtoken）をActions secretに設定すると、既存SSGの決定的再生成に限り、テスト・差分確認済みのPRを作ります。許可対象は生成物 `index.html` のみ。公開文言・イベント日時・人物紹介・写真・設定の自動変更、直接main反映、自動マージ、force pushは行いません。PRが既にある場合や28日以内は抑制します。現在の正規生成結果では通常差分がなくPRは不要です。

```bash
.venv/bin/python -m seo_growth.automation --repo /workspace/unityHP --ledger state/ledger.json
```

Actionsは検索語を伏せた週次Markdownを `reports/` に保存し、JSON等を90日間のartifactに保存します。公開レポートには集計数値・公開ページURLが含まれます。検索語の詳細は認証付きAnalyticsかローカル非公開出力で参照してください。判断履歴はcacheではなくGit保存なので、runnerの入れ替えでも観察期間を維持します。

## Unity Analytics連携

Analyticsの `supabase/migrations/013_seo_growth.sql` を適用し、Vercelと本リポジトリのActions secretに同じ **SEO_INGEST_TOKEN**（16文字以上の専用ランダムキー）を設定します。ローカルは `SEO_ANALYTICS_URL=https://unity-analytics.vercel.app/api/seo/reports` と専用キーを環境変数に設定します。Google認証・Supabase管理キーをHTTP送信しません。

認証付きPOSTは生の検索語を含む非公開レポートを保存します。専用HTTPS endpoint以外とリダイレクトは拒否します。キー未設定・API未配備・SQL未適用は `analyticsStatus` に記録し、検索レポート生成は続けます。保存は同じID・内容の再送を許容し、異なる内容への上書きを拒否します。

## Obsidian

ローカル実行に `run --vault /path/to/vault` を追加すると `Unity/SEO/Weekly/` に管理マーカー付きMarkdownを出力します。ユーザー編集済みの同名ファイル、内容の異なる既存レポート、Vault外パス、symlinkは上書きしません。GitHub Actionsから利用者の端末Vaultへ直接書き込むことはできません。

## 取得できる情報・取得できない情報

- 取得可能：Search Analyticsの表示回数・クリック・CTR・平均掲載順位・検索語・ページ、sitemap状態、指定URLの最終インデックス情報。
- 取得不可：Google全検索の順位追跡、APIにないSearch Consoleの全画面、ライブURL検査、インデックス登録リクエスト、手動対策/セキュリティ情報、Instagramの未認証Insights、LINE/つなげーとの直接申込・現地参加人数・全参加申込CVR、field Core Web Vitals。
- HTTP200、sitemap公開、`site:`検索だけではGoogleのインデックス完了を断定しません。Search Console APIの接続後にURL Inspectionで確認します。

## 停止・ロールバック

Actions workflowを無効化するか専用secretを解除して自動化を停止できます。HP変更は個別commitを `git revert` し、テスト後に通常pushします。Google所有権確認ファイルは削除しません。Analyticsの履歴テーブルは停止時も保持します。

公式仕様：
- https://developers.google.com/webmaster-tools/v1/searchanalytics/query
- https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect
- https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics

## Instagram・参加申込の週次レポート

週次runにGrowth同期/集計を追加しています。既存 `SEO_INGEST_TOKEN` で固定Analytics APIに接続し、Instagram公式Insightsのreach/views/total_interactionsと、推定流入元別のHP訪問→申込クリック→Google側の受付確認を取得します。Meta/フォーム秘密値はAgentに置きません。Googleの検索語を個人申込と結びつけません。

[Analyticsの導入手順](https://github.com/nyokki519/unity-analytics/blob/main/docs/growth-measurement.md)のSQL014、Vercelの計測有効化、Meta認証、Form確認triggerが本番の前提です。未設定・権限不足・開始前は0ではなく未取得、部分取得・10,000行の上限・90日保存期間外をレポートで明示します。受付確認は同じ初回流入コホートの30日以内のセッションで、参加人数/実出席とは区別します。集計はUTC、GSCはPacificで、率や期間比較をそのまま因果効果とは呼びません。

Markdown/Obsidian出力にもGrowth集計を含みます。公開Markdownには集計のみをコピーし、UUID・receipt・accountID・token・フォーム回答・検索語を追加しません。既存GSCレポートはGrowth接続が失敗しても作成を続けます。`state/integration-status.json` に秘密を含まない接続状態を保存します。
