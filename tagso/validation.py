"""Request parameter validation helpers."""

from functools import wraps

from flask import request


def require_params(*keys, source="json"):
    """Decorator that validates required parameters and injects them as `params`.

    Args:
        *keys: Required parameter names.
        source: Where to read from: "args", "json", or "form".

    Returns:
        Decorated view. On validation failure, returns 400 JSON response.
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if source == "args":
                data = request.args
            elif source == "json":
                data = request.get_json()
                if data is None:
                    return {"error": "JSON body required"}, 400
            elif source == "form":
                data = request.form
            else:
                return {"error": "invalid validation source"}, 500

            missing = [k for k in keys if not data.get(k)]
            if missing:
                return {"error": f"{', '.join(missing)} required"}, 400
            kwargs["params"] = data
            return f(*args, **kwargs)

        return wrapped

    return decorator
