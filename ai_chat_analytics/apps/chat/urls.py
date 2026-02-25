from django.urls import path
from . import views

urlpatterns = [
    path('message/', views.ChatMessageView.as_view(), name='chat-message'),
    path('message/stream/', views.chat_stream, name='chat-stream'),
    path('session/<uuid:session_id>/', views.SessionHistoryView.as_view(), name='session-history'),
]
