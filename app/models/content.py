import uuid
from datetime import datetime

from app import db


class Content(db.Model):
    __tablename__ = 'content'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey(
        'projects.id'), nullable=False)
    # text, image, video, etc.
    content_type = db.Column(db.String(50), nullable=False)
    # The actual content or URL
    content_data = db.Column(db.Text, nullable=False)
    meta_data = db.Column(db.JSON)  # Additional metadata
    # pending, approved, rejected, flagged
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    moderation_results = db.relationship(
        'ModerationResult', backref='content', lazy=True, cascade='all, delete-orphan')
    api_user_id = db.Column(db.String(36), db.ForeignKey(
        'api_users.id'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'content_type': self.content_type,
            'content_data': self.content_data,
            'meta_data': self.meta_data,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'moderation_results': [result.to_dict() for result in self.moderation_results]
        }

    def __repr__(self):
        return f'<Content {self.id}>'
