from contextlib import contextmanager
from tempfile import NamedTemporaryFile
import requests

from insights import extract, run, rule, make_metadata
from insights.parsers import uname
from io import open
import sys


@contextmanager
def unpacked_remote_archive(url):
    """ Work with remote archive ( download + unpack )"""
    try:
        with NamedTemporaryFile() as file:
            resp = requests.get(url)
            file.write(resp.content)
            file.flush()
            with extract(file.name) as extracted:
                yield extracted
    except BaseException as e:
        print("Error extracting insights archive %s" % e)
    finally:
        pass


@contextmanager
def unpacked_local_archive(path):
    """ Work with local archive for unpacking, Used for testing"""
    try:
        with NamedTemporaryFile() as file:
            file.write(open(path, 'rb').read())
            file.flush()
            with extract(file.name) as extracted:
                yield extracted
    except BaseException as e:
        print("Error extracting insights archive %s" % e)
    finally:
        pass


# Use uname for now, just getting the architecture down
@rule(uname.Uname)
def pcp_stats(uname):
    stats = {}

    if uname:
        try:
            stats['uname'] = uname
            stats['arch'] = uname.arch
        finally:
            pass

    resp = make_metadata()
    resp.update(stats)
    return resp


def process_archive(path):
    """ Take an unpacked archive, and run our custom rule on it"""
    try:
        parsed = run(pcp_stats, root=path)
        result = parsed[pcp_stats]
        return result
    except BaseException as e:
        print("Error running insights parser", e)


def process_message(msg):
    """ Process the create/update message from insights, and run whole process on this archive"""
    with unpacked_remote_archive(msg['platform_metadata']['url']) as unpacked:
        return process_archive(unpacked.tmp_dir)


if __name__ == "__main__":
    with unpacked_local_archive(sys.argv[1]) as archive:
        res = process_archive(archive.tmp_dir)
        print("Resulted archive evaluation", res)