import sys              # exiting
import os               # forking and waiting
import subprocess       # running cmds
import time             # sleeping
import pandas           # csv exporting
import numpy            # nan value


# ================ PARAMETERS ================ 
""" The number of rounds to run the simulation for a given independent variable.
This MUST be ONE in order for the formatting to work, otherwise you'll have
format dozens of csv files by hand or write your own script to do so. """
g_rounds = 1

""" The constant gridsize at which to benchmark hardware against the
dependent variables. Should be 1000 unless Seagate suggests otherwise. """
g_hardware_gridsize = 1000

""" The constant hardware (machine) on which to benchmark gridsize against
the dependent variables. I'd recommend using the best machine you can access
to speed up the scripts runtime. """
g_gridsize_machine = 'csel-kh1250-13'

""" The gridsizes at which to benchmark against the dependent variables. Make
sure this includes 1000 unless Seagate suggests otherwise. """
g_gridsizes = [ i for i in range(500, 1600, 100) ]

""" The interval at which data points are obtained. Every g_ping_interval
seconds a new data point is pinged. """
g_ping_interval = 0.07       # in seconds
# something for number of chemistry sites

""" possible target metrics, the ordering depends on the user's top configuration
these indexes will not be accurate if the given toprc is not used! """
g_targets = {   # see https://man7.org/linux/man-pages/man1/top.1.html for explanation
    'pid': 1,
    'virt': 2,
    'res': 3,
    'shr': 4,
    '%cpu': 5,
    '%mem': 6,
    'time+': 7,
    'command': 8,
    'swap': 9,
    'data': 10
}
g_memory_targets = ['virt', 'res', 'shr', 'swap', 'data']


# ================ USAGE ================ 
def print_usage(opt):
    if opt:
        print(f'Error: unknown option \'{opt}\'')
    usage = \
    'Usage: python3 Benchmark.py [option] [cmd]\n'+ \
    '   options:\n'+ \
    '       all  - benchmark all options\n'+ \
    '       help - display usage'
    print(usage)


# ================ PINGING ================ 
def get_pings(cmd, gridsize, target_metrics):
    # organizing simple state machine
    simulation_states = ['waiting', 'running', 'done']
    sim_state = simulation_states[0]

    sim_pid = ''    # string representation of the simulations pid
    pings = []      # list of pings; (cpu_run_time, target_metric_0, ... target_metric_N)

    while sim_state == 'waiting' or sim_state == 'running':

        if sim_state == 'waiting':
            # check if the simulation process started running
            completed_process = subprocess.run(f'pgrep -a python3', shell=True, capture_output=True)
            if f'{cmd} {gridsize}' in completed_process.stdout.decode().strip():
                # parse pgrep stdout for simulation's pid
                lines = completed_process.stdout.decode().strip().split('\n')
                sim_pid = ''
                for line in lines:
                    if cmd in line:
                        sim_pid = line.split(' ')[0]
                # set sim_state to running
                sim_state = simulation_states[1]

        elif sim_state == 'running':
            ping = ping_top(sim_pid, target_metrics) 
            if ping:    # if ping succeeds add it to the list of pings
                pings.append(ping)
            # check if the simulation process stopped running
            completed_process = subprocess.run(f'pgrep -a python3', shell=True, capture_output=True)
            if f'{cmd} {gridsize}' not in completed_process.stdout.decode().strip():
                sim_state = simulation_states[2]
        
        time.sleep(g_ping_interval)     # don't spam pings
    
    return pings

