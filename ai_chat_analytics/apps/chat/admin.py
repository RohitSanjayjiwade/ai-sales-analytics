from django.contrib import admin
from .models import ChatSession, ChatMessage, QueryAuditLog


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ('role', 'content', 'status', 'created_at')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'created_at')
    inlines = [ChatMessageInline]


@admin.register(QueryAuditLog)
class QueryAuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user_question', 'row_count', 'execution_time_ms', 'error')
    readonly_fields = ('session', 'user_question', 'generated_sql', 'execution_time_ms', 'row_count', 'error', 'created_at')
