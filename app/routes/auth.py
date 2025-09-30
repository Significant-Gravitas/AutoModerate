import re

from authlib.integrations.flask_client import OAuth
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.services.database_service import db_service

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()


@auth_bp.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        # Input validation and sanitization
        if request.is_json:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'Invalid JSON data'
                }), 400
            email = data.get('email', '').strip()
            password = data.get('password', '')
        else:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')

        # Validate required fields
        if not email or not password:
            error_msg = 'Email and password are required'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            else:
                flash(error_msg, 'error')
                return render_template('auth/login.html')

        # Validate email format
        if not _is_valid_email(email):
            error_msg = 'Invalid email format'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            else:
                flash(error_msg, 'error')
                return render_template('auth/login.html')

        # Normalize inputs
        email = email.lower()

        # Rate limiting check (basic implementation)
        if len(password) > 200:  # Prevent excessive password lengths
            error_msg = 'Invalid credentials'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 401
            else:
                flash(error_msg, 'error')
                return render_template('auth/login.html')

        user = await db_service.get_user_by_email(email)

        if user and user.is_active and user.check_password(password):
            login_user(user)
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'user': user.to_dict()
                })
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard.index'))
        else:
            # Generic error message to prevent user enumeration
            error_msg = 'Invalid email or password'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 401
            else:
                flash(error_msg, 'error')
                return render_template('auth/login.html')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
async def register():
    if request.method == 'POST':
        # Input validation and sanitization
        if request.is_json:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'message': 'Invalid JSON data'
                }), 400
            username = data.get('username', '').strip()
            email = data.get('email', '').strip()
            password = data.get('password', '')
        else:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')

        # Validate required fields
        if not username or not email or not password:
            error_msg = 'All fields are required'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            else:
                flash(error_msg, 'error')
                return render_template('auth/register.html')

        # Validate email format
        if not _is_valid_email(email):
            error_msg = 'Invalid email format'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            else:
                flash(error_msg, 'error')
                return render_template('auth/register.html')

        # Validate username format
        if not _is_valid_username(username):
            error_msg = 'Username must be 3-50 characters, alphanumeric and underscores only'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            else:
                flash(error_msg, 'error')
                return render_template('auth/register.html')

        # Validate password strength
        if len(password) < 8:
            error_msg = 'Password must be at least 8 characters long'
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 400
            else:
                flash(error_msg, 'error')
                return render_template('auth/register.html')

        # Normalize inputs
        username = username
        email = email.lower()

        # Check if user already exists
        if await db_service.get_user_by_email(email):
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Email already registered'
                }), 400
            else:
                flash('Email already registered', 'error')
                return render_template('auth/register.html')

        if await db_service.get_user_by_username(username):
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Username already taken'
                }), 400
            else:
                flash('Username already taken', 'error')
                return render_template('auth/register.html')

        # Create new user and get fresh instance immediately
        created_user = await db_service.create_user(username=username, email=email, password=password)
        if not created_user:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create user account'
                }), 500
            else:
                flash('Failed to create user account', 'error')
                return render_template('auth/register.html')

        # Get fresh user by email to avoid detached session error
        fresh_user = await db_service.get_user_by_email(email)
        login_user(fresh_user)

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': fresh_user.to_dict()
            })
        else:
            flash('Registration successful!', 'success')
            return redirect(url_for('dashboard.index'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
async def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
async def profile():
    # Get fresh user data with projects loaded to avoid detached instance errors
    user = await db_service.get_user_with_projects(current_user.id)
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.login'))
    return render_template('auth/profile.html', user=user)


def _is_valid_email(email):
    """Validate email format"""
    if not email or len(email) > 320:  # RFC 5321 limit
        return False
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_regex, email) is not None


def _is_valid_username(username):
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 50:
        return False
    username_regex = r'^[a-zA-Z0-9_]+$'
    return re.match(username_regex, username) is not None


def _is_valid_password(password):
    """Validate password strength"""
    if len(password) < 8 or len(password) > 200:
        return False
    # At least one uppercase, one lowercase, one digit
    return (re.search(r'[A-Z]', password) and
            re.search(r'[a-z]', password) and
            re.search(r'\d', password))


@auth_bp.route('/google')
def google_login():
    """Redirect to Google OAuth login"""
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/google/callback')
async def google_callback():
    """Handle Google OAuth callback"""
    try:
        token = oauth.google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            flash('Failed to get user information from Google', 'error')
            return redirect(url_for('auth.login'))

        google_id = user_info.get('sub')
        email = user_info.get('email')

        if not google_id or not email:
            flash('Invalid user information from Google', 'error')
            return redirect(url_for('auth.login'))

        # Check if user exists with this Google ID
        user = await db_service.get_user_by_google_id(google_id)

        if user:
            # User exists, log them in
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard.index'))

        # Check if user exists with this email
        user = await db_service.get_user_by_email(email.lower())

        if user:
            # Link Google account to existing user
            await db_service.link_google_account(user.id, google_id)
            login_user(user)
            flash('Google account linked successfully!', 'success')
            return redirect(url_for('dashboard.index'))

        # Create new user
        username = email.split('@')[0]
        # Make username unique if it already exists
        base_username = username
        counter = 1
        while await db_service.get_user_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1

        # Create user without password (Google SSO only)
        user = await db_service.create_google_user(
            username=username,
            email=email.lower(),
            google_id=google_id
        )

        if not user:
            flash('Failed to create user account', 'error')
            return redirect(url_for('auth.login'))

        # Get fresh user and log in
        fresh_user = await db_service.get_user_by_email(email.lower())
        login_user(fresh_user)
        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard.index'))

    except Exception as e:
        current_app.logger.error(f"Google OAuth error: {str(e)}")
        flash('Authentication failed. Please try again.', 'error')
        return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['POST'])
