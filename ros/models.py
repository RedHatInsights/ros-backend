import uuid
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

db = SQLAlchemy()


class PerformanceProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(UUID(as_uuid=True), default=uuid.uuid4)
    avg_memory_used = db.Column(db.String(25))
    avg_memory = db.Column(db.String(25))
