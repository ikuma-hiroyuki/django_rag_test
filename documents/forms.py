from django import forms
from .models import Document


class DocumentUploadForm(forms.ModelForm):
    """ドキュメントアップロードフォーム"""

    class Meta:
        model = Document
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.md'
            })
        }

    def clean_file(self):
        """ファイルのバリデーション"""
        file = self.cleaned_data.get('file')
        if file:
            if not file.name.endswith('.md'):
                raise forms.ValidationError('マークダウンファイル(.md)のみアップロード可能です。')
        return file
