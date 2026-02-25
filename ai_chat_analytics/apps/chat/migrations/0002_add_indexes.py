from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add indexes for chat tables:
      - chat_message.(session, created_at)  — session history queries
      - chat_query_audit.session_id         — audit lookups by session
    """

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='chatmessage',
            index=models.Index(
                fields=['session', 'created_at'],
                name='chat_message_session_created_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='queryauditlog',
            index=models.Index(fields=['session'], name='chat_audit_session_idx'),
        ),
        migrations.AddIndex(
            model_name='queryauditlog',
            index=models.Index(fields=['created_at'], name='chat_audit_created_at_idx'),
        ),
    ]
