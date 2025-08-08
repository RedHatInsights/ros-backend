from math import isclose
from functools import reduce
from collections import namedtuple, defaultdict

from insights import (
    run as insights_run,
    SkipComponent,
    add_filter
)
from insights.core.plugins import (
    make_metadata,
    make_fail,
    rule,
    condition,
    parser
)
from insights.core.spec_factory import SpecSet, simple_file
from insights.parsers.lscpu import LsCPU
from insights.parsers.cmdline import CmdLine
from insights.parsers.insights_client_conf import InsightsClientConf
from insights.parsers.pmlog_summary import PmLogSummaryBase
from insights.parsers.azure_instance import AzureInstanceType
from insights.parsers.aws_instance_id import AWSInstanceIdDoc
from insights.combiners.cloud_provider import CloudProvider

from ros.rules.combiners.rhel_release import RhelRelease
from ros.rules.helpers import Ec2LinuxPrices
from ros.lib.aws_instance_types import INSTANCE_TYPES as EC2_INSTANCE_TYPES
from ros.rules.helpers.rules_data import RosThresholds, RosKeys

add_filter(InsightsClientConf, ['ros_collect'])
ERROR_KEY_NO_DATA = "NO_PCP_DATA"
ERROR_KEY_IDLE = "INSTANCE_IDLE"
ERROR_KEY_OVERSIZED = "INSTANCE_OVERSIZED"
ERROR_KEY_UNDERSIZED = "INSTANCE_UNDERSIZED"
ERROR_KEY_UNDER_PRESSURE = "INSTANCE_OPTIMIZED_UNDER_PRESSURE"
LINKS = {
    "jira": [
        "https://issues.redhat.com/browse/CEECBA-5875",
    ],
    "kcs": [],  # No KCS or doc yet
}


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------
CloudInstance = namedtuple('CloudInstance', ['provider', 'type', 'mic', 'region'])


class RosPmlogsummary(SpecSet):
    pmlogsummary = simple_file("pmlogsummary")


@parser(RosPmlogsummary.pmlogsummary)
class PmLogSummaryRules(PmLogSummaryBase):
    """
    Parser to parse the content of `pmlog_summary` spec.
    """
    pass


def readable_evalution(ret):
    ERROR_KEYs = [
        (ERROR_KEY_IDLE, all, (RosKeys.IDLE,)),
        (ERROR_KEY_UNDERSIZED, any, (RosKeys.CPU_UNDERSIZED,
                                     RosKeys.MEMORY_UNDERSIZED,
                                     RosKeys.IO_UNDERSIZED)),
        # FIXED: CHANGED FROM 'all' TO 'any' - IF ANY RESOURCE IS OVERSIZED,
        # THE SYSTEM SHOULD BE CLASSIFIED AS OVERSIZED (CONSISTENT WITH UNDERSIZED LOGIC)
        (ERROR_KEY_OVERSIZED, any, (RosKeys.CPU_OVERSIZED,
                                    RosKeys.MEMORY_OVERSIZED,
                                    RosKeys.IO_OVERSIZED)),
        (ERROR_KEY_UNDER_PRESSURE, any, (RosKeys.CPU_UNDERSIZED_BY_PRESSURE,
                                         RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE,
                                         RosKeys.IO_UNDERSIZED_BY_PRESSURE)),
    ]
    COMP_KEYs = [
        # FIXME: RosKeys.IDLE -> idle?
        ('idle', (RosKeys.IDLE,)),
        ('cpu', (RosKeys.CPU_IDLING,
                 RosKeys.CPU_OVERSIZED,
                 RosKeys.CPU_UNDERSIZED,
                 RosKeys.CPU_UNDERSIZED_BY_PRESSURE)),
        ('memory', (RosKeys.MEMORY_OVERSIZED,
                    RosKeys.MEMORY_UNDERSIZED,
                    RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE)),
        ('io', (RosKeys.IO_OVERSIZED,
                RosKeys.IO_UNDERSIZED,
                RosKeys.IO_UNDERSIZED_BY_PRESSURE)),
    ]

    err_key = None
    for EK, func, KEYs in ERROR_KEYs:
        if func(ret & k for k in KEYs):
            # FIXME: "ERROR_KEY_OVERSIZED" -> NOT test yet due to IOPS issue
            err_key = EK
            break

    states = defaultdict(list)
    for m, KEYs in COMP_KEYs:
        for k in KEYs:
            states[m].append(k.name) if ret & k else None
        # Exclude other states when 'idle'
        if 'idle' in states:
            break
    return err_key, dict(states)


