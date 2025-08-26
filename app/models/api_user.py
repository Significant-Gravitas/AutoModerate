import uuid
from datetime import datetime

from app import db


class APIUser(db.Model):
    __tablename__ = 'api_users'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    # The user ID passed in metadata
    external_user_id = db.Column(db.String(255), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey(
        'projects.id'), nullable=False)
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    total_requests = db.Column(db.Integer, default=0)
    approved_count = db.Column(db.Integer, default=0)
    rejected_count = db.Column(db.Integer, default=0)
    flagged_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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

    def get_current_stats(self):
        """Get current stats by counting from database"""
        from app.models.content import Content

        # Count actual content records
        total_content = Content.query.filter_by(api_user_id=self.id).count()
        approved = Content.query.filter_by(api_user_id=self.id, status='approved').count()
        rejected = Content.query.filter_by(api_user_id=self.id, status='rejected').count()
        flagged = Content.query.filter_by(api_user_id=self.id, status='flagged').count()

        return {
            'total_requests': total_content,
            'approved_count': approved,
            'rejected_count': rejected,
            'flagged_count': flagged,
            'approval_rate': (approved / total_content * 100) if total_content > 0 else 0
        }

    @property
    def approval_rate(self):
        stats = self.get_current_stats()
        return stats['approval_rate']

    @property
    def current_total_requests(self):
        stats = self.get_current_stats()
        return stats['total_requests']

    @property
    def current_approved_count(self):
        stats = self.get_current_stats()
        return stats['approved_count']

    @property
    def current_rejected_count(self):
        stats = self.get_current_stats()
        return stats['rejected_count']

    @property
    def current_flagged_count(self):
        stats = self.get_current_stats()
        return stats['flagged_count']

    @property
    def days_active(self):
        """Calculate days active more accurately"""
        if not self.last_seen or not self.first_seen:
            return 0

        # Get date components only (ignore time)
        first_date = self.first_seen.date()
        last_date = self.last_seen.date()

        # Calculate difference in days and add 1 (inclusive)
        delta = (last_date - first_date).days + 1
        return max(1, delta)  # Minimum 1 day

    def __repr__(self):
        return f'<APIUser {self.external_user_id}>'
