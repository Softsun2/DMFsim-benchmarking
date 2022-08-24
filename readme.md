# Benchmarking
The current dependent vairables are runtime, memory consumption/usage, and cpu usage.

The current independent variables are system hardware, gridsize, and potentially the number of chemistry sites (do this if we have time).


## [The Script](Benchmark.py)
The script obtains data with [top](https://man7.org/linux/man-pages/man1/top.1.html) and exports that data to a spreadsheet readable format (csv). Message me if there are questions or issues with the script.


### Usage
The following assumes that the benchmarking repo is located at the top level of the `DMFsim` repo.

#### Parameters
At the top of [Benchmark.py](Benchmark.py) you can set the constant variables for the trials, the number of rounds of benchmarking, and range of grid sizes to benchmark against.

#### Using my [shell script](python-benchmarker)
 The following command installs the provided modified files then runs the benchmarking script. The provided files allow for the benchmarking script to pass grid sizes as command ine arguments and to exceed the timeout conditions.
```
./python-benchmarker run
```
The following command restores the user's original `toprc` and python files if they existed prior to running the script.
```
./python-benchmarker restore
```

#### Manually
Make backups of the following original files if desired.
1) Copy/replace all the included python files to the `DMFsim` directory.
2) Copy the included `toprc` to `~/.config/procps/toprc`. You may need to create the config directory if it doesn't exist.
3) Run the benchmarking script.
    ```
    python3 Benchmark.py all python3 ../Tutorial.py
    ```


### Output Data
Data is exported to a directory within the benchmarking repo named `raw-data`. The file prefix `hw` for "hardware" means that the simulation was ran at the default gridsize, for the independent variable: system hardware. The file prefix `gs-<gridsize>` for "gridsize" means that the simulation was ran at the gridsize `<gridsize>`, for the independent variable: gridsize. All csv file names end with an integer identifying the benchmarking round of corresponding independent variable. Each column header describes that column's data. See top's [man page](https://man7.org/linux/man-pages/man1/top.1.html) for an explanation of the headers used. Runtime is measured in seconds, memory is measured in Gib, and CPU usage is measured as a proportion.


### Formatted Data
Formatted data is exported to a directory within the benchmarking repo named `formatted-data`. The file names describe the data it contains. The data is formatted to make graphing easier. You can see how the formatted data was plotted in [this](https://docs.google.com/spreadsheets/d/1Bl_izLWv8FmEm-lo52ixJs7STvj6tqPssFivL9YJV4Q/edit?usp=sharing)  sheet.


# Presentations

You can view how the data obtained from this script on the python implementation was interpreted in [this](https://docs.google.com/presentation/d/12su1NnNt0wvW-tbnNfm5jFDmZSdjTUpHCXEooiUXz8U/edit?usp=sharing) presentation.

Future cpp presentaion.