# ---------------------------------------------------------------------------
# Conditions
# ---------------------------------------------------------------------------
@condition(CloudProvider, [AWSInstanceIdDoc, AzureInstanceType])
def cloud_metadata(cp, aws, azure):
    """
    Returns: CloudInstance
    """
    # FIXME:
    # 1: NO mic (IOPS issue)
    # 2: NO region for Azure
    if cp.cloud_provider in (cp.AWS,):
        _type, mic, region = (
                aws['instanceType'],
                None,
                aws['region']) if aws else (azure.raw, None, None)
        return CloudInstance(cp.cloud_provider, _type, mic, region)
    raise SkipComponent


@condition(optional=[InsightsClientConf, PmLogSummaryRules])
def no_pmlog_summary(cli_cfg, new_pm):
    # Any of:
    # 1. RosConfig is enabled
    # 2. "ros_collect=True" is set
    if (cli_cfg and
            cli_cfg.has_option("insights-client", "ros_collect") and
            cli_cfg.getboolean("insights-client", "ros_collect") and new_pm is None):
        # BUT PmLogSummary is Empty
        return ERROR_KEY_NO_DATA
    raise SkipComponent


@condition([PmLogSummaryRules], optional=[LsCPU])
def cpu_utilization(new_pm, lscpu):
    pls = new_pm
    try:
        # Get ncpu from PmLogSummary at first, then LsCPU
        ncpu = pls.get('hinv', {}).get('ncpu', {}).get('val')
        ncpu = float(lscpu.info['CPUs']) if ncpu is None and lscpu else float(ncpu)
        idle = float(pls['kernel']['all']['cpu']['idle']['val'])
        cpu_ut = 1.0 - idle / ncpu
        return cpu_ut, idle
    except Exception:
        raise SkipComponent("No 'cpu' data")


@condition([PmLogSummaryRules])
def mem_utilization(new_pm):
    pls = new_pm
    try:
        physmem = float(pls['mem']['physmem']['val'])
        available = float(pls['mem']['util']['available']['val'])
        in_use = (physmem - available)
        mem_ut = in_use / physmem
        return mem_ut, in_use
    except Exception:
        raise SkipComponent("No 'mem' data")


@condition([PmLogSummaryRules], cloud_metadata)
def io_utilization(new_pm, cm):
    pls = new_pm
    try:
        io_ut = {}
        dev_total = pls['disk']['dev']['total']
        for dev, val in dev_total.items():
            # FIXME
            # Do not calculate or use disk (IOPS) percentage utilization,
            # since we do not have the actual max IOPS
            # io_ut[dev] = float(val['val']) / cm.mic
            io_ut[dev] = float(val['val'])
        return io_ut
    except Exception:
        raise SkipComponent("No 'disk.dev.total' data")


@condition(CmdLine)
def psi_enabled(cmdline):
    return 'psi' in cmdline and cmdline['psi'][-1] == '1'


@condition(psi_enabled, [PmLogSummaryRules])
def psi_utilization(psi, new_pm):
    if not psi:
        raise SkipComponent("PSI not enabled")
    pls = new_pm
    try:
        return (
            # io_avg_pressure, 0
            float(pls['kernel']['all']['pressure']['io']['some']['avg']['1 minute']['val']),
            # io_full_pressure, 1
            float(pls['kernel']['all']['pressure']['io']['full']['avg']['1 minute']['val']),
            # cpu_avg_pressure, 2
            float(pls['kernel']['all']['pressure']['cpu']['some']['avg']['1 minute']['val']),
            # mem_avg_pressure, 3
            float(pls['kernel']['all']['pressure']['memory']['some']['avg']['1 minute']['val']),
            # mem_full_pressure, 4
            float(pls['kernel']['all']['pressure']['memory']['full']['avg']['1 minute']['val']),
        )
    except Exception:
        raise SkipComponent("No PSI Data")


@condition(optional=[cpu_utilization, mem_utilization])
def idle_evaluation(cpu, mem):
    if (
            cpu is not None and
            cpu[0] < RosThresholds.CPU_UTILIZATION_CRITICAL_LOWER_THRESHOLD and
            mem is not None and
            mem[0] < RosThresholds.MEMORY_UTILIZATION_CRITICAL_LOWER_THRESHOLD
    ):
        # print('idle')
        return RosKeys.IDLE
    return RosKeys.OPTIMIZED


