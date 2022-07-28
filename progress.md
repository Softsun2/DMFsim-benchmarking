# Overview

We have two objectives, to obtain a reference for which to compare future code to as well as identifying bottlenecks and breaking points of the existing code.

The goal is to produce a reusable benchmarking procedure that's independent of the programs implementation.

The current dependent variables are runtime, memory usage, and cpu usage.

The current independent variables are system hardware, gridsize, and potentially the number of chemistry sites.

We are developing a script that first obtains data on the specified metrics then exports that data into csv files that we can manipulate and plot in a spreadsheet.

We will be obtaining multiple rounds of data for each metric on each of our machines.

# Progress

* The skeleton of the script has been layed out.
* Tools have been selected for obtaining all the metrics.
    * time - for runtimes
    * valgrind (massif) - for memory usage
    * top - for cpu usage
    * pycallgraph - for function level timing
* Obtaining runtimes and cpu usage is being worked on.
* Obtaining memory usage is done.
* We still need to export the data. Should be easier than getting the data, I've used pandas in the past.

# Plan
1. Complete the script.
2. Plot the data and analyze the data in a meaningful way.
4. Finish limitation testing the python implementation.
    * Search for breaking inputs.
    * Search for bottlenecks.
5. Compile information into a presentation.