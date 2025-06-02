from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

from .services import RAGService


@login_required
def chat_view(request):
    """チャット画面"""
    return render(request, 'rag/chat.html')


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    """チャットAPI"""
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()

        if not query:
            return JsonResponse({'error': '質問を入力してください。'}, status=400)

        # RAGサービスで回答を生成
        rag_service = RAGService()
        response = rag_service.generate_response(query, str(request.user.id))

        return JsonResponse({
            'response': response,
            'query': query
        })

    except json.JSONDecodeError:
        return JsonResponse({'error': '無効なJSONデータです。'}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'エラーが発生しました: {str(e)}'}, status=500)
