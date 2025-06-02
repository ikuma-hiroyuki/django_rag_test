from django.views.generic import ListView, CreateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages

from .models import Document
from .forms import DocumentUploadForm
from rag.services import DocumentProcessor


class DocumentListView(LoginRequiredMixin, ListView):
    """ドキュメント一覧ビュー"""
    model = Document
    template_name = 'documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 10

    def get_queryset(self):
        """ログインユーザーのドキュメントのみ取得"""
        return Document.objects.filter(user=self.request.user)


class DocumentUploadView(LoginRequiredMixin, CreateView):
    """ドキュメントアップロードビュー"""
    model = Document
    form_class = DocumentUploadForm
    template_name = 'documents/document_upload.html'
    success_url = reverse_lazy('documents:list')

    def post(self, request, *args, **kwargs):
        """複数ファイルアップロードに対応したPOST処理"""
        files = request.FILES.getlist('file')

        if not files:
            messages.error(request, 'ファイルが選択されていません。')
            return self.get(request, *args, **kwargs)

        success_count = 0
        error_count = 0
        skipped_count = 0

        for file in files:
            # ファイルのバリデーション
            if not file.name.endswith('.md'):
                messages.error(request, f'{file.name}: マークダウンファイル(.md)のみアップロード可能です。')
                error_count += 1
                continue

            # 同じファイル名のドキュメントが既に存在するかチェック
            if Document.objects.filter(user=request.user, title=file.name).exists():
                messages.warning(request, f'{file.name}: 同じファイル名のドキュメントが既に存在します。処理をスキップしました。')
                skipped_count += 1
                continue

            try:
                # ドキュメントオブジェクトを作成
                document = Document.objects.create(
                    user=request.user,
                    title=file.name,
                    file=file
                )

                # ドキュメントを処理してベクトルストアに保存
                processor = DocumentProcessor()

                # ドキュメントを読み込み
                documents = processor.load_document(document.file.path)

                # チャンク化
                chunks = processor.chunk_documents(
                    documents,
                    str(request.user.id),
                    str(document.id)
                )

                # ベクトルストアに保存
                processor.store_documents(chunks, str(request.user.id))

                # 処理完了フラグを設定
                document.is_processed = True
                document.save()

                success_count += 1

            except Exception as e:
                error_count += 1
                print(e)
                messages.error(request, f'{file.name}: 処理中にエラーが発生しました - {str(e)}')

        # 結果メッセージ
        if success_count > 0:
            messages.success(request, f'{success_count}個のドキュメントが正常にアップロードされ、処理が完了しました。')

        if skipped_count > 0:
            messages.info(request, f'{skipped_count}個のファイルは既に存在するためスキップされました。')

        if error_count > 0:
            messages.warning(request, f'{error_count}個のファイルでエラーが発生しました。')

        return self.get(request, *args, **kwargs)


class DocumentDeleteView(LoginRequiredMixin, DeleteView):
    """ドキュメント削除ビュー"""
    model = Document
    template_name = 'documents/document_list.html'
    success_url = reverse_lazy('documents:list')

    def get_queryset(self):
        """ログインユーザーのドキュメントのみ削除可能"""
        return Document.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        """削除処理（POSTリクエスト対応）"""
        self.object = self.get_object()

        # ベクトルストアからも削除
        try:
            processor = DocumentProcessor()
            processor.delete_document_from_vectorstore(
                str(self.request.user.id),
                str(self.object.id)
            )
        except Exception as e:
            messages.error(request, f'ベクトルストアからの削除中にエラーが発生しました: {str(e)}')

        messages.success(request, 'ドキュメントが削除されました。')
        return super().delete(request, *args, **kwargs)
