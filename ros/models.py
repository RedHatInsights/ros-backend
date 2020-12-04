from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID

db = SQLAlchemy()


class PerformanceProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False)
    avg_memory_used = db.Column(db.String(25))
    avg_memory = db.Column(db.String(25))
    report_date = db.Column(db.DateTime, default=datetime.now())
