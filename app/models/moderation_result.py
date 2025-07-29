from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from app import db

class ModerationResult(db.Model):
    __tablename__ = 'moderation_results'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content_id = db.Column(db.String(36), db.ForeignKey('content.id'), nullable=False)
    moderator_type = db.Column(db.String(20), nullable=False)  # ai, rule, manual
    moderator_id = db.Column(db.String(100))  # rule_id, ai_model, user_id
    decision = db.Column(db.String(20), nullable=False)  # approved, rejected, flagged
    confidence = db.Column(db.Float)  # 0.0 to 1.0
    reason = db.Column(db.Text)
    details = db.Column(db.JSON)  # Additional details about the moderation
    processing_time = db.Column(db.Float)  # Processing time in seconds
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rule = db.relationship('ModerationRule', foreign_keys=[moderator_id], 
                          primaryjoin="and_(ModerationResult.moderator_id==ModerationRule.id, "
                                    "ModerationResult.moderator_type=='rule')",
                          uselist=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'content_id': self.content_id,
            'moderator_type': self.moderator_type,
            'moderator_id': self.moderator_id,
            'decision': self.decision,
            'confidence': self.confidence,
            'reason': self.reason,
            'details': self.details,
            'processing_time': self.processing_time,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<ModerationResult {self.id}>'
