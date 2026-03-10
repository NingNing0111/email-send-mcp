def validate_email(email):
    import re
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None

def format_email_content(subject, body):
    return f"Subject: {subject}\n\n{body}"


def recipient_resolver_from_tool(tool_callable, *args, **kwargs):
    """Call a tool (callable) to resolve recipients.

    tool_callable must return an iterable of email addresses or dicts
    convertible to strings. This wrapper just forwards args/kwargs and
    normalizes the result to a list of strings.
    """
    raw = tool_callable(*args, **kwargs)
    # Normalize
    recipients = []
    if raw is None:
        return recipients
    for r in raw:
        if isinstance(r, dict):
            # support {'email': 'a@b.c'}
            email = r.get("email") or r.get("to")
            if email:
                recipients.append(str(email))
        else:
            recipients.append(str(r))
    return recipients


def template_renderer_from_tool(tool_callable, template_id, context=None, *args, **kwargs):
    """Call a tool to render a template.

    Expects the tool to return either a tuple (subject, body) or a dict
    with keys 'subject' and 'body'. Returns (subject, body).
    """
    context = context or {}
    raw = tool_callable(template_id, context, *args, **kwargs)
    if raw is None:
        return "", ""
    if isinstance(raw, tuple) or isinstance(raw, list):
        subject, body = raw[0], raw[1]
        return str(subject), str(body)
    if isinstance(raw, dict):
        return str(raw.get("subject", "")), str(raw.get("body", ""))
    # Fallback: convert to string
    return "", str(raw)


# --- Simple mock tools for local testing ---
def mock_recipient_tool(template_id=None, context=None):
    """Return a small list of recipients for testing/demo."""
    return ["user1@example.com", "user2@example.com"]


def mock_template_tool(template_id, context=None):
    subject = f"[Mock:{template_id}] " + (context or {}).get("title", "No Title")
    body = (context or {}).get("message", "This is a mock template body.")
    return {"subject": subject, "body": body}