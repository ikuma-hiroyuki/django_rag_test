import uuid
import os
from django.db import models
from django.conf import settings


def document_upload_path(instance, filename):
    """ドキュメントのアップロードパスを生成"""
    return f'documents/{instance.user.id}/{filename}'


class Document(models.Model):
    """ドキュメントモデル"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255, verbose_name='タイトル')
    file = models.FileField(upload_to=document_upload_path, verbose_name='ファイル')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='アップロード日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')
    is_processed = models.BooleanField(default=False, verbose_name='処理済み')

    class Meta:
        verbose_name = 'ドキュメント'
        verbose_name_plural = 'ドキュメント'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        """ドキュメント削除時にファイルも削除"""
        if self.file:
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        super().delete(*args, **kwargs)
