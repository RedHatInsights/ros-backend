from ros.lib.aws_instance_types import INSTANCE_TYPES


def instance_types_desc_dict():
    instance_and_descriptions = {}
    for instance, info in INSTANCE_TYPES.items():
        processor = info['extra']['physicalProcessor']
        v_cpu = info['extra']['vcpu']
        memory = info['extra']['memory']
        instance_and_descriptions[instance] = f"{processor} instance with {v_cpu} vCPUs and {memory} RAM"
    return instance_and_descriptions
