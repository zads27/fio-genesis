#! /usr/bin/env python
"""Run fio and log BW/IOPS to a file
"""
import sys
import subprocess
import os
import re
import argparse
SCRIPTDIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))


def to_number(mstring):
    """Convert strings like 13.9k or 1733MiB/s to numbers"""
    if mstring == '0':
        return 0
    m = re.match(r'([\d\.]+)(.*)', mstring)
    if m:
        # print 'to_number: groups', m.group(1), m.group(2)
        v = float(m.group(1))
        units = m.group(2)
        if units == 'MiB/s':
            return v * 1.024 * 1.024    # Mbps
        elif units == 'KiB/s':
            return v * 0.001024    # Mbps
        elif units == 'k':
            return v*1000          # kIOPS
        elif units == '':
            return v
    else:
        raise ValueError('unknown units %s' % mstring)


def get_value(line, value='iops'):
    """Parse continuous fio output and get requested value"""
    # jobs: 1 (f=1): [R(1)][1.2%][r=1733MiB/s,w=0KiB/s][r=13.9k,w=0 IOPS][eta 59m:17s]
    if value == 'iops':
        pattern = r'\[r=([^,]+),w=([^\]]+)\s+IOPS\]'
    else:
        pattern = r'\[r=([^,]+),w=([^\]]+)\]'
    m = re.search(pattern, line)
    if m:
        # print 'get_value: groups', m.group(1), m.group(2)
        r, w = to_number(m.group(1)), to_number(m.group(2))
        return '%.2f' % ((r + w)/1000)
    return '0.00' 


def run_fio_process(command, filename, value='iops'):
    """Run the fio process and monitor the bandwidth or iops"""
    outfile = os.path.join(SCRIPTDIR, '..', '%s.txt' % filename)
    try:
        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=False)
        while True:
            nextline = p.stdout.readline()
            if nextline == '' and p.poll is not None:
                break
            sys.stdout.write(nextline)
            with open(outfile, 'w') as of:
                of.write(get_value(nextline, value))
    except KeyboardInterrupt:
        sys.exit(1)


def main():
    """Runs FIO and parses output"""
    fio = os.path.join(SCRIPTDIR, 'fio')
    command = [fio, args.jobfile, '--eta=always']
    if re.search('128k', args.jobfile):
        value = 'bw'
    else:
        value = 'iops'
    filename = args.jobfile.replace(r'.fio', '')
    print filename
    run_fio_process(command, filename, value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-j', '--jobfile', type=str, default=None)
    args = parser.parse_args()

    if not args.jobfile:
        print 'ERROR: Need --jobfile argument.'
        sys.exit(1)
    else:
        main()
