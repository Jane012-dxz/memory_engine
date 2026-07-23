from database.db import get_all_chat_history

history = get_all_chat_history(limit=500)
for h in history:
    print(f"{h['user_id'][:8]} | {h['role']}: {h['content'][:50]}")