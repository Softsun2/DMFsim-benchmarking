# Plan
1. Decide on a benchmarking procedure.
    * Still haven't chosen exact methods for producing runtimes and cpu usage.
2. Implement this procedure with a script.
    * The script should do two things, obtain the data with the chosen benchmarking tools and export that data to a spreadsheet readable format.
3. Plot the data.
4. Make the presentation.


# Benchmarking
Ajay wants a draft of the presentation by Wednesday.

We have two objectives, to obtain a reference for which to compare future code to as well as identifying bottlenecks and breaking points of the existing code.

The goal is to produce a reusable benchmarking procedure that's independent of the programs implementation.

The current dependent vairables are runtime, memory consumption/usage, and cpu usage.

The current independent variables are system hardware, gridsize, and potentially the number of chemistry sites (do this if we have time).

For limitation testing we are searching for breaking inputs (if there's time explain how to adress these inputs). We are also looking for bottlenecks at a highlevel. Ajay suggested mentioning these towards the end of the presentation.

The plan is to average the data over multiple rounds of benchmarking on all of our machines.


## [The Script](Benchmark.py)
As mentioned in the plan, the script should obtain data with the chosen benchmarking tools and export that data to a spreadsheet readable format. The scripts usage can be displayed with `python3 Benchmark.py help`. The basic usage is `python3 Benchmark.py [option] [cmd]` when the script is finished we would most likely run `python3 benchmark.py all python3 ../DMFsim/Tutorial.py`, this assumes that this repo is a sibling to the python repo. This script makes the assumption that we can pass benchmarking parameters such as girdsize to the cmd, I've tweaked `Tutorial.py` to handle this, this is subject to change.


### Timing

Any timer really, perf's timer seems accurate.


### Memory Profiling

#### Valgrind ([Massif](https://valgrind.org/docs/manual/ms-manual.html))
(I've settled on this, let me know if you would like to use another option) We can use valgrind to examine memory usage (heap consumption with respect to time) with `valgrind --tool=massif python3 Tutorial.py`, this will output a `ms_print` readable file with the format massif.out.\<pid\> (See the script for the exact command). There's a gui to better visualize the output called *massif-visualizer*. I like this option becuase it's independent from python. Although, valgrind is unix only. Doesn't profile at the function level (I believe). I found a [massif parser](https://github.com/MathieuTurcotte/msparser) that we could use to export the data.


### CPU Profiling

#### Perf
Uses performance counters to monitor hardware events such as instructions executed. `perf stat python3 Tutorial.py` produces event counts. Not sure what metric we'd use from this? Isn't clock cycles just another way of saying the runtime? Maybe the number of instructions executed would be better? Will need to look into this.


# Presentation

uhhhh