from datetime import date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB

db = SQLAlchemy()


class PerformanceProfile(db.Model):
    __table_args__ = (db.UniqueConstraint('inventory_id', 'report_date'), )
    id = db.Column(db.Integer, primary_key=True)
    inventory_id = db.Column(UUID(as_uuid=True), nullable=False)
    performance_record = db.Column(JSONB)
    performance_score = db.Column(JSONB)
    report_date = db.Column(db.Date, default=date.today())
