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

Additional directories will be generated upon running the benchmarking script exporting data. This is explained further [later](readme.md#output-data).

## Installation

The program was designed to run on Ubuntu 20.04 however it should work on other Linux distributions.

1.  Obtain the source code (clone or download repo).
2.  Install the package and its dependencies: `pip install .`.
3.  Install the provided `toprc`. Back-up up current `toprc` if desired.
    `test -d ~/.config/procps || mkdir -p ~/.config/procps`
    `cp ./toprc ~/.config/procps`
4.  Run the benchmarking script. Refer to [Usage](readme.md#usage) for usage information.
    ```
    python3 Benchmark.py all python3 DMFsim/Tutorial.py
    ```

## Configuration

`config.ini` is the benchmarking program's configuration file. `config.ini` contains three sections. These values determine the bahaviour of the program.

1.  `Benchmarking`: Benchmarking configurations, number of rounds and data collection frequency.
2.  `Constant Variables`: Values for contants. **Note**: if the constant variable `Machine` does not match the current host machine's name (result of `hostname`) gridsize and gene-length benchmarking will **not** be performed.
3.  `Independent Variables`: Values for independent variables.

## Usage

```
usage: Benchmark.py [-h] {all,hardware,gridsize,gene-length} cmd

positional arguments:
  {all,hardware,gridsize,gene-length}
                        benchmark all metrics, hardware, gridsize, or gene-length
  cmd                   the command to be benchmarked

optional arguments:
  -h, --help            show this help message and exit
```

-   option:
    -   `all`: Runs hardware, gridsize, and gene-length benchmarking.
    -   `hardware`: Runs hardware benchmarking.
    -   `gridsize`: Runs gridsize benchmarking.
    -   `gene-length`: Runs gene-length benchmarking.

#### Parameters

At the top of [Benchmark.py](Benchmark.py) you can set the benchmarking parameters such as constants, independent variable ranges, and assign target machines. Variables are documented within the file.

### Output Data

Data is exported to a directory within the benchmarking repo named `raw-data`.

#### File Prefixes

-   `hw`: for "hardware" means that the simulation was ran at the default gridsize, for the independent variable: system hardware.
-   `gs-<gridsize>`: for "gridsize" means that the simulation was ran at the gridsize `<gridsize>`, for the independent variable: gridsize.
-   `gl-<gene-length>`: for "gene length" means that the simulation was ran at the gene length `<gene-length>`, for the independent variable: gene length.

All csv file names are appended with an integer identifying the benchmarking round of the corresponding independent variable. Runtime is measured in seconds, memory is measured in Gib, CPU usage is measured as a proportion, and congestion is the ratio of the total number of droplets pulled from reservoirs to the number of grid points.

#### Formatted Data

Formatted data is exported to a directory within the benchmarking repo named `formatted-data`. The directory structure and file names describe the formatted data. The data is formatted to make organization and graphing more convenient.

## Data Usage

The following list denotes the data used to create each figure and table in the paper.

-   Table 2: [hardware.csv](data/hardware.csv)
-   Table 3: [hardware.csv](data/hardware.csv)
-   Fig 15: [hardware.csv](data/hardware.csv)
-   Fig 16: [gridsize.csv](data/gridsize.csv)
-   Fig 17: [gridsize.csv](data/gridsize.csv)
-   Fig 18: [gridsize.csv](data/gridsize.csv)
-   Table 4: [problem-size.csv](data/problem-size.csv)
-   Fig 19: [problem-size.csv](data/problem-size.csv)
-   Fig 21: [problem-size.csv](data/problem-size.csv)
-   Fig 22: [gene-length.csv](data/gene-length.csv)
-   Fig 23: [gene-length.csv](data/gene-length.csv)

## Aside

The program [gephi](https://gephi.org/) was used in order to determine the runtimes of sub-routines within the simulation.