def ping_top(sim_pid, target_metrics):
    ping = None
    awk_cmd = (             # format awk portion of ping command
        'awk \'{print ' +
        # '$target_index_0, ... $target_index_N'
        ', '.join(['${0}'.format(g_targets[target]) for target in target_metrics]) +
        '}\''
    )
    ping_cmd = (            # format ping command
        'top -b '           # run top in batch mode
        '-n 2 '             # run 2 iterations
        '-d 0.1 '           # dt = .1 sec
        f'-p {sim_pid} | '  # only show data for sim process id
        'tail -1 | ' +      # get the last line of the output
        awk_cmd
    )

    completed_process = subprocess.run(ping_cmd, shell=True, capture_output=True)
    string_metric = completed_process.stdout.decode().strip()

    """ If you ping top with a dead pid it does not error, nor print to stderr,
        afaik the only way to detect when this happens is to check if the
        grabbed strings are the column headers, i.e., contain no digits """
    if any(char.isdigit() for char in string_metric):
        string_list_metric = string_metric.split(' ')

        # ensure memory metrics are in Gibibytes
        for i, target_metric in enumerate(target_metrics):
            if target_metric in g_memory_targets:
                string_mem_metric = string_list_metric[i]
                suffix = string_mem_metric[-1]
                
                if suffix.isdigit():      # no suffix: kibi
                    string_list_metric[i] = str(round((float(string_mem_metric) * 9.5367431640625e-7), 3))
                elif suffix == 'm':       # m: mebi
                    string_list_metric[i] = str(round((float(string_mem_metric[:-1]) * 0.000976563), 3))
                elif suffix == 'g':       # g: gibi
                    string_list_metric[i] = string_list_metric[i][:-1]
                elif suffix == 't':       # t: tebi
                    string_list_metric[i] = str(round((float(string_mem_metric[:-1]) * 1023.99737856), 3))
                elif suffix == 'p':       # p: pebi
                    string_list_metric[i] = str(round((float(string_mem_metric[:-1]) * 1048573.315645), 3))
                elif suffix == 'e':       # e: exbi (lol)
                    string_list_metric[i] = str(round((float(string_mem_metric[:-1]) * 1.074e+9), 3))

        # parse the runtime in seconds from the top
        run_time = string_list_metric[0]
        string_list_metric[0] = str(
            int(run_time.split(':')[0]) * 60 +
            int(run_time.split(':')[1][:2]) +
            float(run_time.split(':')[1][2:])
        )

        ping = tuple(string_list_metric)                # construct ping: (cpu_run_time, target_metric_0, ... target_metric_N)
        assert len(ping) == len(target_metrics)         # ensure expected ping format 
 
    return ping

def write_pings(pings, target_metrics, path):
    # last recorded cpu time of simulation, off by a max of +- g_ping_interval
    last_cpu_time = pings[-1][0]
    # add last cpu time to end of first tuple
    pings[0] = tuple(list(pings[0]) + [last_cpu_time])
    # add column headers
    csv_data = [tuple(target_metrics + ['total-runtime'])] + pings
    # export data
    pandas.DataFrame(csv_data).to_csv(path, index=False, header=False)


# ================ Profiling ================ 
def profile_data(cmd, target_metrics):
    print(f'\nProfiling \'{cmd}\'.\n')
    # get user name of user running the script
    host_string = subprocess.run('hostname', capture_output=True).stdout.decode().strip()
    # user_string = "big-gs"
    # create user dir if necessary
    subprocess.run(f'test -d raw-data/{host_string} || mkdir -p raw-data/{host_string}', shell=True)

    # independent var: system hardware
    for i in range(g_rounds):
        print(f'[PROFILING] --> variable: system hardware (1/2), round: {i+1} ({i+1}/{g_rounds})')

        pid = os.fork()                                 # fork process

        if pid == 0:                                    # child process
            pings = get_pings(                          # ping active simulation
                cmd,
                g_hardware_gridsize,
                target_metrics
            )
            write_pings(                                # export data
                pings,
                target_metrics,
                f'raw-data/{host_string}/hw-{i}.csv'
            )
            sys.exit(0)                                 # kill child (⌣́_⌣̀)

        else:                                           # parent process
            subprocess.run(                             # run simulation
                f'{cmd} {g_hardware_gridsize}',
                shell=True
            )
            os.wait()                                   # wait for child process to complete
            
    # independent var: gridsize
    if host_string == g_gridsize_machine:
        for i, gridsize in enumerate(g_gridsizes):
            for j in range(g_rounds):
                print(f'[PROFILING] --> variable: gridsize (2/2), gridsize: {gridsize} ({i+1}/{len(g_gridsizes)}), round: {j+1} ({j+1}/{g_rounds})')

                pid = os.fork()                                 # fork process

                if pid == 0:                                    # child process
                    pings = get_pings(                          # ping active simulation
                        cmd,
                        g_hardware_gridsize,
                        target_metrics
                    )
                    write_pings(                                # export data
                        pings,
                        target_metrics,
                        f'raw-data/{host_string}/gs-{gridsize}-{j}.csv'
                    )
                    sys.exit(0)                                 # kill child (⌣́_⌣̀)

                else:                                           # parent process
                    subprocess.run(                             # run simulation
                        f'{cmd} {g_hardware_gridsize}',
                        shell=True
                    )
                    os.wait()                                   # wait for child process to complete

    # independent var: chemistry sites
    pass


