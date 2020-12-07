from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB

db = SQLAlchemy()


class PerformanceProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False)
    performance_record = db.Column(JSONB)
    performance_score = db.Column(JSONB)
    report_date = db.Column(db.DateTime, default=datetime.now())
