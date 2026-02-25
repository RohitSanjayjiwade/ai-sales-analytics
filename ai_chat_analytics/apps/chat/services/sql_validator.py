import re

DANGEROUS_KEYWORDS = {
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
    'TRUNCATE', 'EXEC', 'EXECUTE', 'GRANT', 'REVOKE',
}

# Hard ceiling — executor will never return more than this to the LLM.
# Even if the AI or user requests more, this is the absolute maximum.
MAX_ROWS = 200  # change this if you want to allow more rows in responses


class ValidationResult:
    def __init__(self, is_valid, error=None, sanitized_sql=None):
        self.is_valid = is_valid
        self.error = error
        self.sanitized_sql = sanitized_sql


class SQLValidator:

    def validate(self, sql):
        if not sql:
            return ValidationResult(False, error="Empty SQL")

        cleaned = sql.strip().rstrip(';')

        # Strip markdown code fences if AI wrapped the query
        cleaned = re.sub(r'^```\w*\n?', '', cleaned)
        cleaned = re.sub(r'\n?```$', '', cleaned)
        cleaned = cleaned.strip()

        if not cleaned.upper().startswith('SELECT'):
            return ValidationResult(False, error="Only SELECT queries are allowed")

        tokens = re.findall(r'\b\w+\b', cleaned.upper())
        for token in tokens:
            if token in DANGEROUS_KEYWORDS:
                return ValidationResult(False, error="Forbidden keyword: {}".format(token))

        # Enforce LIMIT ceiling:
        # - If no LIMIT clause → inject MAX_ROWS
        # - If LIMIT is present but exceeds MAX_ROWS → replace it
        limit_match = re.search(r'\bLIMIT\s+(\d+)\b', cleaned, re.IGNORECASE)
        if limit_match:
            existing_limit = int(limit_match.group(1))
            if existing_limit > MAX_ROWS:
                cleaned = re.sub(
                    r'\bLIMIT\s+\d+\b',
                    'LIMIT {}'.format(MAX_ROWS),
                    cleaned,
                    flags=re.IGNORECASE,
                )
        else:
            cleaned = "{} LIMIT {}".format(cleaned, MAX_ROWS)

        return ValidationResult(True, sanitized_sql=cleaned)
