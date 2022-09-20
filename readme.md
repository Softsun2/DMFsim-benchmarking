# Benchmarking
The current dependent vairables are runtime, memory consumption/usage, and cpu usage.

The current independent variables are system hardware, gridsize, and gene length.


## [The Script](Benchmark.py)
The script obtains metric data from the simulation with [top](https://man7.org/linux/man-pages/man1/top.1.html) and exports that data to a spreadsheet readable format (csv).

### Running the Script
The following assumes that the benchmarking repo is located at the top level of the `DMFsim` repo.

#### Setup
1) Copy/replace all the included python files within `patched-python-files` to the `DMFsim` directory.
2) Copy the included `toprc` to `~/.config/procps/toprc`. You may need to create the config directory if it doesn't exist.
3) Run the benchmarking script. Refer to [Usage](##Usage) for usage information.
    ```
    python3 Benchmark.py all python3 ../Tutorial.py
    ```
*\*Make backups of the original files if desired.\**

#### Usage
Running `python3 Benchmark.py help` will print the following information.
```
Usage: python3 Benchmark.py [option] [cmd]
   options:
       all         - benchmark all options
       hardware    - benchmark hardware only
       gridsize    - benchmark gridsize only
       gene-length - benchmark only gene length & congestion
       help        - display usage
```
Something to note is that when script's independent variable is "gene-length" (either from passing the option "all" or "gene-length") the previously mentioned metrics are recorded normally as well as congestion metrics. The congestion metrics are unique to the independent variable "gene-length". The congestion metrics are the total number of droplets pulled, the maximum number of concurrent droplets, and the maximum value of congestion (as defined in [`Lab.py`](patched-python-files/Lab.py)). Since `top` obviously can't access this information, the simulation does so internally.

#### Parameters
At the top of [Benchmark.py](Benchmark.py) you can set the benchmarking parameters such as constants, independent variable ranges, and assign host machines. Variables are documented within the file.

### Output Data
Data is exported to a directory within the benchmarking repo named `raw-data`. The file prefix `hw` for "hardware" means that the simulation was ran at the default gridsize, for the independent variable: system hardware. The file prefix `gs-<gridsize>` for "gridsize" means that the simulation was ran at the gridsize `<gridsize>`, for the independent variable: gridsize. All csv file names are appended with an integer identifying the benchmarking round of the corresponding independent variable. The file prefix `gl-<gene-length>` for "gene length" means that the simulation was ran at the gene length `<gene-length>`, for the independent variable: gene length. All csv file names are appended with an integer identifying the benchmarking round of the corresponding independent variable. Runtime is measured in seconds, memory is measured in Gib, and CPU usage is measured as a proportion.

### Formatted Data
Formatted data is exported to a directory within the benchmarking repo named `formatted-data`. The directory structure and file names describe the formatted data. The data is formatted to make graphing more convenient. You can see how the formatted data was plotted in [this](https://docs.google.com/spreadsheets/d/1Bl_izLWv8FmEm-lo52ixJs7STvj6tqPssFivL9YJV4Q/edit?usp=sharing)  sheet.

# Presentations

You can view how the data obtained from this script on the python implementation was interpreted in [this](https://docs.google.com/presentation/d/12su1NnNt0wvW-tbnNfm5jFDmZSdjTUpHCXEooiUXz8U/edit?usp=sharing) presentation.

Future cpp presentaion.