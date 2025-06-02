import re
from typing import List
import logging
import chromadb
import shutil

from django.conf import settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain.schema import Document as LangChainDocument
from langchain.chains.hyde.base import HypotheticalDocumentEmbedder


class DocumentProcessor:
    """ドキュメント処理クラス"""

    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.GEMINI_API_KEY
        )

    def load_document(self, file_path: str) -> List[LangChainDocument]:
        """マークダウンファイルを読み込み"""
        loader = UnstructuredMarkdownLoader(file_path)
        documents = loader.load()
        return documents

    def clean_text(self, text: str) -> str:
        """テキストの不要な改行や空白をトリミング"""
        # 連続する改行を単一の改行に変換
        text = re.sub(r'\n\s*\n', '\n', text)
        # 行頭・行末の空白を削除
        text = '\n'.join(line.strip() for line in text.split('\n'))
        # 連続する空白を単一の空白に変換
        text = re.sub(r' +', ' ', text)
        return text.strip()

    def chunk_documents(self, documents: List[LangChainDocument], user_id: str, document_id: str) -> List[LangChainDocument]:
        """日本語に特化したセマンティックチャンク化"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", "。", "、", " ", ""]
        )

        chunks = []
        for doc in documents:
            # テキストをクリーニング
            cleaned_text = self.clean_text(doc.page_content)

            # チャンク化
            chunk_docs = text_splitter.create_documents(
                [cleaned_text],
                metadatas=[{
                    **doc.metadata,
                    'user_id': user_id,
                    'document_id': document_id,
                    'source': doc.metadata.get('source', '')
                }]
            )
            chunks.extend(chunk_docs)

        return chunks

    def store_documents(self, chunks: List[LangChainDocument], user_id: str):
        """ベクトルストアにドキュメントを保存"""
        persist_directory = settings.CHROMA_PERSIST_DIRECTORY / f"user_{user_id}"
        persist_directory.mkdir(parents=True, exist_ok=True)

        vectorstore = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=self.embeddings,
            collection_name=f"documents_{user_id}"
        )

        vectorstore.add_documents(chunks)
        return vectorstore

    def delete_document_from_vectorstore(self, user_id: str, document_id: str):
        """ベクトルストアから特定のドキュメントを削除"""
        logger = logging.getLogger(__name__)

        print(f"削除処理開始: user_id={user_id}, document_id={document_id}")

        persist_directory = settings.CHROMA_PERSIST_DIRECTORY / f"user_{user_id}"

        if not persist_directory.exists():
            print(f"ベクトルストアディレクトリが存在しません: {persist_directory}")
            logger.warning(f"ベクトルストアディレクトリが存在しません: {persist_directory}")
            return

        try:
            print("ChromaDBクライアントを作成中...")
            # ChromaDBクライアントを直接使用
            client = chromadb.PersistentClient(path=str(persist_directory))
            collection_name = f"documents_{user_id}"

            try:
                print(f"コレクション取得中: {collection_name}")
                collection = client.get_collection(collection_name)
            except Exception as e:
                print(f"コレクションが見つかりません: {collection_name} - {str(e)}")
                logger.warning(f"コレクションが見つかりません: {collection_name} - {str(e)}")
                return

            # 削除前の状態を確認
            all_results = collection.get()
            print(f"削除前のドキュメント数: {len(all_results['ids'])}")
            logger.info(f"削除前のドキュメント数: {len(all_results['ids'])}")

            # メタデータでフィルタリングして対象を取得
            results = collection.get(where={"document_id": document_id})
            print(f"削除対象のドキュメント数: {len(results['ids'])}")
            logger.info(f"削除対象のドキュメント数: {len(results['ids'])}")

            if results['ids']:
                print(f"削除するID: {results['ids']}")
                logger.info(f"削除するID: {results['ids']}")
                # 削除実行
                collection.delete(ids=results['ids'])

                # 削除後の状態を確認
                after_results = collection.get()
                print(f"削除後のドキュメント数: {len(after_results['ids'])}")
                logger.info(f"削除後のドキュメント数: {len(after_results['ids'])}")

                # 削除が成功したかを確認
                remaining = collection.get(where={"document_id": document_id})
                if remaining['ids']:
                    print(f"警告: 削除後もドキュメントが残っています: {remaining['ids']}")
                    logger.error(f"警告: 削除後もドキュメントが残っています: {remaining['ids']}")
                    raise Exception(f"ドキュメントの削除が完了しませんでした: {document_id}")
                else:
                    print("ベクトルストアからの削除が正常に完了しました")
                    logger.info("ベクトルストアからの削除が正常に完了しました")
            else:
                print(f"削除対象のドキュメントが見つかりませんでした: document_id={document_id}")
                logger.warning(f"削除対象のドキュメントが見つかりませんでした: document_id={document_id}")

                # デバッグ: 全てのメタデータを確認
                if all_results['metadatas']:
                    print("既存のメタデータ:")
                    logger.debug("既存のメタデータ:")
                    for i, metadata in enumerate(all_results['metadatas'][:3]):  # 最初の3件のみ表示
                        print(f"  {i + 1}: {metadata}")
                        logger.debug(f"  {i + 1}: {metadata}")
                else:
                    # コレクションが空の場合は、ディレクトリ全体を削除
                    print("コレクションが空のため、ディレクトリ全体を削除します")
                    logger.info("コレクションが空のため、ディレクトリ全体を削除します")
                    client.delete_collection(collection_name)
                    if persist_directory.exists():
                        shutil.rmtree(persist_directory)
                        print("ベクトルストアディレクトリを削除しました")
                        logger.info("ベクトルストアディレクトリを削除しました")

        except Exception as e:
            print(f"ベクトルストアからの削除中にエラーが発生しました: {str(e)}")
            logger.error(f"ベクトルストアからの削除中にエラーが発生しました: {str(e)}")
            # エラーが発生した場合でも、ディレクトリが存在し、空の場合は削除を試行
            try:
                if persist_directory.exists():
                    client = chromadb.PersistentClient(path=str(persist_directory))
                    collection_name = f"documents_{user_id}"
                    try:
                        collection = client.get_collection(collection_name)
                        results = collection.get()
                        if len(results['ids']) == 0:
                            client.delete_collection(collection_name)
                            shutil.rmtree(persist_directory)
                            print("エラー後のクリーンアップでディレクトリを削除しました")
                            logger.info("エラー後のクリーンアップでディレクトリを削除しました")
                    except Exception:
                        pass
            except Exception:
                pass
            raise e


class RAGService:
    """RAGサービスクラス"""

    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=settings.GEMINI_API_KEY
        )
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.1
        )

    def get_retriever(self, user_id: str):
        """ユーザー専用のリトリーバーを取得"""
        persist_directory = settings.CHROMA_PERSIST_DIRECTORY / f"user_{user_id}"

        if not persist_directory.exists():
            # ベクトルストアが存在しない場合はNoneを返す
            return None

        # HypotheticalDocumentEmbedderを作成
        hyde_embeddings = HypotheticalDocumentEmbedder.from_llm(
            llm=self.llm,
            base_embeddings=self.embeddings,
            prompt_key="web_search"
        )

        # HyDEエンベディングを使用してベクトルストアを作成
        vectorstore = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=hyde_embeddings,
            collection_name=f"documents_{user_id}"
        )

        # 標準のリトリーバーを返す
        return vectorstore.as_retriever(search_kwargs={"k": 5})

    def generate_response(self, query: str, user_id: str) -> str:
        """RAGを使用して回答を生成"""
        retriever = self.get_retriever(user_id)

        if not retriever:
            return "アップロードされたドキュメントがありません。まずドキュメントをアップロードしてください。"

        try:
            relevant_docs = retriever.invoke(query)

            if not relevant_docs:
                return "関連する情報が見つかりませんでした。"

            # コンテキストを構築
            context = "\n\n".join([doc.page_content for doc in relevant_docs])

            # プロンプトを構築
            prompt = f"""
以下のコンテキストに基づいて、ユーザーの質問に回答してください。
コンテキストに含まれていない情報については、「アップロードされたドキュメントでは回答できません」と答えてください。

コンテキスト:
{context}

質問: {query}

回答:"""

            # LLMで回答を生成
            response = self.llm.invoke(prompt)
            return response.content

        except Exception as e:
            return f"回答の生成中にエラーが発生しました: {str(e)}"
