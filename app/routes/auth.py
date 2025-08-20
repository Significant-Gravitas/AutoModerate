import uuid

from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from app import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.form.get('email')
            password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

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
def register():
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
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Email already registered'
                }), 400
            else:
                flash('Email already registered', 'error')
                return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Username already taken'
                }), 400
            else:
                flash('Username already taken', 'error')
                return render_template('auth/register.html')

        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

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
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)


@auth_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
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
    current_user.set_password(new_password)
    db.session.commit()

    if request.is_json:
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })
    else:
        flash('Password changed successfully!', 'success')
        return redirect(url_for('auth.profile'))
