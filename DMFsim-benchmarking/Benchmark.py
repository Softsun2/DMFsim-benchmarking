import sys              # exiting
import os               # forking and waiting
import subprocess       # running cmds
import time             # sleeping
import pandas           # csv exporting/importing
import numpy            # nan values
import argparse
import configparser
import json


# ================ CONSTANTS ================ 

""" The target metrics, a list of strings corresponding to top metric headers.
When benchmarking an independent variable the specified target metrics will be obtained
per ping from top. "time+": runtime, "res": RAM usage, "%cpu": cpu usage. """
g_target_metrics = ['time+', 'res', '%cpu']
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


# ================ PARAMETERS ================ 
config = configparser.ConfigParser()
config.read('./config.ini')

g_rounds = int(config['Benchmarking']['Rounds'])
g_ping_interval = float(config['Benchmarking']['PingInterval'])

g_const_machine = config['Constant Variables']['Machine']
g_const_gridsize = int(config['Constant Variables']['Gridsize'])
g_const_gene_length = int(config['Constant Variables']['GeneLength'])

g_gridsizes = json.loads(config['Independent Variables']['Gridsizes'])
g_gene_lengths = json.loads(config['Independent Variables']['GeneLengths'])


# ================ PINGING ================ 
def get_pings(full_cmd, target_metrics):
    # organizing simple state machine
    simulation_states = ['waiting', 'running', 'done']
    sim_state = simulation_states[0]

    sim_pid = ''    # string representation of the simulations pid
    pings = []      # list of pings; (cpu_run_time, target_metric_0, ... target_metric_N)

    while sim_state == 'waiting' or sim_state == 'running':

        if sim_state == 'waiting':
            # check if the simulation process started running
            completed_process = subprocess.run(f'pgrep -a python3', shell=True, capture_output=True)
            if f'{full_cmd}' in completed_process.stdout.decode().strip():
                # parse pgrep stdout for simulation's pid
                lines = completed_process.stdout.decode().strip().split('\n')
                sim_pid = ''
                for line in lines:
                    if full_cmd in line:
                        sim_pid = line.split(' ')[0]
                # set sim_state to running
                sim_state = simulation_states[1]

        elif sim_state == 'running':
            ping = ping_top(sim_pid, target_metrics) 
            if ping:    # if ping succeeds add it to the list of pings
                pings.append(ping)
            # check if the simulation process stopped running
            completed_process = subprocess.run(f'pgrep -a python3', shell=True, capture_output=True)
            if f'{full_cmd}' not in completed_process.stdout.decode().strip():
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
def profile_hardware(variable_count, ith_variable, cmd, target_metrics, host_string):
    if target_metrics == []:
        return

    for i in range(g_rounds):
        print(f'[PROFILING] --> variable: system hardware ({ith_variable}/{variable_count}), round: {i+1} ({i+1}/{g_rounds})')

        pid = os.fork()                                 # fork process
        full_cmd = (
            f'{cmd} '
            f'--gridsize={g_const_gridsize} '
            f'--gene-length={g_const_gene_length}'
        )

        if pid == 0:                                    # child process
            # ping active simulation
            pings = get_pings(full_cmd, target_metrics)
            write_pings(                                # export data
                pings,
                target_metrics,
                f'raw-data/{host_string}/hw-{i}.csv'
            )
            sys.exit(0)                                 # kill child

        else:                                           # parent process
            # run simulation
            subprocess.run(full_cmd, shell=True)
            os.wait()                                   # wait for child process to complete

def profile_gridsize(variable_count, ith_variable, cmd, target_metrics, host_string):
    if target_metrics == []:
        return

    # only profile on desired constant machine
    if host_string == g_const_machine:
        for i, gridsize in enumerate(g_gridsizes):
            for j in range(g_rounds):
                # FIXME:
                print(f'[PROFILING] --> variable: gridsize ({ith_variable}/{variable_count}), gridsize: {gridsize} ({i+1}/{len(g_gridsizes)}), round: {j+1} ({j+1}/{g_rounds})')

                pid = os.fork()                                 # fork process
                full_cmd = (
                    f'{cmd} '
                    f'--gridsize={gridsize} '
                    f'--gene-length={g_const_gene_length}'
                )

                if pid == 0:                                    # child process
                    # ping active simulation
                    pings = get_pings(full_cmd, target_metrics)
                    write_pings(                                # export data
                        pings,
                        target_metrics,
                        f'raw-data/{host_string}/gs-{gridsize}-{j}.csv'
                    )
                    sys.exit(0)                                 # kill child

                else:                                           # parent process
                    # run simulation
                    subprocess.run(full_cmd, shell=True)
                    os.wait()                                   # wait for child process to complete