@condition(optional=[cpu_utilization])
def cpu_evaluation(cpu_ut):
    ret = RosKeys.OPTIMIZED
    idle = 0
    if cpu_ut is not None:
        cpu_ut, idle = cpu_ut
        if cpu_ut > RosThresholds.CPU_UTILIZATION_WARNING_UPPER_THRESHOLD:
            ret |= RosKeys.CPU_UNDERSIZED
        elif cpu_ut < RosThresholds.CPU_UTILIZATION_WARNING_LOWER_THRESHOLD:
            ret |= RosKeys.CPU_OVERSIZED
    # print('cpu', ret, idle)
    return ret, idle


@condition(optional=[mem_utilization])
def mem_evaluation(mem_ut):
    ret = RosKeys.OPTIMIZED
    in_use = 0
    if mem_ut is not None:
        mem_ut, in_use = mem_ut
        if mem_ut > RosThresholds.MEMORY_UTILIZATION_WARNING_UPPER_THRESHOLD:
            ret |= RosKeys.MEMORY_UNDERSIZED
        elif mem_ut < RosThresholds.MEMORY_UTILIZATION_WARNING_LOWER_THRESHOLD:
            ret |= RosKeys.MEMORY_OVERSIZED
    # print('mem', ret, in_use)
    return ret, in_use


@condition(optional=[io_utilization])
def io_evaluation(io_ut):
    ret = RosKeys.OPTIMIZED
    """
    # FIXME
    # Do not calculate or use disk (IOPS) percentage utilization,
    # since we do not have the actual max IOPS
    if io_ut is not None:
        for dev, val in io_ut.items():
            if val > RosThresholds.IO_UTILIZATION_WARNING_UPPER_THRESHOLD:
                ret |= RosKeys.IO_UNDERSIZED
            elif val < RosThresholds.IO_UTILIZATION_WARNING_LOWER_THRESHOLD:
                ret |= RosKeys.IO_OVERSIZED
        # Whenever there is at least one undersized condition, state is undersized.
        if ret & RosKeys.IO_UNDERSIZED:
            ret &= ~RosKeys.IO_OVERSIZED
    """
    # print('io', ret)
    return ret


@condition(optional=[psi_utilization])
def psi_evaluation(psi_ut):
    ret = RosKeys.OPTIMIZED
    if psi_ut is not None:
        # mem_avg_pressure, mem_full_pressure
        if (psi_ut[3] > RosThresholds.MEMORY_PRESSURE_UPPER_AVERAGE_THRESHOLD or
                psi_ut[4] > RosThresholds.MEMORY_PRESSURE_FULL_THRESHOLD):
            ret |= RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE
        # cpu_avg_pressure
        if psi_ut[2] > RosThresholds.CPU_PRESSURE_UPPER_AVERAGE_THRESHOLD:
            ret |= RosKeys.CPU_UNDERSIZED_BY_PRESSURE
        # io_avg_pressure, io_full_pressure
        if (psi_ut[0] > RosThresholds.IO_PRESSURE_UPPER_AVERAGE_THRESHOLD or
                psi_ut[1] > RosThresholds.IO_PRESSURE_FULL_THRESHOLD):
            ret |= RosKeys.IO_UNDERSIZED_BY_PRESSURE
    # print('psi', ret)
    return ret


# ---------------------------------------------------------------------------
# Logics
# ---------------------------------------------------------------------------
@condition(cloud_metadata, cpu_evaluation, psi_evaluation)
def cpu_candidates(cm, cpu_ut, psi_ut):
    ut = cpu_ut[0] | psi_ut

    cur_inst = EC2_INSTANCE_TYPES.get(cm.type)
    inst_vcpu = float(cur_inst["extra"]["vcpu"])
    inst_phyp = cur_inst["extra"]["physicalProcessor"]
    in_use = inst_vcpu - cpu_ut[1]

    candidates = set()
    for ci, cd in EC2_INSTANCE_TYPES.items():
        # Skip the current instance
        if ci == cm.type:
            continue
        if cd["extra"]["physicalProcessor"] != inst_phyp:
            continue
        cand_vcpu = float(cd["extra"]["vcpu"])
        cand_vcpu_ev = cand_vcpu * RosThresholds.CPU_UTILIZATION_WARNING_UPPER_THRESHOLD
        # print(cand_vcpu, cand_vcpu_ev, in_use)
        if not (cand_vcpu_ev > in_use or isclose(cand_vcpu_ev, in_use)):
            continue
        # CPU_UNDERSIZED _OR_ CPU_UNDERSIZED_BY_PRESSURE
        if ut & RosKeys.CPU_UNDERSIZED or ut & RosKeys.CPU_UNDERSIZED_BY_PRESSURE:
            # print(cand_vcpu, inst_vcpu, cand_vcpu > inst_vcpu or isclose(cand_vcpu, inst_vcpu))
            if cand_vcpu > inst_vcpu or isclose(cand_vcpu, inst_vcpu):
                candidates.add(ci)
        # CPU_OVERSIZED
        elif ut & RosKeys.CPU_OVERSIZED:
            if cand_vcpu < inst_vcpu or isclose(cand_vcpu, inst_vcpu):
                candidates.add(ci)
        else:
            candidates.add(ci)
    # print('cpu_cand', len(candidates))
    return ut, candidates


