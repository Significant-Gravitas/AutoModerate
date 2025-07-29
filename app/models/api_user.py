from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from app import db

class APIUser(db.Model):
    __tablename__ = 'api_users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    external_user_id = db.Column(db.String(255), nullable=False)  # The user ID passed in metadata
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    total_requests = db.Column(db.Integer, default=0)
    approved_count = db.Column(db.Integer, default=0)
    rejected_count = db.Column(db.Integer, default=0)
    flagged_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref='api_users')
    content_items = db.relationship('Content', backref='api_user', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'external_user_id': self.external_user_id,
            'project_id': self.project_id,
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
            'total_requests': self.total_requests,
            'approved_count': self.approved_count,
            'rejected_count': self.rejected_count,
            'flagged_count': self.flagged_count,
            'approval_rate': (self.approved_count / self.total_requests * 100) if self.total_requests > 0 else 0,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def update_stats(self, status):
        """Update user statistics based on moderation result"""
        self.total_requests += 1
        self.last_seen = datetime.utcnow()
        
        if status == 'approved':
            self.approved_count += 1
        elif status == 'rejected':
            self.rejected_count += 1
        elif status == 'flagged':
            self.flagged_count += 1
    
    @property
    def approval_rate(self):
        if self.total_requests > 0:
            return (self.approved_count / self.total_requests) * 100
        return 0
    
    def __repr__(self):
        return f'<APIUser {self.external_user_id}>' 