from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from app.services.database_service import db_service

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
async def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')

        user = await db_service.get_user_by_email(email)

        if user and user.check_password(password):
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
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Invalid email or password'
                }), 401
            else:
                flash('Invalid email or password', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
async def register():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
        else:
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

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

        # Create new user
        user = await db_service.create_user(username=username, email=email, password=password)
        if not user:
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Failed to create user account'
                }), 500
            else:
                flash('Failed to create user account', 'error')
                return render_template('auth/register.html')

        login_user(user)

        if request.is_json:
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user': user.to_dict()
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

    # Validate new password
    if len(new_password) < 6:
        if request.is_json:
            return jsonify({
                'success': False,
                'message': 'New password must be at least 6 characters long'
            }), 400
        else:
            flash('New password must be at least 6 characters long', 'error')
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
