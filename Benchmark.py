import sys              # exiting
import os               # forking and waiting
import subprocess       # running cmds
import time             # sleeping
import pandas           # csv exporting


# benchmarking params
g_rounds = 3
g_gridsizes = [ i for i in range(500, 2100, 100) ]
g_ping_interval = 0.07       # in seconds
# something for number of chemistry sites

# possible target metrics, the ordering depends on the user's top configuration
# these indexes will not be accurate if the given toprc is not used!
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
    '       time - benchmark runtime\n'+ \
    '       mem  - profile memory usage\n'+ \
    '       cpu  - profile cpu usage\n'+ \
    '       help - display usage'
    print(usage)


# ================ PINGING ================ 
def get_pings(process_name, target_metrics):
    # organizing simple state machine
    simulation_states = ['waiting', 'running', 'done']
    sim_state = simulation_states[0]

    sim_pid = ''    # string representation of the simulations pid
    pings = []      # list of pings; (cpu_run_time, target_metric_0, ... target_metric_N)

    while sim_state == 'waiting' or sim_state == 'running':

        if sim_state == 'waiting':
            # check if the simulation process started running
            completed_process = subprocess.run(
                f'pidof {process_name}',            # lookup the processes id
                shell=True,                         # use a subshell
                capture_output=True                 # record pid if found
            )
            if completed_process.returncode == 0:
                # get pid of simulation process
                sim_pid = completed_process.stdout.decode().strip()
                # set sim_state to running
                sim_state = simulation_states[1]

        elif sim_state == 'running':
            ping = ping_top(sim_pid, target_metrics) 
            if ping:    # if ping succeeds add it to the list of pings
                pings.append(ping)
            # check if the simulation process stopped running
            completed_process = subprocess.run(f'pidof {process_name} > /dev/null', shell=True)
            if completed_process.returncode != 0:
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
def profile(cmd, process_name, target_metrics):
    print(f'\nProfiling \'{cmd}\'.\n')
    # get user name of user running the script
    user_string = subprocess.run('hostname', capture_output=True).stdout.decode().strip()
    # user_string = "big-gs"
    # create user dir if necessary
    subprocess.run(f'test -d raw-data/{user_string} || mkdir raw-data/{user_string}', shell=True)
    
    # independent var: system hardware
    for i in range(g_rounds):
        print(f'[PROFILING] --> variable: system hardware (1/2), round: {i+1} ({i+1}/{g_rounds})')

        pid = os.fork()                                 # fork process

        if pid == 0:                                    # child process
            pings = get_pings(                          # ping active simulation
                process_name,
                target_metrics
            )
            write_pings(                                # export data
                pings,
                target_metrics,
                f'raw-data/{user_string}/hw-{i}.csv'
            )
            sys.exit(0)                                 # kill child (⌣́_⌣̀)

        else:                                           # parent process
            subprocess.run(                             # run simulation
                f'sh -c \'exec -a {process_name} {cmd}\'',
                shell=True
            )
            os.wait()                                   # wait for child process to complete
            
    # independent var: gridsize
    for i, gridsize in enumerate(g_gridsizes):
        for j in range(g_rounds):
            print(f'[PROFILING] --> variable: gridsize (2/2), gridsize: {gridsize} ({i+1}/{len(g_gridsizes)}), round: {j+1} ({j+1}/{g_rounds})')

            pid = os.fork()                                 # fork process

            if pid == 0:                                    # child process
                pings = get_pings(                          # ping active simulation
                    process_name,
                    target_metrics
                )
                write_pings(                                # export data
                    pings,
                    target_metrics,
                    f'raw-data/{user_string}/gs-{gridsize}-{j}.csv'
                )
                sys.exit(0)                                 # kill child (⌣́_⌣̀)

            else:                                           # parent process
                subprocess.run(                             # run simulation
                    f'sh -c \'exec -a {process_name} {cmd} {gridsize}\'',
                     shell=True
                )
                os.wait()                                   # wait for child process to complete

    # independent var: chemistry sites


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
    process_name = 'dmf-sim'

    # option handling
    if option == 'time':
        profile(cmd, process_name, ['time+'])
    elif option == 'mem':
        profile(cmd, process_name, ['time+', 'res'])
    elif option == 'cpu':
        profile(cmd, process_name, ['time+', '%cpu'])
    elif option == 'all':
        profile(cmd, process_name, ['time+', 'res', '%cpu'])
    elif option == 'help':
        print_usage(None)
    else:
        print_usage(option)
    
    print('\nProfiling done. See \'raw-data\' for output.\n')


if __name__ == '__main__':      # entry point
    main(sys.argv)