def profile_gene_length(variable_count, ith_variable, cmd, target_metrics, host_string):
    if target_metrics == []:
        return
    
    # only profile on desired constant machine
    if host_string == g_const_machine:
        for i, gene_length in enumerate(g_gene_lengths):
            for j in range(g_rounds):
                # FIXME:
                print(f'[PROFILING] --> variable: gene length ({ith_variable}/{variable_count}), gene length: {gene_length} ({i+1}/{len(g_gene_lengths)}), round: {j+1} ({j+1}/{g_rounds})')

                pid = os.fork()                                 # fork process
                full_cmd = (
                    f'{cmd} '
                    f'--host-string={host_string} '
                    f'--gridsize={g_const_gridsize} '
                    f'--gene-length={gene_length} '
                    f'--round={j}'
                )

                if pid == 0:                                    # child process
                    # ping active simulation
                    pings = get_pings(full_cmd, target_metrics)
                    write_pings(                                # export data
                        pings,
                        target_metrics,
                        f'raw-data/{host_string}/gl-{gene_length}-{j}.csv'
                    )
                    sys.exit(0)                                 # kill child

                else:                                           # parent process
                    # run simulation
                    subprocess.run(full_cmd, shell=True)
                    os.wait()                                   # wait for child process to complete


# ================ FORMATTING ================ 
def import_data(raw_data_path, matcher, labeler, sorter):
    # get paths of raw-data and append them to their corresponding list
    label_file_pairs = []
    for machine in os.listdir(raw_data_path):
        machine_path = os.path.join(raw_data_path, machine)
        if os.path.isdir(machine_path):
            for file in os.listdir(machine_path):
                if matcher(machine, file):
                    label = labeler(machine, file)
                    label_file_pairs.append(
                        (label, os.path.join(machine_path, file))
                    )

    # prepare sorter by first sorting on round number
    label_file_pairs.sort(key=lambda ele: ele[0].split('.csv')[0][-1])

    # sort files
    if sorter:
        label_file_pairs.sort(key=sorter)

    # import data
    label_data_pairs = []
    for label_file_pair in label_file_pairs:
        label = label_file_pair[0]
        label_file = label_file_pair[1]
        label_data = pandas.read_csv(label_file).to_dict('records')
        label_data_pairs.append((label, label_data))

    return label_data_pairs

def format_runtime_data(title, header, data, path):
    # format data
    formatted_data = header
    runtimes = []
    for d in data:
        runtimes.append(d[0]['total-runtime'])
    formatted_data.append(tuple(runtimes))

    # export data
    pandas.DataFrame(formatted_data).to_csv(
        f'{path+title}.csv',
        index=False,
        header=False
    )

def format_mem_data(title, header, data, path, mem_label):
    # format data
    formatted_data = header
    labels = header[1]
    mems = []
    for i, d in enumerate(data):
        for row in d:
            nan_list = [numpy.nan for _ in range(len(labels))]
            nan_list[0] = row['time+']
            nan_list[i+1] = row[mem_label]
            mems.append(tuple(nan_list))

    # sort runtime-memory pairs by runtime
    mems.sort(key=lambda ele: ele[0])

    formatted_data += mems

    # export data
    pandas.DataFrame(formatted_data).to_csv(
        f'{path+title}.csv',
        index=False,
        header=False
    )

def format_peak_mem_data(title, header, data, path, mem_label):
     # format data
    formatted_data = header
    peak_mems = []
    for d in data:
        mems = []
        for row in d:
            mems.append(row[mem_label])
        peak_mems.append(max(mems))
    formatted_data.append(tuple(peak_mems))

    # export data
    pandas.DataFrame(formatted_data).to_csv(
        f'{path+title}.csv',
        index=False,
        header=False
    )

def format_avg_cpu_data(title, header, data, path):
    # format data
    formatted_data = header
    avg_cpus = []
    for d in data:
        cpus = []
        for row in d:
            cpus.append(row['%cpu'])
        avg_cpus.append(sum(cpus)/len(cpus))
    formatted_data.append(tuple(avg_cpus))

    # export data
    pandas.DataFrame(formatted_data).to_csv(
        f'{path+title}.csv',
        index=False,
        header=False
    )

