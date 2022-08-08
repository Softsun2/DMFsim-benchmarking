import sys              # exiting
import os               # forking and waiting
import subprocess       # running cmds
import time             # sleeping
import pandas           # csv exporting


# benchmarking params
g_rounds = 3
g_grid_sizes = [40, 240]
g_ping_interval = 1   # in seconds
# something for number of chemistry sites
g_targets = {
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

    # TODO: independent var: system hardware
    # produce n_rounds many runtimes at the default gridsize

    # TODO: independent var: gridsize
    # produce n_rounds many runtimes for each gridsize in gridsizes

    # NOTE: rutimes are simple, we could maybe parse cmd print
    # statements and send the results to export_time_data as a variable

    export_time_data()

def export_time_data():
    print('exporting time data')

    # TODO: compile data into a csv for system hardware
    # should just be one row of all the runtimes
    # NOTE: need to track who's machine was used to obtain this data
    # maybe do so in filename or something with whoami cmd.
    
    # TODO: compile data into a csv for gridsizes
    # format as follows
    #   gridsize0   gridsize1    ... gridsizeN
    #   r0_gs0_time r0_gs1_time      r0_gsN_time
    #   ...
    #   rN_gs0_time rN_gs1_time      rN_gsN_time
    pass


# ================ PINGING ================ 
def get_pings(process_name, target_metric):
    simulation_states = ['waiting', 'running', 'done']
    sim_state = simulation_states[0]

    sim_pid = ''
    pings = []

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
                print(f'[CHILD]: sim pid: {sim_pid}')
                # set sim_state to running
                sim_state = simulation_states[1]

        elif sim_state == 'running':
            # ping top
            ping = ping_top(sim_pid, target_metric) 
            # if ping succeeds add it to pings
            if ping:
                pings.append(ping)
            # check if the simulation process stopped running
            completed_process = subprocess.run(f'pidof {process_name} > /dev/null', shell=True)
            if completed_process.returncode != 0:
                sim_state = simulation_states[2]
        
        time.sleep(g_ping_interval)     # don't spam pings
    
    return pings

def ping_top(sim_pid, target_metric):
    ping = None
    ping_cmd = (
        'top -b '           # run top in batch mode
        '-n 2 '             # run 2 iterations
        '-d 0.1 '           # dt = .1 sec
        f'-p {sim_pid} | '    # only show data for sim process id
        'tail -1 | '        # get the last line of the output
        # print the process's cpu time and target metric
        f'awk \'{{print ${g_targets["time+"]}, ${g_targets[target_metric]}}}\''
    )

    completed_process = subprocess.run(ping_cmd, shell=True, capture_output=True)
    string_metric = completed_process.stdout.decode().strip()

    """ If you ping top with a dead pid it does not error, nor print to stderr,
        the afaik the only way to detect when this happens is to check if the
        grabbed strings are the column headers, i.e., contain no digits """
    if any(char.isdigit() for char in string_metric):
        string_list_metric = string_metric.split(' ')

        # parse the runtime in seconds from the top
        run_time = string_list_metric[0]
        string_list_metric[0] = str(
            int(run_time[0]) * 60 +
            int(run_time[2:4]) +
            float(run_time[4:])
        )

        ping = tuple(string_list_metric)            # make the (cpu_time, target_metric) data point
        assert len(ping) == 2                       # ensure expected ping format
 
    print('[CHILD]: Pinged top!')
    return ping

def write_pings(pings, path):
    pandas.DataFrame(pings).to_csv(path, index=False, header=False)


# ================ MEMORY ================ 
def profile_memory(cmd, process_name):
    print(f'\nProfiling memory usage of \'{cmd}\'.\n')
    # independent var: system hardware
    for i in range(g_rounds):
        print('[PARENT]: Forking.')
        pid = os.fork()                                # fork process

        if pid == 0:                                   # if; child process
            print('[CHILD]: Preparing to ping.')
            pings = get_pings(process_name, 'res')     # ping active simulation
            print(f'[CHILD]: pings: {pings}')
            print('[CHILD]: Pinging done.')
            write_pings(pings, f'raw-data/mem/hw-{i}.csv')
            sys.exit(0)                                # kill child (⌣́_⌣̀)

        else:                                          # else; parent process
            print('[PARENT]: Running Simulation.')
            subprocess.run(f'sh -c \'exec -a {process_name} {cmd}\'', shell=True)     # run simulation
            print('[PARENT]: Simulation done.')
            os.wait()                                  # wait for child process to complete
            
    # independent var: gridsize
    # independent var: chemistry sites


# ================ CPU ================ 
def profile_cpu(cmd):
    print(f'profiling cpu usage of \'{cmd}\'')
    
    # TODO: independent var: system hardware
    # produce n_rounds many cpu usage metrics at the default gridsize

    # TODO: independent var: gridsize
    # produce n_rounds many cpu usage metrics for each gridsize in gridsizes

    # NOTE: we could maybe parse cmd print statements
    # and send the results to export_cpu_data as a variable

    pass


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
        time_cmd(cmd)
    elif option == 'mem':
        profile_memory(cmd, process_name)
    elif option == 'cpu':
        profile_cpu(cmd)
    elif option == 'all':
        time_cmd(cmd)
        profile_memory(cmd, process_name)
        profile_cpu(cmd)
    elif option == 'help':
        print_usage(None)
    else:
        print_usage(option)


if __name__ == '__main__':      # entry point
    main(sys.argv)
