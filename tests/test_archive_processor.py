from unittest import mock

from ros.processor.process_archive import performance_profile

EXPECTED_PERFORMANCE_RECORD = {
    'disk.dev.total': {'nvme0n1': {'units': 'count / sec', 'val': 7.22}},
    'hinv.ncpu': 8.0,
    'instance_type': 't2.micro',
    'kernel.all.cpu.idle': 7.55,
    'kernel.all.pressure.cpu.some.avg': {
        '1 minute': {'units': 'none', 'val': 0.575},
        '10 second': {'units': 'none', 'val': 0.579},
        '5 minute': {'units': 'none', 'val': 0.572}
    },
    'kernel.all.pressure.io.full.avg': {
        '1 minute': {'units': 'none', 'val': 0.006},
        '10 second': {'units': 'none', 'val': 0.012},
        '5 minute': {'units': 'none', 'val': 0.004}
    },
    'kernel.all.pressure.io.some.avg': {
        '1 minute': {'units': 'none', 'val': 0.006},
        '10 second': {'units': 'none', 'val': 0.013},
        '5 minute': {'units': 'none', 'val': 0.004}
    },
    'kernel.all.pressure.memory.full.avg': {
        '1 minute': {'units': 'none', 'val': 0.0},
        '10 second': {'units': 'none', 'val': 0.0},
        '5 minute': {'units': 'none', 'val': 0.0}
    },
    'kernel.all.pressure.memory.some.avg': {
        '1 minute': {'units': 'none', 'val': 0.0},
        '10 second': {'units': 'none', 'val': 0.0},
        '5 minute': {'units': 'none', 'val': 0.0}
    },
    'mem.physmem': 32617072.0,
    'mem.util.available': 27455175.254,
    'total_cpus': 1,
    'type': 'metadata'
}


def test_performance_profile_response():
    # test setup
    lscpu = mock.Mock()
    setattr(lscpu, 'info', {'CPUs': '1'})
    aws_instance_id = {'instanceType': 't2.micro'}
    sample_pmlog_summary = {
      'hinv': {'ncpu': {'val': 8.0, 'units': 'none'}},
      'mem': {
        'physmem': {'val': 32617072.0, 'units': 'Kbyte'},
        'util': {'available': {'val': 27455175.254, 'units': 'Kbyte'}}
      },
      'disk': {'dev': {'total': {'nvme0n1': {'val': 7.22, 'units': 'count / sec'}}}},
      'kernel': {
        'all': {
          'cpu': {'idle': {'val': 7.55, 'units': 'none'}},
          'pressure': {'cpu': {'some': {
            'avg': {
                '10 second': {'val': 0.579, 'units': 'none'},
                '1 minute': {'val': 0.575, 'units': 'none'},
                '5 minute': {'val': 0.572, 'units': 'none'}
                }
              }
            },
            'io': {
                'full': {'avg': {
                    '10 second': {'val': 0.012, 'units': 'none'},
                    '1 minute': {'val': 0.006, 'units': 'none'},
                    '5 minute': {'val': 0.004, 'units': 'none'}}
                },
                'some': {'avg': {
                    '10 second': {'val': 0.013, 'units': 'none'},
                    '1 minute': {'val': 0.006, 'units': 'none'},
                    '5 minute': {'val': 0.004, 'units': 'none'}}
                }
            },
            'memory': {
              'full': {'avg': {
                  '10 second': {'val': 0.0, 'units': 'none'},
                  '1 minute': {'val': 0.0, 'units': 'none'},
                  '5 minute': {'val': 0.0, 'units': 'none'}
                }
              },
              'some': {'avg': {
                  '10 second': {'val': 0.0, 'units': 'none'},
                  '1 minute': {'val': 0.0, 'units': 'none'},
                  '5 minute': {'val': 0.0, 'units': 'none'}
              }
              }
            }
          }
        }
      }
    }
    generated_performance_record = performance_profile(lscpu, aws_instance_id, None, sample_pmlog_summary)
    assert generated_performance_record == EXPECTED_PERFORMANCE_RECORD
