import uuid
from django.db import models


class ChatSession(models.Model):
    """Represents a single conversation thread with the AI."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_session'
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.id} - {self.title or 'Untitled'}"


class ChatMessage(models.Model):
    """Individual message inside a chat session."""

    class Role(models.TextChoices):
        USER = 'user', 'User'
        ASSISTANT = 'assistant', 'Assistant'

    class Status(models.TextChoices):
        SUCCESS = 'success', 'Success'
        FAILED = 'failed', 'Failed'

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_message'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:60]}"


class QueryAuditLog(models.Model):
    """Audit trail — every SQL query the AI generates and runs."""

    session = models.ForeignKey(ChatSession, on_delete=models.SET_NULL, null=True, blank=True)
    user_question = models.TextField()
    generated_sql = models.TextField()
    execution_time_ms = models.IntegerField(null=True, blank=True)
    row_count = models.IntegerField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_query_audit'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.created_at}] {self.user_question[:60]}"
