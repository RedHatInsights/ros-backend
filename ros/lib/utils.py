from collections import Counter
from http.server import BaseHTTPRequestHandler
import threading
import uuid
import base64
import json
from flask import jsonify, make_response
from flask_restful import abort
from sqlalchemy import Integer, select
from ros.lib.models import (
    RhAccount,
    System,
    PerformanceProfile,
    PerformanceProfileHistory,
    db,)
from ros.lib.config import get_logger
from ros.lib import aws_instance_types
from ros.processor.metrics import ec2_instance_lookup_failures
from ros.lib.constants import CloudProvider, OperatingSystem

LOG = get_logger(__name__)
PROCESSOR_INSTANCES = []


def is_valid_uuid(val):
    try:
        uuid.UUID(str(val), version=4)
        return True
    except ValueError:
        return False


def get_or_create(session, model, keys, **kwargs):
    if not keys:
        keys = kwargs.keys()
    if isinstance(keys, str):
        keys = [keys]
    if not isinstance(keys, list):
        raise TypeError('keys argument must be a list or string')
    instance = session.scalar(db.select(model).filter_by(**{k: kwargs[k] for k in keys}))
    if instance:
        for k, v in kwargs.items():
            setattr(instance, k, v)
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.flush()
    return instance


def update_system_record(session, **kwargs):
    inventory_id = kwargs.get('inventory_id')
    if inventory_id is None:
        return
    instance = session.scalar(db.select(System).filter_by(inventory_id=inventory_id))
    if instance:
        for k, v in kwargs.items():
            setattr(instance, k, v)
    return instance


def delete_record(session, model, **kwargs):
    """ Deletes a record filtered by key(s) present in kwargs(contains model specific fields)."""
    keys = list(kwargs.keys())
    instance = session.scalar(db.select(model).filter_by(**{k: kwargs[k] for k in keys}))
    if instance:
        session.delete(instance)
        session.commit()
    return instance


def identity(request):
    ident = request.headers.get('X-RH-IDENTITY')
    if not ident:
        response = make_response(
            jsonify({"Error": "Authentication token not provided"}), 401)
        abort(response)
    else:
        return json.loads(base64.b64decode(ident))


def user_data_from_identity(identity):
    """
    Get the user details dict from the rh-identity data or error out.
    """
    if 'user' not in identity:
        return None

    return identity['user']


def is_valid_cloud_provider(cloud_provider):
    """
    Validates cloud_provider value.
    """
    return cloud_provider in [provider.value for provider in CloudProvider]


def is_valid_operating_system(operating_system):
    """
    Validates operating_system value.
    """
    return operating_system["name"] in [os.value for os in OperatingSystem]


def validate_ros_payload(is_ros, cloud_provider, operating_system):
    """
    Validate ros payload.
    :param is_ros: is_ros boolean flag
    :param cloud_provider: cloud provider value
    :return: True if cloud_provider is supported & is_ros is true else False.
    """
    return is_ros and is_valid_cloud_provider(cloud_provider) and is_valid_operating_system(operating_system)


def cast_iops_as_float(iops_all_dict):
    """
    Convert IOPS  values from str to float
    :param iops_all_dict: IOPS dict to convert.
    :return: IOPS values as float
    """
    iops_all_dict_float = {}
    for key, value in iops_all_dict.items():
        try:
            iops_all_dict_float[key] = float(value)
        except ValueError:
            continue
    return iops_all_dict_float


def sort_io_dict(performance_utilization: dict):
    """
    Sorts io dict by max_io in descending order.
    """
    sorted_io_dict = {
        'io_all': dict(sorted(performance_utilization['io'].items(), key=lambda x: x[1], reverse=True))
    }
    performance_utilization.update({**sorted_io_dict})
    del performance_utilization['io']
    return performance_utilization


def system_ids_by_org_id(org_id, fetch_records=False):
    account_query = select(RhAccount.id).where(RhAccount.org_id == org_id)

    if fetch_records is True:
        return select(System).filter(System.tenant_id.in_(account_query))
    return select(System.id).filter(System.tenant_id.in_(account_query))


def org_id_from_identity_header(request):
    return identity(request)['identity']['org_id']


def insert_performance_profiles(session, system_id, fields):
    """This method deletes an old entry from performance_profile &
       inserts latest data inside performance_profile as well as
       performance_profile_history table.
    """
    fields = {} if fields is None else fields
    fields_for_perf_profile_history = redact_instance_type_and_price(fields)

    old_profile_record = session.query(PerformanceProfile).filter_by(
        system_id=system_id).first()
    if old_profile_record:
        session.delete(old_profile_record)
        session.commit()

    model_fields_map = {PerformanceProfile: fields,
                        PerformanceProfileHistory: fields_for_perf_profile_history}

    for model_class, model_fields in model_fields_map.items():
        new_entry = model_class(**model_fields)
        session.add(new_entry)
        session.flush()


def redact_instance_type_and_price(fields):
    """Remove unwanted attributes for performance profile history.
        Such as - top_candidate & top_candidate_price.
    """
    fields_for_perf_profile_history = {}
    try:
        fields_for_perf_profile_history = fields.copy()
        del fields_for_perf_profile_history['top_candidate']
        del fields_for_perf_profile_history['top_candidate_price']
    except KeyError as err:
        LOG.debug(f'Key(s) not found in fields: {err}')
    return fields_for_perf_profile_history


def count_per_state(queryset, custom_filters: dict):
    return queryset.filter_by(**custom_filters).count() if queryset else 0


def calculate_percentage(numerator, denominator):
    if numerator and denominator:
        return round((numerator / denominator) * 100, 2)
    else:
        return 0


