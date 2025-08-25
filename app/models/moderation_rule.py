import uuid
from datetime import datetime

from app import db


class ModerationRule(db.Model):
    __tablename__ = 'moderation_rules'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey(
        'projects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    # keyword, regex, ai_prompt, etc.
    rule_type = db.Column(db.String(50), nullable=False)
    # The actual rule configuration
    rule_data = db.Column(db.JSON, nullable=False)
    # approve, reject, flag, review
    action = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    # Higher priority rules are checked first
    priority = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