# ================ FORMATTING ================ 
def format_data(hardware_gridsize, gridsize_machine, gridsizes):
    data_path_prefix = 'raw-data/'
    hardware_files = []
    gridsize_files = []
    hardware_machines = []

    # get paths of raw-data and append them to their corresponding list
    for machine_dir in os.listdir(data_path_prefix):
        hardware_machines.append(machine_dir)
        machine_path = os.path.join(data_path_prefix, machine_dir)
        if os.path.isdir(machine_path):
            for machine_file in os.listdir(machine_path):
                # append hardware files
                if 'hw' in machine_file:
                    hardware_files.append(os.path.join(machine_path, machine_file))

                # append gridsize files
                elif machine_dir == gridsize_machine:
                    gridsize_files.append(os.path.join(machine_path, machine_file))

    # sort hardware on round number
    sort_hardware_on = lambda ele: int(ele.split('/')[-1].split('-')[-1].split('.')[0])
    sort_gridsize_on = lambda ele: int(ele.split('/')[-1].split('-')[1])
    hardware_files.sort(key=sort_hardware_on)   # sort hardware files on round
    gridsize_files.sort(key=sort_gridsize_on)   # sort gridsize files on gridsize

    hardware_data = []
    gridsize_data = []

    for hardware_file in hardware_files:
        machine_data = pandas.read_csv(hardware_file).to_dict('records')    # get a list of machine data records
        machine_data.insert(0, {'col1': hardware_file.split('/')[1]})       # insert machine name as header
        hardware_data.append(machine_data)

    for gridsize_file in gridsize_files:
        data = pandas.read_csv(gridsize_file).to_dict('records')                       # get a list of gridsize data records
        data.insert(0, {'col1': int(gridsize_file.split('/')[-1].split('-')[1])})      # insert gridsize as header
        gridsize_data.append(data)
    
    # get hostname of machine running script
    host_string = subprocess.run('hostname', capture_output=True).stdout.decode().strip()
    # if target format directory doesn't exist, create it
    subprocess.run(f'test -d formatted-data/{host_string} || mkdir -p formatted-data/{host_string}', shell=True)

    # always format harware data
    format_hardware_data(host_string, hardware_gridsize, hardware_machines, hardware_data)
    # if the machine running the script is the constant variable for gridsize, format the gridsize data
    if host_string == g_gridsize_machine:
        format_gridsize_data(host_string, gridsize_machine, gridsizes, gridsize_data)

def format_hardware_data(host_string, hardware_gridsize, hardware_machines, hardware_data):
    # initialize data with headers
    hardware_v_runtime = [(f'hardware vs. runtime ({hardware_gridsize})', )]
    hardware_v_mem = [(f'hardware vs. memory ({hardware_gridsize})', )]
    hardware_v_peak_mem = [(f'hardware vs. peak memory consumption ({hardware_gridsize})', )]
    hardware_v_avg_cpu = [(f'hardware vs. avg cpu usage ({hardware_gridsize})', )]

    # hardware vs. runtime
    hardware_v_runtime.append(tuple(hardware_machines))     # add label row
    runtimes = []
    for data in hardware_data:
        runtimes.append(data[1]['total-runtime'])
    hardware_v_runtime.append(tuple(runtimes))
    pandas.DataFrame(hardware_v_runtime).to_csv(
        f'formatted-data/{host_string}/hardware_v_runtime.csv',
        index=False,
        header=False
    )

    # hardware vs. mem
    hardware_v_mem.append(tuple(['time+'] + hardware_machines))     # add label row
    # a list of rows of runtime memory usage pairs, the column of
    # memory usage corresponds with it's associated label's column.
    mems = []
    for i, data in enumerate(hardware_data):
        for row in data[1:]:
            nan_list = [numpy.nan for i in range(len(hardware_machines)+1)]
            nan_list[0] = row['time+']
            nan_list[i+1] = row['res']
            mems.append(tuple(nan_list))
    mems.sort(key=lambda ele: ele[0])       # sort all runtime-memory pairs by runtime
    hardware_v_mem += mems
    pandas.DataFrame(hardware_v_mem).to_csv(
        f'formatted-data/{host_string}/hardware_v_mem.csv',
        index=False,
        header=False
    )
    
    # hardware vs. peak mem
    hardware_v_peak_mem.append(tuple(hardware_machines))        # add label row
    peak_mems = []
    for data in hardware_data:
        mems = []
        for row in data[1:]:            # skip header
            mems.append(row['res'])
        peak_mems.append(max(mems))
    hardware_v_peak_mem.append(tuple(peak_mems))
    pandas.DataFrame(hardware_v_peak_mem).to_csv(
        f'formatted-data/{host_string}/hardware_v_peak_mem.csv',
        index=False,
        header=False
    )

    # hardware vs. avg cpu
    hardware_v_avg_cpu.append(tuple(hardware_machines))
    avg_cpus = []
    for data in hardware_data:
        cpus = []
        for row in data[1:]:            # skip header
            cpus.append(row['%cpu'])
        avg_cpus.append(sum(cpus)/len(cpus))
    hardware_v_avg_cpu.append(tuple(avg_cpus))
    pandas.DataFrame(hardware_v_avg_cpu).to_csv(
        f'formatted-data/{host_string}/hardware_v_avg_cpu.csv',
        index=False,
        header=False
    )

