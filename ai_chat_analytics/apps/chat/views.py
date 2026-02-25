import json
import logging
from decimal import Decimal
from datetime import datetime, date
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view
from openai import OpenAI
from django.conf import settings
from .models import ChatSession, ChatMessage, QueryAuditLog
from .services.agent import ChatAgent
from .services.schema_extractor import SchemaExtractor
from .services.sql_validator import SQLValidator
from .services.query_executor import QueryExecutor
from .services.business_context import BUSINESS_CONTEXT

logger = logging.getLogger(__name__)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


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

        # Get or create session
        if session_id:
            session = ChatSession.objects.filter(id=session_id).first()
            if not session:
                return Response({'error': 'Session not found'}, status=404)
        else:
            session = ChatSession.objects.create(title=question[:100])

        logger.info("SESSION  — id: %s", session.id)

        # Save user message
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=question,
        )

        # Run agent
        agent = ChatAgent()
        result = agent.run(user_question=question)
        logger.info("RESPONSE — success: %s | rows: %d", result.success, result.row_count)

        # Audit log
        QueryAuditLog.objects.create(
            session=session,
            user_question=question,
            generated_sql=result.sql_used or '',
            row_count=result.row_count,
            error=result.error,
        )

        # Save AI response
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=result.response,
            status=ChatMessage.Status.SUCCESS if result.success else ChatMessage.Status.FAILED,
        )

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

    def event_stream():
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        schema_extractor = SchemaExtractor()
        validator = SQLValidator()
        executor = QueryExecutor()

        # Step 1 — decide: does this question need a database query?
        yield "data: {}\n\n".format(json.dumps({'type': 'status', 'message': 'Analyzing your question...'}))

        schema = schema_extractor.get_schema()
        agent = ChatAgent()
        datetime_context = agent._get_datetime_context()

        system_sql = """You are an SQL expert for a business analytics assistant.

TASK:
- If the user's message is a greeting, acknowledgment ("ok", "yes", "no", "thanks", "great", "got it", "sure", "bye", etc.) or general small talk that does NOT need database data — return exactly: NO_QUERY
- Otherwise, generate a single SQL SELECT query using the schema below.

LIMIT RULES (strictly follow):
- Aggregation queries (SUM, COUNT, AVG, MAX, MIN, GROUP BY): NO LIMIT clause needed.
- Listing / detail queries (SELECT columns or SELECT *): use LIMIT 50.
- Top-N queries where user specifies a number (e.g. "top 5", "show 100"): use that exact number, but never exceed 200.
- If user says "show all" or "all records": use LIMIT 50 and mention total count separately using COUNT(*).
- Never use arbitrary large limits like 500, 1000, etc.

DATABASE SCHEMA:
{schema}

{datetime_context}

{context}

Return ONLY the raw SQL query or the text NO_QUERY. No explanation. No markdown.""".format(
            schema=schema, datetime_context=datetime_context, context=BUSINESS_CONTEXT
        )

        sql_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_sql},
                {"role": "user", "content": question},
            ],
            temperature=0,
            max_tokens=512,
        )
        sql = sql_response.choices[0].message.content.strip()

        # ── Conversational path (no DB needed) ──────────────────────────────
        if sql.upper().startswith('NO_QUERY'):
            yield "data: {}\n\n".format(json.dumps({'type': 'status', 'message': 'Responding...'}))

            full_response = []
            conv_stream = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a friendly business analytics assistant. "
                            "The user sent a conversational message — reply naturally and briefly. "
                            "Do not query any data or mention SQL."
                        ),
                    },
                    {"role": "user", "content": question},
                ],
                stream=True,
                max_tokens=256,
            )
            for chunk in conv_stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    full_response.append(delta)
                    yield "data: {}\n\n".format(json.dumps({'type': 'chunk', 'content': delta}))

            final_text = ''.join(full_response)
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content=final_text,
                status=ChatMessage.Status.SUCCESS,
            )
            yield "data: {}\n\n".format(json.dumps({
                'type': 'done',
                'session_id': str(session.id),
                'row_count': 0,
            }))
            return

        # ── Data query path ──────────────────────────────────────────────────
        sql_used = sql
        row_count = 0

        validation = validator.validate(sql)
        if not validation.is_valid:
            yield "data: {}\n\n".format(json.dumps({'type': 'error', 'message': 'Could not generate a valid query.'}))
            return

        yield "data: {}\n\n".format(json.dumps({'type': 'sql', 'query': validation.sanitized_sql}))

        # Step 2 — execute query
        yield "data: {}\n\n".format(json.dumps({'type': 'status', 'message': 'Fetching data...'}))

        result = executor.execute(validation.sanitized_sql)
        if not result.success:
            logger.warning("STREAM QUERY FAILED — %s", result.error)
            QueryAuditLog.objects.create(
                session=session, user_question=question,
                generated_sql=sql_used or '', error=result.error,
            )
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content="Sorry, I couldn't retrieve the data. Please try rephrasing your question.",
                status=ChatMessage.Status.FAILED,
            )
            yield "data: {}\n\n".format(json.dumps({
                'type': 'error',
                'message': 'Query execution failed: {}'.format(result.error or 'unknown error'),
            }))
            return

        row_count = result.row_count

        QueryAuditLog.objects.create(
            session=session,
            user_question=question,
            generated_sql=sql_used or '',
            row_count=row_count,
            execution_time_ms=result.execution_time_ms,
        )

        # Step 3 — stream final response
        yield "data: {}\n\n".format(json.dumps({'type': 'status', 'message': 'Preparing response...'}))

        data_json = json.dumps(result.rows, cls=DecimalEncoder)  # executor already caps at HARD_ROW_LIMIT
        full_response = []

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": "You are a business intelligence assistant. Convert raw DB results into clear, friendly business responses. Format currency with $. Be concise."
                },
                {
                    "role": "user",
                    "content": "User asked: {}\n\nQuery returned {} rows:\n{}".format(question, row_count, data_json)
                }
            ],
            stream=True,
            max_tokens=1024,
        )

        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                full_response.append(delta)
                yield "data: {}\n\n".format(json.dumps({'type': 'chunk', 'content': delta}))

        # Save full response to DB
        final_text = ''.join(full_response)
        ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=final_text,
            status=ChatMessage.Status.SUCCESS,
        )

        yield "data: {}\n\n".format(json.dumps({
            'type': 'done',
            'session_id': str(session.id),
            'row_count': row_count,
        }))

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
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

        # Return last 100 messages — include id so frontend can use it as React key
        messages = (
            session.messages
            .values('id', 'role', 'content', 'status', 'created_at')
            .order_by('created_at')[:100]
        )
        return Response({
            'session_id': str(session.id),
            'title': session.title,
            'messages': [
                {**msg, 'id': str(msg['id'])}   # cast int pk → string to match frontend type
                for msg in messages
            ],
        })
