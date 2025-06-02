# Django RAG システム

マークダウンファイルをアップロードして、AIとチャットできるRAG（Retrieval-Augmented Generation）システムです。

## 機能

- **ユーザー認証**: django-allauthを使用したメール認証
- **ドキュメント管理**: マークダウンファイルのアップロード・管理
- **RAG機能**: アップロードしたドキュメントに基づくAIチャット
- **ベクトル検索**: Chromaを使用したセマンティック検索
- **HyDE**: Hypothetical Document Embedderによる高精度検索

## 技術スタック

- **Backend**: Django 5.2+
- **Frontend**: Bootstrap 5
- **AI/ML**:
  - LangChain
  - Google Gemini 2.0 Flash (LLM)
  - Google Text Embedding 004 (Embeddings)
- **Vector Store**: ChromaDB
- **Authentication**: django-allauth
- **Document Processing**: Unstructured

## セットアップ

### 1. 環境変数の設定

`.env`ファイルを作成し、以下の環境変数を設定してください：

```env
# Django設定
SECRET_KEY=your-secret-key-here
DEBUG=True

# Gemini API
GEMINI_API=your-gemini-api-key-here

# LangSmith（オプション）
LANGCHAIN_API_KEY=your-langchain-api-key-here
```

**注意**: 開発環境では、メール認証は無効化されており、コンソールにメールが出力されます。本番環境では適切なメールサーバー設定が必要です。

### 2. 依存関係のインストール

```bash
uv sync
```

### 3. データベースのマイグレーション

```bash
python manage.py migrate
```

### 4. スーパーユーザーの作成

```bash
python manage.py createsuperuser
```

### 5. 開発サーバーの起動

```bash
python manage.py runserver
```

## 使い方

### 1. ユーザー登録・ログイン

1. http://127.0.0.1:8000/ にアクセス
2. 「サインアップ」からユーザー登録
3. メール認証を完了
4. ログイン

### 2. ドキュメントのアップロード

1. 「ドキュメント管理」をクリック
2. 「新しいドキュメントをアップロード」をクリック
3. マークダウンファイル（.md）を選択してアップロード
4. 自動的にベクトル化処理が実行されます

### 3. AIチャット

1. 「チャット」をクリック
2. アップロードしたドキュメントに関する質問を入力
3. AIが関連情報を検索して回答を生成

## システム構成

### アプリケーション構成

- `accounts/`: ユーザー認証・管理
- `documents/`: ドキュメントアップロード・管理
- `rag/`: RAG機能・チャット

### RAG処理フロー

1. **ドキュメント処理**:
   - UnstructuredMarkdownLoaderでマークダウンファイルを読み込み
   - テキストクリーニング（不要な改行・空白の除去）
   - 日本語対応のセマンティックチャンク化

2. **ベクトル化**:
   - Google Text Embedding 004でベクトル化
   - ユーザーごとに分離されたChromaDBに保存

3. **検索・回答生成**:
   - HypotheticalDocumentEmbedderで高精度検索
   - Gemini 2.0 Flashで回答生成

### セキュリティ

- ユーザーごとのデータ分離
- ログインユーザーのみアクセス可能
- ファイルタイプ制限（.mdのみ）
- CSRF保護

## API仕様

### チャットAPI

```
POST /rag/api/chat/
Content-Type: application/json

{
    "query": "質問内容"
}
```

レスポンス:
```json
{
    "response": "AI回答",
    "query": "質問内容"
}
```

## 開発

### ディレクトリ構造

```
django_rag_test/
├── accounts/           # ユーザー認証
├── documents/          # ドキュメント管理
├── rag/               # RAG機能
├── templates/         # テンプレート
├── static/           # 静的ファイル
├── config/           # Django設定
├── media/            # アップロードファイル
└── chroma_db/        # ベクトルストア
```

### カスタマイズ

- `rag/services.py`: RAG処理ロジック
- `templates/`: UI テンプレート
- `static/css/style.css`: カスタムスタイル

## トラブルシューティング

### よくある問題

1. **Gemini APIエラー**: `.env`ファイルのAPIキーを確認
2. **ファイルアップロードエラー**: ファイル形式が.mdか確認
3. **チャットで回答が返らない**: ドキュメントが処理済みか確認

### ログ確認

```bash
# Django開発サーバーのログを確認
python manage.py runserver --verbosity=2
```

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 参考資料

- [LangChain Documentation](https://python.langchain.com/)
- [Django Documentation](https://docs.djangoproject.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Google AI Documentation](https://ai.google.dev/)
