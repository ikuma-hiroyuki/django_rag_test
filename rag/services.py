import re
import shutil
from typing import List

import chromadb
from django.conf import settings
from langchain.chains.hyde.base import HypotheticalDocumentEmbedder
from langchain.schema import Document as LangChainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings


class DocumentProcessor:
    """ドキュメント処理クラス"""

    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", google_api_key=settings.GEMINI_API_KEY
        )

    def load_document(self, file_path: str) -> List[LangChainDocument]:
        """マークダウンファイルを読み込み"""
        loader = UnstructuredMarkdownLoader(file_path)
        documents = loader.load()
        return documents

    def clean_text(self, text: str) -> str:
        """テキストの不要な改行や空白をトリミング"""
        # 連続する改行を単一の改行に変換
        text = re.sub(r"\n\s*\n", "\n", text)
        # 行頭・行末の空白を削除
        text = "\n".join(line.strip() for line in text.split("\n"))
        # 連続する空白を単一の空白に変換
        text = re.sub(r" +", " ", text)
        return text.strip()

    def chunk_documents(
        self, documents: List[LangChainDocument], user_id: str, document_id: str
    ) -> List[LangChainDocument]:
        """日本語に特化したセマンティックチャンク化"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", "。", "、", " ", ""],
        )

        chunks = []
        for doc in documents:
            # テキストをクリーニング
            cleaned_text = self.clean_text(doc.page_content)

            # チャンク化
            chunk_docs = text_splitter.create_documents(
                [cleaned_text],
                metadatas=[
                    {
                        **doc.metadata,
                        "user_id": user_id,
                        "document_id": document_id,
                        "source": doc.metadata.get("source", ""),
                    }
                ],
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
            collection_name=f"documents_{user_id}",
        )

        vectorstore.add_documents(chunks)
        return vectorstore

    def delete_document_from_vectorstore(self, user_id: str, document_id: str):
        """ベクトルストアから特定のドキュメントを削除"""
        persist_directory = settings.CHROMA_PERSIST_DIRECTORY / f"user_{user_id}"

        client = chromadb.PersistentClient(path=str(persist_directory))
        collection_name = f"documents_{user_id}"
        collection = client.get_collection(collection_name)

        # 指定されたドキュメントIDのデータを取得
        results = collection.get(where={"document_id": document_id})

        if results["ids"]:
            # 指定されたドキュメントを削除
            collection.delete(ids=results["ids"])

            # 削除後にコレクションが空かどうかを確認
            remaining_data = collection.get()
            if not remaining_data["ids"]:
                # コレクションが空の場合、コレクションを削除
                client.delete_collection(collection_name)

                # コレクションのUUIDディレクトリを削除
                for item in persist_directory.iterdir():
                    if item.is_dir() and len(item.name) == 36:  # UUIDの長さは36文字
                        shutil.rmtree(item)


class RAGService:
    """RAGサービスクラス"""

    def __init__(self):
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004", google_api_key=settings.GEMINI_API_KEY
        )
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0.1,
        )

    def get_retriever(self, user_id: str):
        """ユーザー専用のリトリーバーを取得"""
        persist_directory = settings.CHROMA_PERSIST_DIRECTORY / f"user_{user_id}"

        if not persist_directory.exists():
            # ベクトルストアが存在しない場合はNoneを返す
            return None

        # HypotheticalDocumentEmbedderを作成
        hyde_embeddings = HypotheticalDocumentEmbedder.from_llm(
            llm=self.llm, base_embeddings=self.embeddings, prompt_key="web_search"
        )

        # HyDEエンベディングを使用してベクトルストアを作成
        vectorstore = Chroma(
            persist_directory=str(persist_directory),
            embedding_function=hyde_embeddings,
            collection_name=f"documents_{user_id}",
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
