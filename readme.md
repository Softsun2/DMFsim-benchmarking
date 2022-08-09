# Plan
1. **XXX** Decide on a benchmarking procedure.
    * Still haven't chosen exact methods for producing runtimes and cpu usage.
2. **XXX** Implement this procedure with a script.
    * The script should do two things, obtain the data with the chosen benchmarking tools and export that data to a spreadsheet readable format.
3. Plot the data.
4. Manual limitation testing
5. Make the presentation.


# Benchmarking
We have two objectives, to obtain a reference for which to compare future code to as well as identifying bottlenecks and breaking points of the existing code.

The goal is to produce a reusable benchmarking procedure that's independent of the programs implementation.

The current dependent vairables are runtime, memory consumption/usage, and cpu usage.

The current independent variables are system hardware, gridsize, and potentially the number of chemistry sites (do this if we have time).

For limitation testing we are searching for breaking inputs (if there's time explain how to adress these inputs). We are also looking for bottlenecks at a highlevel. Ajay suggested mentioning these towards the end of the presentation.

The plan is to average the data over multiple rounds of benchmarking on all of our machines.


## [The Script](Benchmark.py)
The script obtains data with [top](https://man7.org/linux/man-pages/man1/top.1.html) and exports that data to a spreadsheet readable format (csv).

### Usage
You will most likely only need to run the command `python3 Benchmarking.py all <command-to-run-simulation>`. For example running the script on the python implementation `python3 Benchmarking.py all python3 ../Tutorial.py`, note that the paths here are relative, be mindful of which directory you are with respect to the `DMFsim` repo and the benchmarking repo. Additional usage can be displayed with `python3 Benchmarking.py help`. The `all` option means that the output csv files will contain data for all the benchmarking metrics.

#### Output Data
Data is exported to a directory within the benchmarking repo named `raw-data`. The file prefix `hw` for "hardware" means that the simulation was ran at the default gridsize, for the independent variable: system hardware. The file prefix `gs-<gridsize>` for "gridsize" means that the simulation was ran at the gridsize `<gridsize>`, for the independent variable: gridsize. All csv file names end with an integer identifying the benchmarking round of corresponding independent variable. Each column header describes that column's data. See top's [man page](https://man7.org/linux/man-pages/man1/top.1.html) for an explanation of the headers used. TODO: Go over units.

### Assumptions
* **The user's top is configured as mine.** The script will **not** work if the user's top is not configured as mine! I've include my `toprc` to be copied. Make a backup of your toprc (if you want) and use the one provided. The user's toprc is located at `~/.config/procps/toprc`.
* **The executable/cmd to run the simulation can take gridsize as a command line argument.** The script will **not** work if the simulation can't take gridsize as a command line arg, I've included a modified `Tutorial.py` to handle this in this repo to replace the old `Tutorial.py`.

### Multiprocessing
It should be clear that the script uses multiprocessing. Top records process's hardware usage *as those processes run* which means we have to incorporate multiprocessing or threading. Shared data isn't necessary so we use child processes to interact with top as the parent process runs the simulation. The control flow is illustrated below. A ping is a data point of the form (current_cpu_runtime, target_metric). You can see that the simulation ended before the last ping was able to complete, hence it was discarded.
```
[PARENT]: Forking.
[PARENT]: Running Simulation.
[CHILD]: Preparing to ping.
[CHILD]: sim pid: 59677
[CHILD]: Pinged top!
[CHILD]: Pinged top!

Success!
[CHILD]: Pinged top!
[PARENT]: Simulation done.
[CHILD]: Pinged top!
[CHILD]: pings: [('1.25', '67028'), ('2.5300000000000002', '71192'), ('3.8', '64960')]
[CHILD]: Pinging done.
```

### top
The script uses `top` to obtain all metrics. Top's readings are more transparent and the scripts runtime will be drastically reduced. With top it's easy to retrieve various metrics interchangeably. This will require threading or processing to ping top in parallel with the running the simulation.

# Presentation

uhhhh