"""System-wide settings model."""
import os

from app import db


class SystemSettings(db.Model):
    """Store system-wide configuration settings."""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500))
    description = db.Column(db.String(255))

    @staticmethod
    def get_setting(key, default=None):
        """Get a setting value by key."""
        setting = SystemSettings.query.filter_by(key=key).first()
        return setting.value if setting else default

    @staticmethod
    def set_setting(key, value, description=None):
        """Set a setting value."""
        setting = SystemSettings.query.filter_by(key=key).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
        else:
            setting = SystemSettings(key=key, value=value, description=description)
            db.session.add(setting)
        db.session.commit()
        return setting

    @staticmethod
    def is_registration_enabled():
        """Check if user registration is enabled.

        Requires both the REGISTRATION_ENABLED env var and the admin toggle
        to be 'true'. Closed by default.
        """
        if os.environ.get('REGISTRATION_ENABLED', 'false').lower() != 'true':
            return False
        value = SystemSettings.get_setting('registration_enabled', 'false')
        return (value or 'false').lower() == 'true'

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description
        }

    def __repr__(self):
        return f'<SystemSettings {self.key}={self.value}>'
