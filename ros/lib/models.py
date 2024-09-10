from ros.extensions import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
import datetime
import enum


class PerformanceProfile(db.Model):
    performance_record = db.Column(JSONB)
    performance_utilization = db.Column(JSONB)
    report_date = db.Column(
        db.DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        nullable=False
    )
    state = db.Column(db.String(25), index=True)
    operating_system = db.Column(JSONB)
    rule_hit_details = db.Column(JSONB)
    number_of_recommendations = db.Column(db.Integer)
    system_id = db.Column(db.Integer)
    psi_enabled = db.Column(db.Boolean)
    top_candidate = db.Column(db.String(25), nullable=True)
    top_candidate_price = db.Column(db.Float)
    __table_args__ = (
        db.PrimaryKeyConstraint('system_id', name='performance_profile_pkey'),
        db.ForeignKeyConstraint(
            ['system_id'], ['systems.id'],
            name='performance_profile_system_id_fkey',
            ondelete='CASCADE'),
        db.Index('non_optimized_system_profiles', number_of_recommendations, unique=False,
                 postgresql_where=(number_of_recommendations > 0)),
        db.Index('top_candidate_idx', top_candidate)
    )

    @property
    def idling_time(self):
        if 'kernel.all.cpu.idle' in self.performance_record:
            idling_percent = ((float(self.performance_record['kernel.all.cpu.idle']) * 100)
                              / int(self.performance_record['total_cpus']))
            return "%0.2f" % idling_percent


class PerformanceProfileHistory(db.Model):
    performance_record = db.Column(JSONB)
    performance_utilization = db.Column(JSONB)
    report_date = db.Column(
        db.DateTime(timezone=True),
        default=datetime.datetime.utcnow,
        nullable=False,
        index=True
    )
    state = db.Column(db.String(25))
    operating_system = db.Column(JSONB)
    rule_hit_details = db.Column(JSONB)
    number_of_recommendations = db.Column(db.Integer)
    system_id = db.Column(db.Integer)
    psi_enabled = db.Column(db.Boolean)
    __table_args__ = (
        db.PrimaryKeyConstraint('system_id', 'report_date', name='pk_performance_profile_history'),
        db.ForeignKeyConstraint(
            ['system_id'], ['systems.id'],
            name='fk_performance_profile_history_systems',
            ondelete='CASCADE'),
    )


class System(db.Model):
    __tablename__ = 'systems'
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer)
    inventory_id = db.Column(UUID(as_uuid=True), nullable=False)
    display_name = db.Column(db.String(100))
    fqdn = db.Column(db.String(100))
    cloud_provider = db.Column(db.String(25))
    instance_type = db.Column(db.String(25))
    state = db.Column(db.String(25))
    stale_timestamp = db.Column(db.DateTime(timezone=True))
    region = db.Column(db.String(25))
    operating_system = db.Column(JSONB, index=True)
    __table_args__ = (
        db.UniqueConstraint('inventory_id'),
        db.ForeignKeyConstraint(['tenant_id'], ['rh_accounts.id'], name='systems_tenant_id_fkey'),
        db.Index('inventory_id_hash_index', inventory_id, postgresql_using='hash'),
    )
    cpu_states = db.Column(db.ARRAY(db.String))
    io_states = db.Column(db.ARRAY(db.String))
    memory_states = db.Column(db.ARRAY(db.String))
    groups = db.Column(JSONB)

    @property
    def deserialize_host_os_data(self):
        """
        Returns os data per host in a consumable format
        """
        os_data = None
        if (
                self.operating_system
                and all(key in self.operating_system.keys() for key in ['name', 'major', 'minor'])
        ):
            os_data = f"{self.operating_system.get('name')} " \
                         f"{self.operating_system.get('major')}." \
                         f"{self.operating_system.get('minor')}"

        return os_data


class RatingChoicesEnum(enum.IntEnum):
    Dislike = -1
    Neutral = 0
    Like = 1


class RecommendationRating(db.Model):
    __tablename__ = 'recommendation_rating'
    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer, index=True)
    rated_by = db.Column(db.Text, nullable=False, index=True)
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
    account = db.Column(db.Text, nullable=True)
    org_id = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('org_id'),
        db.CheckConstraint('NOT(org_id IS NULL)'),
    )


class Rule(db.Model):
    __tablename__ = 'rules'
    id = db.Column(db.Integer, primary_key=True)
    rule_id = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    resolution = db.Column(db.Text, nullable=False)
    condition = db.Column(db.Text, nullable=False)
