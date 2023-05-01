# DMFsim-benchmarking
Source independent DMFsim benchmarking.

## File Structure
```
% tree -L 1 .
.
├── Benchmark.py        # The benchmarking script
├── data                # Organized source data for paper
├── DMFsim              # Simulation source code
├── readme.md
├── shell.nix           # Nix dev shell declaration
└── toprc               # Provided top configuration file
```

Additional directories will be generated upon running the benchmarking script exporting data. This is explained further [later](readme.md#output data).

## [The Script](Benchmark.py)
The script obtains hardware metrics and gene synthesis congestion data while running the simulation. Hardware metrics are obtained using [top](https://man7.org/linux/man-pages/man1/top.1.html). Gene synthesis congestion data are recorded directly by the simulation. After obtaining the data the script exports and formats the data to a spreadsheet readable format (csv).

### Running the Script

#### Setup
1) Copy/replace all the included python files within `patched-python-files` to the `DMFsim` directory.
1) Obtain provided source code (clone or download this repo).
2) Copy the included `toprc` to `~/.config/procps/toprc`. You may need to create the config directory if it doesn't exist.
    ```
    # from the repo's root
    test [ ~/.config/procps -d ] || mkdir -p ~/.config/procps
    cp ./toprc ~/.config/procps
    ```
3) Run the benchmarking script. Refer to [Usage](readme.md#usage) for usage information.
    ```
    python3 Benchmark.py all python3 ../Tutorial.py
    ```

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
Something to note is that when script's independent variable is "gene-length" (either from passing the option "all" or "gene-length") the previously mentioned metrics are recorded normally as well as **congestion metrics**. The congestion metrics are unique to the independent variable "gene-length". The congestion metrics are the total number of droplets pulled, the maximum number of concurrent droplets, and the maximum value of congestion (**TODO**). Since `top` can't access this information, the simulation does so internally.

#### Parameters
At the top of [Benchmark.py](Benchmark.py) you can set the benchmarking parameters such as constants, independent variable ranges, and assign target machines. Variables are documented within the file.

### Output Data
Data is exported to a directory within the benchmarking repo named `raw-data`.

#### File Prefixes
* `hw`: for "hardware" means that the simulation was ran at the default gridsize, for the independent variable: system hardware.
* `gs-<gridsize>`: for "gridsize" means that the simulation was ran at the gridsize `<gridsize>`, for the independent variable: gridsize.
* `gl-<gene-length>`: for "gene length" means that the simulation was ran at the gene length `<gene-length>`, for the independent variable: gene length.

All csv file names are appended with an integer identifying the benchmarking round of the corresponding independent variable. Runtime is measured in seconds, memory is measured in Gib, CPU usage is measured as a proportion, and congestion is the ratio of the total number of droplets pulled from reservoirs to the number of grid points.

#### Formatted Data
Formatted data is exported to a directory within the benchmarking repo named `formatted-data`. The directory structure and file names describe the formatted data. The data is formatted to make organization and graphing more convenient.

## Data Usage
The following list denotes the data used to create each figure and table in the paper.
* Table 2: hardware.csv
* Table 3: hardware.csv
* Fig 15: hardware.csv
* Fig 16: gridsize.csv
* Fig 17: gridsize.csv
* Fig 18: gridsize.csv
* Table 4: problem-size.csv
* Fig 19: problem-size.csv
* Fig 21: problem-size.csv
* Fig 22: gene-length.csv
* Fig 23: gene-length.csv

## Aside
The program [gephi](https://gephi.org/) was used in order to determine runtime of sub-routines within the simulation.
