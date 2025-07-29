from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from app import db

class ModerationRule(db.Model):
    __tablename__ = 'moderation_rules'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    rule_type = db.Column(db.String(50), nullable=False)  # keyword, regex, ai_prompt, etc.
    rule_data = db.Column(db.JSON, nullable=False)  # The actual rule configuration
    action = db.Column(db.String(20), nullable=False)  # approve, reject, flag, review
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0)  # Higher priority rules are checked first
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'rule_type': self.rule_type,
            'rule_data': self.rule_data,
            'action': self.action,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ModerationRule {self.name}>'