def format_gridsize_data(host_string, gridsize_machine, gridsizes, gridsize_data):
    # initialize data with headers
    gridsize_v_runtime = [(f'gridsize vs. runtime ({gridsize_machine})', )]
    gridsize_v_mem = [(f'gridsize vs. memory ({gridsize_machine})', )]
    gridsize_v_peak_mem = [(f'gridsize vs. peak memory consumption ({gridsize_machine})', )]
    gridsize_v_avg_cpu = [(f'gridsize vs. avg cpu usage ({gridsize_machine})', )]

    # gridsize vs. runtime
    gridsize_v_runtime.append(tuple(gridsizes))
    runtimes = []
    for data in gridsize_data:
        runtimes.append(data[1]['total-runtime'])
    gridsize_v_runtime.append(tuple(runtimes))
    pandas.DataFrame(gridsize_v_runtime).to_csv(
        f'formatted-data/{host_string}/gridsize_v_runtime.csv',
        index=False,
        header=False
    )

    # gridsize vs. mem
    gridsize_v_mem.append(tuple(['time+'] + [ f'gs={gs}' for gs in gridsizes ]))
    # a list of rows of runtime memory usage pairs, the column of
    # memory usage corresponds with it's associated label's column.
    mems = []
    for i, data in enumerate(gridsize_data):
        for row in data[1:]:
            nan_list = [numpy.nan for i in range(len(gridsizes)+1)]
            nan_list[0] = row['time+']
            nan_list[i+1] = row['res']
            mems.append(tuple(nan_list))
    mems.sort(key=lambda ele: ele[0])       # sort all runtime-memory pairs by runtime
    gridsize_v_mem += mems
    pandas.DataFrame(gridsize_v_mem).to_csv(
        f'formatted-data/{host_string}/gridsize_v_mem.csv',
        index=False,
        header=False
    )
    
    # gridsize vs. peak mem
    gridsize_v_peak_mem.append(tuple(gridsizes))
    peak_mems = []
    for data in gridsize_data:
        mems = []
        for row in data[1:]:            # skip header
            mems.append(row['res'])
        peak_mems.append(max(mems))
    gridsize_v_peak_mem.append(tuple(peak_mems))
    pandas.DataFrame(gridsize_v_peak_mem).to_csv(
        f'formatted-data/{host_string}/gridsize_v_peak_mem.csv',
        index=False,
        header=False
    )

    # gridsize vs. avg cpu
    gridsize_v_avg_cpu.append(tuple(gridsizes))
    avg_cpus = []
    for data in gridsize_data:
        cpus = []
        for row in data[1:]:            # skip header
            cpus.append(row['%cpu'])
        avg_cpus.append(sum(cpus)/len(cpus))
    gridsize_v_avg_cpu.append(tuple(avg_cpus))
    pandas.DataFrame(gridsize_v_avg_cpu).to_csv(
        f'formatted-data/{host_string}/gridsize_v_avg_cpu.csv',
        index=False,
        header=False
    )


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
    if option == 'all':
        profile_data(cmd, ['time+', 'res', '%cpu'])
        format_data(g_hardware_gridsize, g_gridsize_machine, g_gridsizes)
    elif option == 'help':
        print_usage(None)
    else:
        print_usage(option)
    
    print('\nProfiling done. See \'raw-data\' for raw output. See \'formatted-data\' for formatted output.\n')


if __name__ == '__main__':      # entry point
    main(sys.argv)
