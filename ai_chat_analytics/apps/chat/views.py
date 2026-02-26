import logging
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import ChatSession, ChatMessage
from .services.agent import ChatAgent

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────
#  Standard (non-streaming) chat endpoint
# ─────────────────────────────────────────
class ChatMessageView(APIView):

    def post(self, request):
        question = request.data.get('message', '').strip()
        session_id = request.data.get('session_id')

        if not question:
            return Response({'error': 'message is required'}, status=400)

        logger.info("REQUEST  — session: %s | question: %s", session_id or "new", question)

        if session_id:
            session = ChatSession.objects.filter(id=session_id).first()
            if not session:
                return Response({'error': 'Session not found'}, status=404)
        else:
            session = ChatSession.objects.create(title=question[:100])

        logger.info("SESSION  — id: %s", session.id)

        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=question,
        )

        result = ChatAgent().run(user_question=question, session=session)
        logger.info("RESPONSE — success: %s | rows: %d", result.success, result.row_count)

        return Response({
            'session_id': str(session.id),
            'response': result.response,
            'metadata': {
                'row_count': result.row_count,
                'success': result.success,
            }
        })


# ─────────────────────────────────────────
#  Streaming chat endpoint (SSE)
# ─────────────────────────────────────────
@api_view(['POST'])
def chat_stream(request):
    question = request.data.get('message', '').strip()
    session_id = request.data.get('session_id')

    if not question:
        return Response({'error': 'message is required'}, status=400)

    if session_id:
        session = ChatSession.objects.filter(id=session_id).first()
        if not session:
            return Response({'error': 'Session not found'}, status=404)
    else:
        session = ChatSession.objects.create(title=question[:100])

    ChatMessage.objects.create(
        session=session,
        role=ChatMessage.Role.USER,
        content=question,
    )

    response = StreamingHttpResponse(
        ChatAgent().stream_run(question, session),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


# ─────────────────────────────────────────
#  Session history
# ─────────────────────────────────────────
class SessionHistoryView(APIView):

    def get(self, request, session_id):
        session = ChatSession.objects.filter(id=session_id).first()
        if not session:
            return Response({'error': 'Session not found'}, status=404)

        messages = (
            session.messages
            .values('id', 'role', 'content', 'status', 'created_at')
            .order_by('created_at')[:100]
        )
        return Response({
            'session_id': str(session.id),
            'title': session.title,
            'messages': [
                {**msg, 'id': str(msg['id'])}
                for msg in messages
            ],
        })
