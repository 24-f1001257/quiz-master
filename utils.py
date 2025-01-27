from flask import request, redirect, url_for, flash
from functools import wraps

def is_loggedIn():
    userId = request.cookies.get('user_id')

    if userId is None:
        return False
    
    return True

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
        admin_id = request.cookies.get('admin_id')
        if not admin_id or admin_id != 'admin':
            flash('Admin access required!', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