@condition(cloud_metadata, [mem_evaluation, psi_evaluation])
def mem_candidates(cm, mem_ut, psi_ut):
    ut = mem_ut[0] | psi_ut

    cur_inst = EC2_INSTANCE_TYPES.get(cm.type)
    inst_mem = float(cur_inst['ram'] * 1024)
    in_use = mem_ut[1]

    candidates = set()
    for ci, cd in EC2_INSTANCE_TYPES.items():
        # Skip the current instance
        if ci == cm.type:
            continue
        cand_mem = float(cd['ram'] * 1024)
        if not (cand_mem * RosThresholds.MEMORY_UTILIZATION_WARNING_UPPER_THRESHOLD >= in_use):
            continue
        # MEM_UNDERSIZED _OR_ MEMORY_UNDERSIZED_BY_PRESSURE
        if ut & RosKeys.MEMORY_UNDERSIZED or ut & RosKeys.MEMORY_UNDERSIZED_BY_PRESSURE:
            if cand_mem > inst_mem or isclose(cand_mem, inst_mem):
                candidates.add(ci)
        # MEM_OVERSIZED
        elif ut & RosKeys.MEMORY_OVERSIZED:
            if cand_mem < inst_mem or isclose(cand_mem, inst_mem):
                candidates.add(ci)
        else:
            candidates.add(ci)
    # print('mem_cand', len(candidates))
    return ut, candidates


# FIXME:
# Return all here for now
@condition(cloud_metadata, io_evaluation)
def io_candidates(cm, io_ut):
    # print('io_cand', len(EC2_INSTANCE_TYPES.keys()))
    return io_ut, set(EC2_INSTANCE_TYPES.keys())


@condition(cloud_metadata,
           cpu_candidates, mem_candidates, io_candidates,
           idle_evaluation, psi_evaluation)
def find_solution(cm, cpu, mem, io, idle, psi):
    ret = reduce(lambda x, y: x | y, [cpu[0], mem[0], io[0], idle, psi])
    solution = reduce(lambda x, y: x & y, [cpu[1], mem[1], io[1]])
    err_key, states = readable_evalution(ret)
    if err_key and solution:
        solution_w_price = list()
        cur_price = Ec2LinuxPrices().get(cm.type, {}).get(cm.region, 0)
        for can in solution:
            price = Ec2LinuxPrices().get(can, {}).get(cm.region)
            if err_key in (ERROR_KEY_IDLE, ERROR_KEY_OVERSIZED):
                # When IDLE/OVERSIZED, skip the candidates more expansive than the current
                solution_w_price.append((can, price)) if price <= cur_price else None
            else:
                solution_w_price.append((can, price))
        # sort with name at first and then price
        solution_w_price = sorted(solution_w_price, key=lambda x: (x[1], x[0]))

        if solution_w_price:
            return err_key, cur_price, states, solution_w_price

    # Not reach
    raise SkipComponent


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
@rule(RhelRelease, cloud_metadata,
      optional=[psi_enabled, cpu_utilization,
                mem_utilization, io_utilization], links=LINKS)
def report_metadata(rhel, cloud, psi, cpu, mem, io):
    ret = dict(cloud_provider=cloud.provider)
    ret.update(cpu_utilization=f'{round(cpu[0] * 100)}') if cpu else None
    ret.update(mem_utilization=f'{round(mem[0] * 100)}') if mem else None
    ret.update(io_utilization={k: f'{v:.3f}' for k, v in io.items()}) if io else None
    ret.update(psi_enabled=psi) if psi is not None else None
    return make_metadata(**ret)


@rule(RhelRelease, cloud_metadata, find_solution, links=LINKS)
def report(rhel, cloud, solution):
    ret_dict = dict(
        rhel=rhel.rhel,
        cloud_provider=cloud.provider,
        instance_type=cloud.type,
        region=cloud.region,
        price=solution[1],
        candidates=solution[3],
    )
    ret_dict.update(states=solution[2]) if solution[2] else None
    return make_fail(solution[0], **ret_dict)


def run_rules(extracted_dir_root):
    rules = [report_metadata, report]
    result = insights_run(rules, root=extracted_dir_root)
    return result
