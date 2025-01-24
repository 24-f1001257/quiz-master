from flask import request, redirect, url_for
from functools import wraps

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.cookies.get('user_id')
        if user_id is None:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        admin = request.cookies.get('is_admin')

        if not admin:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function