import sys, os

# import massif parser from its repo
# clone this repo: https://github.com/MathieuTurcotte/msparser
# should install msparser rather than cloning at somepoint
sys.path.append('msparser/')
import msparser

# benchmarking params
n_rounds = 3
gridsizes = [40, 240]
# something for number of chemistry sites


# ================ USAGE ================ 
def print_usage(opt):
    if opt:
        print(f'Error: unknown option \'{opt}\'')
    usage = \
    'Usage: python3 Benchmark.py [option] [cmd]\n'+ \
    '   options:\n'+ \
    '       time - benchmark runtime\n'+ \
    '       mem  - profile memory usage\n'+ \
    '       cpu  - profile cpu usage\n'+ \
    '       all  - benchmark all options\n'+ \
    '       help - display usage'
    print(usage)

# ================ TIMING ================ 
def time_cmd(cmd):
    print(f'timing \'{cmd}\'')
    export_time_data()

def export_time_data():
    print('exporting time data')


# ================ MEMORY ================ 
def profile_memory(cmd):
    print(f'\nProfiling memory usage of \'{cmd}\'.\n')
    profile_cmd_pref = (
        'valgrind '
        '--tool=massif '            # heap profiler tool
        '--time-unit=ms '           # profiling time unit in milliseconds
        '--pages-as-heap=yes '
        '--detailed-freq=1000000 '     # disable detailed snapshots
        '--depth=1 '                # max depth of allocation trees for deatiled snapshots
    )

    # independent var: system hardware
    for round in range(n_rounds):
        profile_cmd = (
            profile_cmd_pref +
            f'--massif-out-file=data/mem/sys-{round} '
            f'{cmd}'
        )
        os.system(profile_cmd)
        print(f'[Round {round}]: profiled memory usage of \'{cmd}\'.\n')

    # independent var: gridsize
    for gridsize in gridsizes:
        for round in range(n_rounds):
            profile_cmd = (
                profile_cmd_pref +
                f'--massif-out-file=data/mem/gridsize-{gridsize}-{round} '
                f'{cmd} {gridsize}'
            )
            os.system(profile_cmd)
            print(f'[Round {round}]: profiled memory usage of \'{cmd}\'.\n')
    
    # independent var: chemistry sites
    
    export_memory_data()

def export_memory_data():
    print('exporting memory data')


# ================ CPU ================ 
def profile_cpu(cmd):
    print(f'profiling cpu usage of \'{cmd}\'')
    export_cpu_data()

def export_cpu_data():
    print('exporting cpu data')


# ================ MAIN ================ 
def main(argv):
    # cmd line args error handling
    try:
        option = argv[1]
        assert option == 'help' or len(argv) > 2
    except:
        print_usage(None)
        sys.exit(1)

    cmd = ' '.join(argv[2:])    # the string representing the command to benchmark

    # option handling
    if option == 'time':
        time_cmd(cmd)
    elif option == 'mem':
        profile_memory(cmd)
    elif option == 'cpu':
        profile_cpu(cmd)
    elif option == 'all':
        time_cmd(cmd)
        profile_memory(cmd)
        profile_cpu(cmd)
    elif option == 'help':
        print_usage(None)
    else:
        print_usage(option)


if __name__ == '__main__':      # entry point
    main(sys.argv)