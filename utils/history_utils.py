MAX_HISTORY_MESSAGES = 10

def truncate_history(history):
    if not history:
        return history
    system_msgs = [m for m in history if m["role"] == "system"]
    others = [m for m in history if m["role"] != "system"]
    truncated = others[-MAX_HISTORY_MESSAGES:]
    return system_msgs + truncated
