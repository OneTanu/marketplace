from django.contrib import admin

from .models import Conversation, ConversationParticipant, Message

admin.site.register(Conversation)
admin.site.register(ConversationParticipant)
admin.site.register(Message)
