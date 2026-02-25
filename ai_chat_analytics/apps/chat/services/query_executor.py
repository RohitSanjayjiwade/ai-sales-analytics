import time
import logging
from django.db import connections

logger = logging.getLogger(__name__)

# Maximum rows ever loaded into Python memory per query.
# Even if the SQL has LIMIT 200, this is the absolute ceiling.
HARD_ROW_LIMIT = 200

# SQLite busy timeout (ms) — how long to wait when DB is locked
SQLITE_BUSY_TIMEOUT_MS = 5000


class ExecutionResult:
    def __init__(self, success, columns=None, rows=None, row_count=0, execution_time_ms=0, error=None):
        self.success = success
        self.columns = columns or []
        self.rows = rows or []
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.error = error


class QueryExecutor:
    DB_ALIAS = 'readonly'

    def execute(self, sql):
        start = time.time()
        try:
            conn = connections[self.DB_ALIAS]

            # Set SQLite busy timeout so concurrent requests wait rather than
            # immediately failing with "database is locked".
            if conn.vendor == 'sqlite':
                conn.cursor().execute(
                    "PRAGMA busy_timeout = {}".format(SQLITE_BUSY_TIMEOUT_MS)
                )

            with conn.cursor() as cursor:
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description]

                # Use fetchmany instead of fetchall to avoid loading the entire
                # result set into memory when the query returns a large dataset.
                rows = []
                while len(rows) < HARD_ROW_LIMIT:
                    batch = cursor.fetchmany(HARD_ROW_LIMIT - len(rows))
                    if not batch:
                        break
                    rows.extend(dict(zip(columns, row)) for row in batch)

                elapsed = int((time.time() - start) * 1000)

                logger.debug(
                    "DB QUERY — %d row(s) in %dms | columns: %s",
                    len(rows), elapsed, columns,
                )

                return ExecutionResult(
                    success=True,
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=elapsed,
                )

        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            logger.error("DB QUERY FAILED after %dms — %s", elapsed, str(e))
            return ExecutionResult(
                success=False,
                execution_time_ms=elapsed,
                error=str(e),
            )
