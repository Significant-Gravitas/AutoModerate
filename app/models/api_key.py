import secrets
import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

from app import db


class APIKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey(
        'projects.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_used = db.Column(db.DateTime)
    usage_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, **kwargs):
        super(APIKey, self).__init__(**kwargs)
        if not self.key:
            self.key = self.generate_key()

    @staticmethod
    def generate_key():
        return f"am_{secrets.token_urlsafe(32)}"

    def increment_usage(self):
        self.usage_count += 1
        self.last_used = datetime.utcnow()
        db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'name': self.name,
            'project_id': self.project_id,
            'is_active': self.is_active,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'usage_count': self.usage_count,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f'<APIKey {self.name}>'
