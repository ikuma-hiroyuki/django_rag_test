
document.addEventListener('DOMContentLoaded', function() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('id_file');
    const fileList = document.getElementById('file-list');
    const fileItems = document.getElementById('file-items');
    const uploadBtn = document.getElementById('upload-btn');
    const uploadForm = document.getElementById('upload-form');
    const uploadProgress = document.getElementById('upload-progress');
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.getElementById('progress-text');

    let selectedFiles = [];

    // ドラッグ&ドロップイベント
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#007bff';
        dropZone.style.backgroundColor = '#f8f9fa';
    });

    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#dee2e6';
        dropZone.style.backgroundColor = '';
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#dee2e6';
        dropZone.style.backgroundColor = '';

        const files = Array.from(e.dataTransfer.files);
        handleFiles(files);
    });

    // ファイル選択イベント
    fileInput.addEventListener('change', function(e) {
        const files = Array.from(e.target.files);
        handleFiles(files);
    });

    // ファイル処理関数
    function handleFiles(files) {
        // マークダウンファイルのみフィルタリング
        const mdFiles = files.filter(file => file.name.endsWith('.md'));

        if (mdFiles.length !== files.length) {
            alert('マークダウンファイル(.md)のみアップロード可能です。');
        }

        selectedFiles = mdFiles;
        updateFileList();
        updateUploadButton();
    }

    // ファイル一覧更新
    function updateFileList() {
        if (selectedFiles.length === 0) {
            fileList.style.display = 'none';
            return;
        }

        fileList.style.display = 'block';
        fileItems.innerHTML = '';

        selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'alert alert-light d-flex justify-content-between align-items-center py-2';
            fileItem.innerHTML = `
                <span><i class="fas fa-file-alt me-2"></i>${file.name}</span>
                <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFile(${index})">
                    <i class="fas fa-times"></i>
                </button>
            `;
            fileItems.appendChild(fileItem);
        });
    }

    // ファイル削除
    window.removeFile = function(index) {
        selectedFiles.splice(index, 1);
        updateFileList();
        updateUploadButton();
    };

    // アップロードボタン状態更新
    function updateUploadButton() {
        uploadBtn.disabled = selectedFiles.length === 0;
    }

    // フォーム送信処理
    uploadForm.addEventListener('submit', function(e) {
        e.preventDefault();

        if (selectedFiles.length === 0) {
            alert('ファイルを選択してください。');
            return;
        }

        // プログレスバー表示
        uploadProgress.style.display = 'block';
        uploadBtn.disabled = true;

        // FormDataを作成
        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', document.querySelector('[name=csrfmiddlewaretoken]').value);

        selectedFiles.forEach(file => {
            formData.append('file', file);
        });

        // XMLHttpRequestでアップロード
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', function(e) {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressBar.style.width = percentComplete + '%';
                progressText.textContent = `アップロード中... ${Math.round(percentComplete)}%`;
            }
        });

        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                progressText.textContent = '処理中...';
                // ページをリロードして結果を表示
                window.location.reload();
            } else {
                alert('アップロードに失敗しました。');
                uploadProgress.style.display = 'none';
                uploadBtn.disabled = false;
            }
        });

        xhr.addEventListener('error', function() {
            alert('アップロードエラーが発生しました。');
            uploadProgress.style.display = 'none';
            uploadBtn.disabled = false;
        });

        xhr.open('POST', uploadForm.action);
        xhr.send(formData);
    });
});
