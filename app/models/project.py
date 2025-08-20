import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

from app import db


class ProjectMember(db.Model):
    __tablename__ = 'project_members'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey(
        'projects.id'), nullable=False)
    user_id = db.Column(db.String(36), db.ForeignKey(
        'users.id'), nullable=False)
    # 'owner', 'admin', 'member'
    role = db.Column(db.String(20), default='member')
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref='memberships')
    user = db.relationship('User', backref='project_memberships')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'joined_at': self.joined_at.isoformat(),
            'user': self.user.to_dict() if self.user else None
        }


class ProjectInvitation(db.Model):
    __tablename__ = 'project_invitations'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey(
        'projects.id'), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    invited_by = db.Column(
        db.String(36), db.ForeignKey('users.id'), nullable=False)
    role = db.Column(db.String(20), default='member')
    # 'pending', 'accepted', 'declined', 'expired'
    status = db.Column(db.String(20), default='pending')
    token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    project = db.relationship('Project', backref='invitations')
    inviter = db.relationship('User', backref='sent_invitations')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'email': self.email,
            'invited_by': self.invited_by,
            'role': self.role,
            'status': self.status,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat()
        }


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    user_id = db.Column(db.String(36), db.ForeignKey(
        'users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    api_keys = db.relationship(
        'APIKey', backref='project', lazy=True, cascade='all, delete-orphan')
    content = db.relationship(
        'Content', backref='project', lazy=True, cascade='all, delete-orphan')
    moderation_rules = db.relationship(
        'ModerationRule', backref='project', lazy=True, cascade='all, delete-orphan')

    @property
    def members(self):
        """Get all members of the project"""
        return [membership.user for membership in self.memberships]

    @property
    def member_ids(self):
        """Get all member user IDs"""
        return [membership.user_id for membership in self.memberships]

    def is_member(self, user_id):
        """Check if a user is a member of this project"""
        return user_id in self.member_ids or user_id == self.user_id

    def get_member_role(self, user_id):
        """Get the role of a user in this project"""
        if user_id == self.user_id:
            return 'owner'
        membership = next(
            (m for m in self.memberships if m.user_id == user_id), None)
        return membership.role if membership else None

    def can_manage_members(self, user_id):
        """Check if a user can manage project members"""
        role = self.get_member_role(user_id)
        return role in ['owner', 'admin']

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'user_id': self.user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'api_keys_count': len(self.api_keys),
            'content_count': len(self.content),
            'members_count': len(self.memberships)
        }

    def __repr__(self):
        return f'<Project {self.name}>'
