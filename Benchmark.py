import sys, os, time


# benchmarking params
g_rounds = 3
g_grid_sizes = [40, 240]
# something for number of chemistry sites
targets = {
    'pid': 0,
    'virt': 1,
    'res': 2,
    'shr': 3,
    '%cpu': 4,
    '%mem': 5,
    'time+': 7,
    'command': 7,
    'swap': 8,
    'data': 9
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
            if os.system(f'pidof {process_name} > /dev/null') == 0:
                # get pid of simulation process
                sim_pid = os.popen(f'pidof {process_name}').read().strip()
                # set sim_state to running
                sim_state = simulation_states[1]

        elif sim_state == 'running':
            # ping top
            ping_top(sim_pid, target_metric) 
            # check if the simulation process stopped running
            if os.system(f'pidof {process_name} > /dev/null') != 0:
                sim_state = simulation_states[2]
        
        time.sleep(1)     # don't spam pings
    
    return pings

def ping_top(sim_pid, target_metric):
    ping_cmd = (
        'top -b '           # run top in batch mode
        '-n 2 '             # run 2 iterations
        '-d 0.1 '           # dt = .1 sec
        f'-p {sim_pid} '    # only show data for sim process id
        '2> /dev/null | '   # supress inactive pid error message
        'tail -1 | '        # get the last line of the output
        # print the process's cpu time and target metric
        f'awk \'{{print ${targets["time+"]}, ${targets[target_metric]}}}\''
    )

    string_metric = os.popen(ping_cmd).read()
    if string_metric:
        print(f'[CHILD]: string_metric: {string_metric}')
    print('[CHILD]: Pinged top!')
    pass

def write_pings(pings):
    pass


# ================ MEMORY ================ 
def profile_memory(cmd, process_name):
    print(f'\nProfiling memory usage of \'{cmd}\'.\n')
    # independent var: system hardware
    for i in range(g_rounds):
        print('[PARENT]: Forking.')
        pid = os.fork()             # fork process

        if pid == 0:                # if child process
            print('[CHILD]: Preparing to ping.')
            pings = get_pings(process_name, 'res')     # ping active simulation
            print('[CHILD]: Pinging done.')
            write_pings(pings)      # write simulation data
            sys.exit(0)             # reap child

        else:                       # else; parent process
            print('[PARENT]: Running Simulation.')
            os.system(f'sh -c \'exec -a {process_name} {cmd}\'')     # run simulation
            print('[PARENT]: Simulation done.')
            os.wait()               # wait for child process to complete
            
    # independent var: gridsize
    # independent var: chemistry sites
    export_memory_data()

def export_memory_data():
    print('exporting memory data')


# ================ CPU ================ 
def profile_cpu(cmd):
    print(f'profiling cpu usage of \'{cmd}\'')
    
    # TODO: independent var: system hardware
    # produce n_rounds many cpu usage metrics at the default gridsize

    # TODO: independent var: gridsize
    # produce n_rounds many cpu usage metrics for each gridsize in gridsizes

    # NOTE: we could maybe parse cmd print statements
    # and send the results to export_cpu_data as a variable

    export_cpu_data()

def export_cpu_data():
    print('exporting cpu data')
    
    # TODO: compile data into a csv for cpu usage
    # format as follows
    #   gridsize0     gridsize1    ...  gridsizeN
    #   r0_gs0_usage  r0_gs1_usage ...  r0_gsN_usage
    #   ...
    #   rN_gs0_usage  rN_gs1_usage ...  rN_gsN_usage
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