def format_hardware_data(raw_data_path, formatted_data_path, target_metrics):
    matcher = lambda _, file: 'hw' in file
    labeler = lambda machine, file: f"{machine}-{file.split('.csv')[0][-1]}"
    sorter = None

    machine_data_pairs = import_data(raw_data_path, matcher, labeler, sorter)

    # format and export data
    labels = tuple([ pair[0] for pair in machine_data_pairs ])
    data = [ pair[1] for pair in machine_data_pairs ]
    path = formatted_data_path+'hardware/'
    if 'time+' in target_metrics:
        format_runtime_data(
            'hardware-v-runtime', 
            [ (f'hardware vs. runtime (gs={g_const_gridsize})', ), labels ],
            data, path
        )
    if any(metric in g_memory_targets for metric in target_metrics):
        mem_label = next(metric for metric in target_metrics if metric in g_memory_targets)
        format_mem_data(
            'hardware-v-mem', 
            [
                (f'hardware vs. memory (gs={g_const_gridsize})', ),
                ('time+', ) + labels
            ],
            data, path, mem_label
        )
        format_peak_mem_data(
            'hardware-v-peak-mem', 
            [ (f'hardware vs. peak memory (gs={g_const_gridsize})', ), labels ],
            data, path, mem_label
        )
    if '%cpu' in target_metrics:
        format_avg_cpu_data(
            'hardware-v-avg-cpu', 
            [ (f'hardware vs. avg cpu % (gs={g_const_gridsize})', ), labels ],
            data, path
        )

def format_gridsize_data(raw_data_path, formatted_data_path, target_metrics, host_string):
    matcher = lambda machine, file : machine == g_const_machine and 'gs' in file
    labeler = lambda _, file : f"{file.split('-')[1]}-{file.split('.csv')[0][-1]}"
    sorter = lambda ele : int(ele[0].split('-')[0])

    gridsize_data_pairs = import_data(raw_data_path, matcher, labeler, sorter)

    # format and export data
    labels = tuple([ pair[0] for pair in gridsize_data_pairs ])
    data = [ pair[1] for pair in gridsize_data_pairs ]
    path = f'{formatted_data_path+host_string}/'
    if 'time+' in target_metrics:
        format_runtime_data(
            'gridsize-v-runtime', 
            [ (f'gridsize vs. runtime (hw={g_const_machine})', ), labels ],
            data, path
        )
    if any(metric in g_memory_targets for metric in target_metrics):
        mem_label = next(metric for metric in target_metrics if metric in g_memory_targets)
        format_mem_data(
            'gridsize-v-mem', 
            [
                (f'gridsize vs. memory (hw={g_const_machine})', ),
                ('time+', ) + labels
            ],
            data, path, mem_label
        )
        format_peak_mem_data(
            'gridsize-v-peak-mem', 
            [ (f'gridsize vs. peak memory (hw={g_const_machine})', ), labels ],
            data, path, mem_label
        )
    if '%cpu' in target_metrics:
        format_avg_cpu_data(
            'gridsize-v-avg-cpu', 
            [ (f'gridsize vs. avg cpu % (hw={g_const_machine})', ), labels ],
            data, path
        )

def format_gene_length_data(raw_data_path, formatted_data_path, target_metrics, host_string):
    matcher = lambda machine, file : machine == g_const_machine and 'gl' in file
    labeler = lambda _, file : f"{file.split('-')[1]}-{file.split('.csv')[0][-1]}"
    sorter = lambda ele : int(ele[0].split('-')[0])

    gene_length_data_pairs = import_data(raw_data_path, matcher, labeler, sorter)

    # format and export data
    labels = tuple([ pair[0] for pair in gene_length_data_pairs ])
    data = [ pair[1] for pair in gene_length_data_pairs ]
    path = f'{formatted_data_path+host_string}/'
    if 'time+' in target_metrics:
        format_runtime_data(
            'gene-length-v-runtime', 
            [ (f'gene length vs. runtime (hw={g_const_machine})', ), labels ],
            data, path
        )
    if any(metric in g_memory_targets for metric in target_metrics):
        mem_label = next(metric for metric in target_metrics if metric in g_memory_targets)
        format_mem_data(
            'gene-length-v-mem', 
            [
                (f'gene length vs. memory (hw={g_const_machine})', ),
                ('time+', ) + labels
            ],
            data, path, mem_label
        )
        format_peak_mem_data(
            'gene-length-v-peak-mem', 
            [ (f'gene length vs. peak memory (hw={g_const_machine})', ), labels ],
            data, path, mem_label
        )
    if '%cpu' in target_metrics:
        format_avg_cpu_data(
            'gene-length-v-avg-cpu', 
            [ (f'gene length vs. avg cpu % (hw={g_const_machine})', ), labels ],
            data, path
        )

