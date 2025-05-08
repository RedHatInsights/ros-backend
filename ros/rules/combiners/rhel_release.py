"""
RhelRelease - Combiner
======================
It combines the result of `Uname`, `RedhatRlease`, and `LsCPU` parsers, to
ensure the checking target is a `RHEL` host.

It checks the `Uname` at first, only when the `Uname` parser is not available,
checks the `RedhatRelease`.

The `LsCPU` parser is an optional condition to this combiner for the favor of
getting the `Architecture` of the host.

"""
# Insights core functionality
from insights import SkipComponent
from insights.core.plugins import combiner

# System parsers
from insights.parsers.lscpu import LsCPU
from insights.parsers.redhat_release import RedhatRelease
from insights.parsers.uname import Uname

# TODO: Update when new RHEL is GA
# https://access.redhat.com/downloads/content/package-browser -> kernel
SUPPORTED_RHEL = {
    'aarch64': [7, 8, 9],
    'ppc64': [7],
    'ppc64le': [7, 8, 9],
    's390x': [7, 8, 9],
    'x86_64': [7, 8, 9],
}
"""The supported RHEL major releases for Advisor rules."""


@combiner([Uname, RedhatRelease], optional=[LsCPU])
class RhelRelease(object):
    """
    Combiner for the supported RHEL Release.

    Attributes:
        major (int): The major RHEL Release
        minor (int): The minor RHEL Release
        rhel (str): The RHEL Release, e.g. '9.2'.  Never be `None`.
        rhel# (str): The RHEL Release for RHEL #, it's the same as ``rhel``.
            The '#' can be one the supported RHEL Major versions.  `None` when
            it's not the specified `rhel#`.
        arch (str): The architecture of the RHEL.

    Raises:
        SkipComponent: When it's not a supported RHEL
    """

    def __init__(self, uname, rh_rel, lscpu):
        rhel = uname.redhat_release if uname else rh_rel
        # Unknown Uname
        if rhel.major == -1:
            raise SkipComponent
        self.major, self.minor = rhel.major, rhel.minor
        self.rhel = f'{self.major}.{self.minor}'
        # Default x86_64
        self.arch = uname.arch if uname else lscpu.info.get('Architecture') if lscpu else 'x86_64'
        # Not supported RHEL
        reqs = SUPPORTED_RHEL.get(self.arch, SUPPORTED_RHEL.get('x86_64'))
        if rhel.major not in reqs:
            raise SkipComponent
        # Set the self.rhel#
        for rel in reqs:
            setattr(self, f'rhel{rel}', self.rhel if self.major == rel else None)
