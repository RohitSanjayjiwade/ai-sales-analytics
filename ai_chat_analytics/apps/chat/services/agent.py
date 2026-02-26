import json
import logging
from decimal import Decimal
from datetime import datetime, date
from openai import OpenAI
from django.conf import settings
from .schema_extractor import SchemaExtractor
from .sql_validator import SQLValidator
from .query_executor import QueryExecutor
from .business_context import BUSINESS_CONTEXT
from ..models import ChatMessage, QueryAuditLog

logger = logging.getLogger(__name__)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "execute_sql",
            "description": "Execute a SQL SELECT query against the business database to retrieve data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A valid SQL SELECT query. Must start with SELECT. No INSERT/UPDATE/DELETE allowed."
                    }
                },
                "required": ["sql"]
            }
        }
    }
]


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


class AgentResult:
    def __init__(self, success, response, sql_used=None, row_count=0, error=None):
        self.success = success
        self.response = response
        self.sql_used = sql_used
        self.row_count = row_count
        self.error = error


class ChatAgent:
    MAX_TOOL_ITERATIONS = 5

    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.schema_extractor = SchemaExtractor()
        self.validator = SQLValidator()
        self.executor = QueryExecutor()

    def _get_datetime_context(self):
        """
        Auto-generate datetime context from Django settings.
        Detects DB engine (SQLite vs PostgreSQL) and generates correct SQL syntax.
        No manual rules needed — works for any timezone, any DB.
        """
        from django.utils import timezone as tz
        from django.db import connection

        now_local = tz.localtime(tz.now())
        today_str  = now_local.strftime('%Y-%m-%d')
        now_str    = now_local.strftime('%Y-%m-%d %H:%M:%S')
        month_str  = today_str[:7]
        tz_name    = str(now_local.tzinfo)  # e.g. Asia/Kolkata

        db_engine = connection.vendor  # 'sqlite' or 'postgresql' or 'mysql'

        if db_engine == 'sqlite':
            offset         = now_local.utcoffset()
            offset_minutes = int(offset.total_seconds() / 60)
            sign           = '+' if offset_minutes >= 0 else '-'
            offset_str     = "'{}{} minutes'".format(sign, abs(offset_minutes))

            convert    = "datetime(column, {})".format(offset_str)
            today_cond = "DATE(datetime(column, {})) = '{}'".format(offset_str, today_str)
            week_cond  = "datetime(column, {}) >= datetime('now', '-6 days', {})".format(offset_str, offset_str)
            month_cond = "strftime('%Y-%m', datetime(column, {})) = '{}'".format(offset_str, month_str)

        else:  # postgresql
            convert    = "column AT TIME ZONE 'UTC' AT TIME ZONE '{}'".format(tz_name)
            today_cond = "(column AT TIME ZONE 'UTC' AT TIME ZONE '{}')::date = '{}'".format(tz_name, today_str)
            week_cond  = "(column AT TIME ZONE 'UTC' AT TIME ZONE '{}')::date >= '{}'::date - INTERVAL '6 days'".format(tz_name, today_str)
            month_cond = "to_char(column AT TIME ZONE 'UTC' AT TIME ZONE '{}', 'YYYY-MM') = '{}'".format(tz_name, month_str)

        logger.debug("DATETIME CONTEXT — db: %s | tz: %s | today: %s", db_engine, tz_name, today_str)

        return """
CURRENT DATE & TIME (auto-injected from server):
- Today's date : {today}
- Current time : {now}
- Timezone     : {tz}
- Database     : {db}
- DB stores datetimes in UTC — always convert before date comparisons

HOW TO HANDLE DATES in SQL (replace 'column' with actual column name):
- Convert to local time : {convert}
- Filter for today      : {today_cond}
- Filter for this week  : {week_cond}
- Filter for this month : {month_cond}
""".format(
            today=today_str,
            now=now_str,
            tz=tz_name,
            db=db_engine,
            convert=convert,
            today_cond=today_cond,
            week_cond=week_cond,
            month_cond=month_cond,
        )

    def _build_system_prompt(self):
        schema = self.schema_extractor.get_schema()
        datetime_context = self._get_datetime_context()
        return """You are a business intelligence assistant with access to a database.
Use the execute_sql tool to fetch data when answering questions.

DATABASE SCHEMA:
{schema}

{datetime_context}

{context}

RULES:
- Always call execute_sql before answering data questions
- Only write SELECT queries
- After getting data, respond clearly and concisely
- Format currency values nicely using the ₹ symbol (e.g. ₹1,234.56) — never use $
- If no data found, say so clearly

MULTI-PART QUESTIONS:
- If a question has multiple parts, call execute_sql SEPARATELY for each part
- Never assume or hardcode values — always query to find them dynamically
- Example: "which day had most cancellations" → run a query to find that day first, then use the result in the next query

LIMIT RULES (strictly follow):
- Aggregation queries (SUM, COUNT, AVG, MAX, MIN, GROUP BY): NO LIMIT clause needed
- Listing / detail queries (SELECT columns or SELECT *): use LIMIT 50
- Top-N queries where user specifies a number (e.g. "top 5", "show 100"): use that exact number, never exceed 200
- If user says "show all" or "all records": use LIMIT 50 and mention total count separately using COUNT(*)
- Never use arbitrary large limits like 500, 1000, etc""".format(
            schema=schema,
            datetime_context=datetime_context,
            context=BUSINESS_CONTEXT,
        )

    # ─────────────────────────────────────────
    #  Non-streaming run
    # ─────────────────────────────────────────
    def run(self, user_question, session=None):
        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": user_question},
        ]

        sql_used = None
        row_count = 0
        iterations = 0

        logger.info("━" * 60)
        logger.info("USER QUESTION : %s", user_question)
        logger.info("━" * 60)

        try:
            while iterations < self.MAX_TOOL_ITERATIONS:
                iterations += 1

                logger.debug("── Calling OpenAI (iteration %d) ──", iterations)

                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="required" if iterations == 1 else "auto",
                    temperature=0,
                    max_tokens=1024,
                )

                choice = response.choices[0]
                logger.debug("OpenAI finish_reason : %s", choice.finish_reason)

                messages.append(choice.message)

                if choice.finish_reason == "tool_calls":
                    for tool_call in choice.message.tool_calls:
                        if tool_call.function.name == "execute_sql":
                            args = json.loads(tool_call.function.arguments)
                            sql = args.get("sql", "")
                            sql_used = sql

                            logger.info("── STEP 1: AI Generated SQL ──")
                            logger.info("%s", sql)

                            validation = self.validator.validate(sql)
                            if not validation.is_valid:
                                tool_result = "Validation error: {}. Please fix the SQL.".format(validation.error)
                                logger.warning("── STEP 2: VALIDATION FAILED — %s", validation.error)
                                if session:
                                    QueryAuditLog.objects.create(
                                        session=session,
                                        user_question=user_question,
                                        generated_sql=sql,
                                        error=validation.error,
                                    )
                            else:
                                logger.info("── STEP 2: SQL Validated OK ──")

                                result = self.executor.execute(validation.sanitized_sql)
                                if result.success:
                                    row_count = result.row_count
                                    tool_result = json.dumps(result.rows, cls=DecimalEncoder)
                                    logger.info("── STEP 3: DB RETURNED %d row(s) in %dms ──", result.row_count, result.execution_time_ms)
                                    logger.debug("RAW DATA : %s", result.rows)
                                    if session:
                                        QueryAuditLog.objects.create(
                                            session=session,
                                            user_question=user_question,
                                            generated_sql=validation.sanitized_sql,
                                            row_count=result.row_count,
                                            execution_time_ms=result.execution_time_ms,
                                        )
                                else:
                                    tool_result = "Query execution error: {}. Please fix the SQL.".format(result.error)
                                    logger.warning("── STEP 3: DB QUERY FAILED — %s", result.error)
                                    if session:
                                        QueryAuditLog.objects.create(
                                            session=session,
                                            user_question=user_question,
                                            generated_sql=validation.sanitized_sql,
                                            error=result.error,
                                        )

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result,
                            })
                            logger.debug("── DB result sent back to OpenAI ──")

                elif choice.finish_reason == "stop":
                    final_text = choice.message.content
                    logger.info("── STEP 4: FINAL RESPONSE ──")
                    logger.info("%s", final_text)
                    logger.info("━" * 60)

                    if session:
                        ChatMessage.objects.create(
                            session=session,
                            role=ChatMessage.Role.ASSISTANT,
                            content=final_text,
                            status=ChatMessage.Status.SUCCESS,
                        )

                    return AgentResult(
                        success=True,
                        response=final_text,
                        sql_used=sql_used,
                        row_count=row_count,
                    )

                else:
                    break

        except Exception as e:
            logger.exception("Agent error: %s", str(e))
            if session:
                ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.Role.ASSISTANT,
                    content="Service error: {}".format(str(e)),
                    status=ChatMessage.Status.FAILED,
                )
            return AgentResult(
                success=False,
                response="Service error: {}".format(str(e)),
                error=str(e),
            )

        if session:
            ChatMessage.objects.create(
                session=session,
                role=ChatMessage.Role.ASSISTANT,
                content="Sorry, I could not process your question. Please try rephrasing it.",
                status=ChatMessage.Status.FAILED,
            )
        return AgentResult(
            success=False,
            response="Sorry, I could not process your question. Please try rephrasing it.",
            error="Max iterations reached or unexpected finish reason",
        )

    # ─────────────────────────────────────────
    #  Streaming run (SSE generator)
    # ─────────────────────────────────────────
    def stream_run(self, question, session):
        """Yields SSE-formatted strings. Contains all streaming business logic."""

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": question},
        ]

        row_count = 0
        iterations = 0

        yield "data: {}\n\n".format(json.dumps({'type': 'status', 'message': 'Analyzing your question...'}))

        try:
            while iterations < self.MAX_TOOL_ITERATIONS:
                iterations += 1

                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages,
                    tools=TOOLS,
                    tool_choice="required" if iterations == 1 else "auto",
                    temperature=0,
                    max_tokens=1024,
                )

                choice = response.choices[0]

                # ── Tool call — execute SQL and feed result back ──────────────
                if choice.finish_reason == "tool_calls":
                    messages.append(choice.message)

                    for tool_call in choice.message.tool_calls:
                        if tool_call.function.name == "execute_sql":
                            args = json.loads(tool_call.function.arguments)
                            sql = args.get("sql", "")

                            logger.info("STREAM AGENT — SQL (iteration %d): %s", iterations, sql)
                            yield "data: {}\n\n".format(json.dumps({'type': 'sql', 'query': sql}))
                            yield "data: {}\n\n".format(json.dumps({'type': 'status', 'message': 'Fetching data...'}))

                            validation = self.validator.validate(sql)
                            if not validation.is_valid:
                                tool_result = "Validation error: {}. Please fix the SQL.".format(validation.error)
                                logger.warning("STREAM AGENT — Validation failed: %s", validation.error)
                                QueryAuditLog.objects.create(
                                    session=session,
                                    user_question=question,
                                    generated_sql=sql,
                                    error=validation.error,
                                )
                            else:
                                result = self.executor.execute(validation.sanitized_sql)
                                if result.success:
                                    row_count = result.row_count
                                    tool_result = json.dumps(result.rows, cls=DecimalEncoder)
                                    logger.info("STREAM AGENT — DB returned %d rows in %dms", result.row_count, result.execution_time_ms)
                                    QueryAuditLog.objects.create(
                                        session=session,
                                        user_question=question,
                                        generated_sql=validation.sanitized_sql,
                                        row_count=result.row_count,
                                        execution_time_ms=result.execution_time_ms,
                                    )
                                else:
                                    tool_result = "Query execution error: {}. Please fix the SQL.".format(result.error)
                                    logger.warning("STREAM AGENT — Query failed: %s", result.error)
                                    QueryAuditLog.objects.create(
                                        session=session,
                                        user_question=question,
                                        generated_sql=validation.sanitized_sql,
                                        error=result.error,
                                    )

                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_result,
                            })

                # ── Final answer — re-request with streaming for live typing ──
                elif choice.finish_reason == "stop":
                    yield "data: {}\n\n".format(json.dumps({'type': 'status', 'message': 'Preparing response...'}))

                    full_response = []
                    stream = self.client.chat.completions.create(
                        model="gpt-4o",
                        messages=messages,
                        stream=True,
                        temperature=0,
                        max_tokens=1024,
                    )

                    for chunk in stream:
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
                        'row_count': row_count,
                    }))
                    return

                else:
                    break

        except Exception as e:
            logger.exception("Stream agent error: %s", str(e))
            yield "data: {}\n\n".format(json.dumps({'type': 'error', 'message': 'Service error: {}'.format(str(e))}))
            return

        yield "data: {}\n\n".format(json.dumps({'type': 'error', 'message': 'Could not process your question. Please try rephrasing it.'}))
