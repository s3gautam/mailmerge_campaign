"""Business logic for browsing and replying to Gmail threads.

Never calls the Gmail API directly — always goes through GmailService,
same as the campaign module.
"""

from __future__ import annotations

from services.gmail_service import GmailService, ThreadDetail, ThreadSummary


class InboxManager:
    def __init__(self, gmail_service: GmailService) -> None:
        self.gmail_service = gmail_service

    def list_threads(self, query: str = "", max_results: int = 20) -> list[ThreadSummary]:
        return self.gmail_service.list_threads(query=query, max_results=max_results)

    def get_thread(self, thread_id: str) -> ThreadDetail:
        return self.gmail_service.get_thread(thread_id)

    def reply(self, thread: ThreadDetail, body: str) -> str:
        """Reply to the most recent message in a thread."""
        if not thread.messages:
            raise ValueError("Thread has no messages to reply to")
        last_message = thread.messages[-1]
        return self.gmail_service.reply_to_thread(
            thread_id=thread.id,
            to=last_message.sender,
            subject=thread.subject,
            body=body,
            in_reply_to=last_message.message_id_header,
        )
