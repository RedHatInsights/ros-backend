from datetime import date
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID, JSONB

db = SQLAlchemy()


class PerformanceProfile(db.Model):
    performance_record = db.Column(JSONB)
    performance_score = db.Column(JSONB)
    report_date = db.Column(db.Date, default=date.today())
    system_id = db.Column(db.Integer)
    __table_args__ = (
        db.PrimaryKeyConstraint('system_id', 'report_date', name='performance_profile_pkey'),
        db.ForeignKeyConstraint(['system_id'], ['systems.id'], name='performance_profile_system_id_fkey'),
    )

    @property
    def display_performance_score(self):
        display_performance_score = {
            'memory_score': self.performance_score['memory_score'] // 20,
            'cpu_score': self.performance_score['cpu_score'] // 20

            # TODO

            # commenting this as cpu and io metrics aren't currently present in report
            # 'io_score': self.performance_score['io_score'] // 20
        }
        return display_performance_score


class System(db.Model):
    __tablename__ = 'systems'
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer)
    inventory_id = db.Column(UUID(as_uuid=True), nullable=False)
    display_name = db.Column(db.String(100))
    fqdn = db.Column(db.String(100))
    cloud_provider = db.Column(db.String(25))
    instance_type = db.Column(db.String(25))
    state = db.Column(db.String(25))
    __table_args__ = (
        db.UniqueConstraint('inventory_id'),
        db.ForeignKeyConstraint(['account_id'], ['rh_accounts.id'], name='systems_account_id_fkey'),
    )


class RhAccount(db.Model):
    __tablename__ = 'rh_accounts'
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.Text, nullable=False)
    __table_args__ = (
        db.UniqueConstraint('account'),
        db.CheckConstraint('NOT(account IS NULL)'),
    )