@login_required
async def change_password():
    # Check if this is an AJAX request by looking for specific headers or content type
    # is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
    #     request.headers.get('Content-Type') == 'application/json' or \
    #     'application/json' in request.headers.get('Accept', '')

    if request.is_json:
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
    else:
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

    # Validate current password
    if not current_user.check_password(current_password):
        if request.is_json:
            return jsonify({
                'success': False,
                'message': 'Current password is incorrect'
            }), 400
        else:
            flash('Current password is incorrect', 'error')
            return redirect(url_for('auth.profile'))

    # Validate inputs
    if not current_password or not new_password or not confirm_password:
        error_msg = 'All password fields are required'
        if request.is_json:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        else:
            flash(error_msg, 'error')
            return redirect(url_for('auth.profile'))

    # Validate new password
    if len(new_password) < 8:
        if request.is_json:
            return jsonify({
                'success': False,
                'message': 'New password must be at least 8 characters long'
            }), 400
        else:
            flash('New password must be at least 8 characters long', 'error')
            return redirect(url_for('auth.profile'))

    # Check password strength
    if not _is_valid_password(new_password):
        error_msg = 'Password must contain at least one uppercase, one lowercase, and one number'
        if request.is_json:
            return jsonify({
                'success': False,
                'message': error_msg
            }), 400
        else:
            flash(error_msg, 'error')
            return redirect(url_for('auth.profile'))

    # Validate password confirmation
    if new_password != confirm_password:
        if request.is_json:
            return jsonify({
                'success': False,
                'message': 'New passwords do not match'
            }), 400
        else:
            flash('New passwords do not match', 'error')
            return redirect(url_for('auth.profile'))

    # Update password
    if not await db_service.update_user_password(current_user.id, new_password):
        if request.is_json:
            return jsonify({
                'success': False,
                'message': 'Failed to update password'
            }), 500
        else:
            flash('Failed to update password', 'error')
            return redirect(url_for('auth.profile'))

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
    else:
        flash('Password changed successfully!', 'success')
        return redirect(url_for('auth.profile'))
