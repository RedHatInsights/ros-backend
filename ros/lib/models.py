from datetime import date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB
import datetime
import enum

db = SQLAlchemy()


class PerformanceProfile(db.Model):
    performance_record = db.Column(JSONB)
    performance_score = db.Column(JSONB)
    report_date = db.Column(db.Date, default=date.today())
    system_id = db.Column(db.Integer)
    __table_args__ = (
        db.PrimaryKeyConstraint('system_id', 'report_date', name='performance_profile_pkey'),
        db.ForeignKeyConstraint(
            ['system_id'], ['systems.id'],
            name='performance_profile_system_id_fkey',
            ondelete='CASCADE'),
    )

    @property
    def display_performance_score(self):
        display_performance_score = {}
        for key, value in self.performance_score.items():
            score = value // 20
            display_performance_score[key] = 1 if score < 1 else score

        return display_performance_score

    @property
    def idling_time(self):
        return (self.performance_record['kernel.all.cpu.idle']
                / self.performance_record['total_cpus'])

    @property
    def io_wait(self):
        return self.performance_record['kernel.all.cpu.wait.total']


class System(db.Model):
    __tablename__ = 'systems'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer)
    inventory_id = db.Column(UUID(as_uuid=True), nullable=False)
    display_name = db.Column(db.String(100))
    fqdn = db.Column(db.String(100))
    cloud_provider = db.Column(db.String(25))
    instance_type = db.Column(db.String(25))
    rule_hit_details = db.Column(JSONB)
    __table_args__ = (
        db.UniqueConstraint('inventory_id'),
        db.ForeignKeyConstraint(['account_id'], ['rh_accounts.id'], name='systems_account_id_fkey'),
    )


class RatingChoicesEnum(enum.IntEnum):
    Dislike = -1
    Neutral = 0
    Like = 1


class RecommendationRating(db.Model):
    __tablename__ = 'recommendation_rating'
    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer)
    rated_by = db.Column(db.Text, nullable=False)
    rating = db.Column(db.SmallInteger, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        db.ForeignKeyConstraint(
            ['system_id'], ['systems.id'],
            name='recommendation_rating_system_id_fkey',
            ondelete='CASCADE'
        ),
    )


class RhAccount(db.Model):
    __tablename__ = 'rh_accounts'
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.Text, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('account'),
        db.CheckConstraint('NOT(account IS NULL)'),
    )
