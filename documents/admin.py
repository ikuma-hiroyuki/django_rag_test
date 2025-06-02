from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """ドキュメントの管理画面"""
    list_display = ('title', 'user', 'uploaded_at', 'is_processed')
    list_filter = ('is_processed', 'uploaded_at')
    search_fields = ('title', 'user__email')
    readonly_fields = ('uploaded_at', 'updated_at')
    ordering = ('-uploaded_at',)