def systems_ids_for_existing_profiles(org_id):
    return db.session.query(PerformanceProfile.system_id) \
        .filter(PerformanceProfile.system_id.in_(system_ids_by_org_id(org_id)))


class MonitoringHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        total_processors_names = list(map(lambda i: i.processor_name, PROCESSOR_INSTANCES))
        active_threads_names = list(map(lambda i: i.name, threading.enumerate()))
        if not all(item in active_threads_names for item in total_processors_names):
            dead_processors = set(total_processors_names).difference(active_threads_names)
            LOG.error(f"SERVICE STATUS - Dead processors - {dead_processors}")
            self.send_response(500)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes("ERROR: Processor thread exited", encoding='utf8'))
        else:
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(bytes("All Processor and Threads are running", encoding='utf8'))

    def log_request(self, code='-', size='-'):
        if code == 200:
            return
        else:
            super().log_request(code, size)


def get_psi_count(queryset: db.Model, bool_flag: bool) -> int:
    return queryset.filter(
        PerformanceProfile.operating_system['major'].astext.cast(Integer) != 7,
        PerformanceProfile.psi_enabled == bool_flag
    ).count()


def instance_type_info_by_name(instance_type_name, cloud_provider):
    """Returns dict with metadata of instance type from static data."""
    instance_type_properties = None
    if cloud_provider == 'AWS':
        instance_type_properties = aws_instance_types.INSTANCE_TYPES.get(
            instance_type_name, None)
        if instance_type_properties is None:
            # logging lookup failure on Prometheus
            ec2_instance_lookup_failures.labels(reporter='API Events').inc()
    return instance_type_properties


def generate_highlight_description(instance_type, cloud_provider, regions):
    """Returns string that is description against instance type."""
    instance_type_properties = instance_type_info_by_name(
        instance_type, cloud_provider)
    regions_info = ",".join(regions) + ' regions' if regions else ''

    if instance_type_properties is not None:
        cpu_type = instance_type_properties['extra']['physicalProcessor']
        num_vcpus = instance_type_properties['extra']['vcpu']
        ram_gb = instance_type_properties['extra']['memory']
        description_text = f'{cpu_type} instance with {num_vcpus} vCPUs ' \
                           f'and {ram_gb} of RAM, running on {cloud_provider} ' \
                           f'{regions_info}'
        return description_text

    return 'NA'


def is_current_section(section):
    """
        Returns true when section is current
        otherwise false for rest sections.
    """
    return section == 'current'


def find_instance_type(section, record):
    """Get instance type by current, suggested & historical section."""
    instance_type = None
    try:
        if is_current_section(section):
            instance_type = record.rule_hit_details[0]['details']['instance_type']
        else:
            instance_type = record.rule_hit_details[0]['details']['candidates'][0][0]
    except (IndexError, KeyError):
        instance_type = None

    if is_current_section(section):
        return (instance_type if instance_type else record.instance_type)

    return instance_type


def find_candidates_and_regions(highlight_type, dataset):
    """Find candidates by highlight_type & regions per candidate ."""
    instance_candidates, regions = [], {}
    for record in dataset:
        instance_type = find_instance_type(highlight_type, record)
        if instance_type is None:
            continue
        instance_candidates.append(instance_type)
        if instance_type not in regions:
            regions[instance_type] = []
        if record.region not in regions[instance_type]:
            regions[instance_type].append(record.region)

    return instance_candidates, regions


def highlights_instance_types(queryset, highlight_type):
    values_dict, highlights_list = {}, []
    candidates, regions_by_type = find_candidates_and_regions(
        highlight_type, queryset)

    if candidates:
        # Creates a dict with {value: count} values sorts the same, DESC order
        values_dict = dict(sorted(Counter(candidates).items(), key=lambda x: x[1], reverse=True))

    item_count = 1
    for key, value in values_dict.items():
        if item_count == 5:
            break

        highlights_list.append({
            "type": key,
            "count": value,
            # file will differ w.r.t. instance_type properties as per cloud_provider value
            "desc": generate_highlight_description(
                key, 'AWS', regions_by_type.get(key))
        })
        item_count += 1

    return highlights_list


def system_allowed_in_ros(msg, reporter):
    is_ros = False
    cloud_provider = ''
    operating_system = ''
    if reporter == 'INSIGHTS ENGINE':
        is_ros = msg["input"]["platform_metadata"].get("is_ros")
        cloud_provider = msg["results"]["system"]["metadata"].get("cloud_provider")
        operating_system = msg["input"]["host"]["system_profile"].get("operating_system")
    elif reporter == 'INVENTORY EVENTS':
        cloud_provider = msg["host"]["system_profile"].get("cloud_provider")
        operating_system = msg["host"]["system_profile"].get("operating_system")
        # Note that 'is_ros' ONLY available when payload uploaded
        # via insights-client. 'platform_metadata' field not included
        # when the host is updated via the API.
        # https://consoledot.pages.redhat.com/docs/dev/services/inventory.html#_updated_event
        if (
                msg.get('type') == 'updated'
                and is_platform_metadata_empty(msg)
        ):
            return is_valid_cloud_provider(cloud_provider)
        is_ros = msg["platform_metadata"].get("is_ros")
    return validate_ros_payload(is_ros, cloud_provider, operating_system)


def is_platform_metadata_empty(msg):
    if msg.get("platform_metadata") is None or \
            (isinstance(msg.get("platform_metadata"), dict) and
             len(msg.get("platform_metadata")) < 1 and
             "b64_identity" in msg.get("platform_metadata")):
        return True

    return False