def format_congestion_data(raw_data_path, formatted_data_path, host_string):
    matcher = lambda machine, file : machine == g_const_machine and 'cg' in file
    labeler = lambda _, file : f"{file.split('-')[1]}-{file.split('.csv')[0][-1]}"
    sorter = lambda ele : int(ele[0].split('-')[0])
    
    congestion_data_pairs = import_data(raw_data_path, matcher, labeler, sorter)
    
    # format data
    labels = ('total droplets', 'max droplets', 'max congestion')
    data = [ pair[1] for pair in congestion_data_pairs ]
    path = f'{formatted_data_path+host_string}/'
    title = 'gene-length-v-congestion'
    header = [
        (f'gene length vs. congestion (hw={g_const_machine}, gs={g_const_gridsize})', ),
        labels
    ]
    
    formatted_congestion_data = header
    for d in data:
        congestion = (
            d[0]['total droplets'],
            d[0]['max droplets'],
            d[0]['max congestion']
        )
        formatted_congestion_data.append(congestion)
    formatted_congestion_data = tuple(formatted_congestion_data)

    # export data
    pandas.DataFrame(formatted_congestion_data).to_csv(
        f'{path+title}.csv',
        index=False,
        header=False
    )

# ================ MAIN ================ 
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'option',
        choices=['all', 'hardware', 'gridsize', 'gene-length'],
        type=str,
        help='benchmark all independent variables, hardware, gridsize, or gene-length',
    )
    parser.add_argument(
        'cmd',
        type=str,
        help='the command to be benchmarked',
    )
    args = parser.parse_args()


    # the string representing the command to benchmark
    cmd = args.cmd
    option = args.option

    # memory type to use as memory metric
    mem_label = g_targets

    # data paths
    raw_data_path = 'raw-data/'
    formatted_data_path = 'formatted-data/'

    # get name of the machine running the script
    host_string = subprocess.run('hostname', capture_output=True).stdout.decode().strip()

    if host_string != g_const_machine:
        print("Host machine doesn't match configured machine! Check that the machine declared in `config.ini` is your hostname! Also make sure there are no quotes around the hostname in the config.ini file! ")
        sys.exit(1)

    # create data dirs if necessary
    subprocess.run(
        f'test -d {raw_data_path + host_string} || '
        f'mkdir -p {raw_data_path + host_string}',
        shell=True
    )
    subprocess.run(
        f'test -d {formatted_data_path + host_string} || '
        f'mkdir -p {formatted_data_path + host_string}',
        shell=True
    )
    subprocess.run(
        f'test -d {formatted_data_path}hardware || '
        f'mkdir -p {formatted_data_path}hardware',
        shell=True
    )

    print(f'\nProfiling \'{cmd}\'.\n')

    variable_count = 0

    # option handling
    if option == 'all':
        variable_count = 3
        profile_hardware(variable_count, 1, cmd, g_target_metrics, host_string)
        profile_gridsize(variable_count, 2, cmd, g_target_metrics, host_string)
        profile_gene_length(variable_count, 3, cmd, g_target_metrics, host_string)

        format_hardware_data(raw_data_path, formatted_data_path, g_target_metrics)
        format_gridsize_data(raw_data_path, formatted_data_path, g_target_metrics, host_string)
        format_gene_length_data(raw_data_path, formatted_data_path, g_target_metrics, host_string)
        format_congestion_data(raw_data_path, formatted_data_path, host_string)
    else:
        variable_count = 1
        if option == 'hardware':
          profile_hardware(variable_count, 1, cmd, g_target_metrics, host_string)
          format_hardware_data(raw_data_path, formatted_data_path, g_target_metrics)
        if option == 'gridsize':
          profile_gridsize(variable_count, 1, cmd, g_target_metrics, host_string)
          format_gridsize_data(raw_data_path, formatted_data_path, g_target_metrics, host_string)
        if option == 'gene-length':
          profile_gene_length(variable_count, 1, cmd, g_target_metrics, host_string)
          format_gene_length_data(raw_data_path, formatted_data_path, g_target_metrics, host_string)
          format_congestion_data(raw_data_path, formatted_data_path, host_string)

    print('\nProfiling done. See \'raw-data\' for raw output. See \'formatted-data\' for formatted output.\n')


if __name__ == '__main__':      # entry point
    main()
