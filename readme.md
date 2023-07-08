# DMFsim-benchmarking

Source independent DMFsim benchmarking.

## File Structure

```
$ tree -L 1 .
.
├── DMFsim
├── DMFsim-benchmarking
├── config.ini
├── data
├── readme.md
├── setup.py
└── toprc
```

-   DMFsim: The simulation source code, slightly tweaked to capture congestion data.
-   DMFsim-benchmarking: The benchmarking source code.
-   config.ini: The benchmarking program's configuration file.
-   data: Contains organized data used in the paper.
-   setup.py: Benchmarker installer.
-   toprc: The provided top configuration file.

Additional directories will be generated upon running the benchmarking script exporting data. This is explained further [later](readme.md#output-data).

## Installation

The program was designed to run on Ubuntu 20.04 however it should work on other Linux distributions.

1.  Obtain the source code (clone or download repo).
2.  Install the package and its dependencies: `pip install .`.
3.  Install the provided toprc. Back-up up current toprc if desired.
    ```
    test -d ~/.config/procps || mkdir -p ~/.config/procps
    cp ./toprc ~/.config/procps
    ```
4.  Run the benchmarking script. Refer to [Usage](readme.md#usage) for usage information.
    ```
    python3 DMFsim-benchmarking/Benchmark.py all 'python3 DMFsim/Tutorial.py'
    ```

## Configuration

[config.ini](config.ini) is the benchmarking program's configuration file. The configurations determine the behavior of the program. config.ini contains three sections.

1.  `[Benchmarking]`: Benchmarking configurations, number of rounds, and data collection frequency.
2.  `[Constant Variables]`: Values for contants. **Note**: if the constant variable `Machine` does not match the current host machine's name (the result of `hostname`) benchmarking will **not** be performed.
3.  `[Independent Variables]`: Values for independent variables.

## Usage

```
usage: Benchmark.py [-h] {all,hardware,gridsize,gene-length} cmd

positional arguments:
  {all,hardware,gridsize,gene-length}
                        benchmark all independent variables, hardware, gridsize, or gene-length',
  cmd                   the command to be benchmarked

optional arguments:
  -h, --help            show this help message and exit
```

-   option:
    -   all: Runs hardware, gridsize, and gene-length benchmarking.
    -   hardware: Runs hardware benchmarking.
    -   gridsize: Runs gridsize benchmarking.
    -   gene-length: Runs gene-length benchmarking.
-   cmd: a command the benchmarker runs while observing machine performance.

## Recreating Data

This program is not deterministic and the machines used are not publicly accessible meaning our exact data is impossible to recreate. However, the process used to gather our data is reproducible.

### Independent Variable: Machine Hardware

In our analysis, we deemed it valuable to see how the simulation runs on different hardware. What components affect the simulation the most? We obtained hardware metrics running the simulation on three machines of varying hardware specs.

To gather this data the following commands were run with the following configuration file.

```ini
# config.ini
[Benchmarking]
Rounds = 1
PingInterval = 0.07

[Constant Variables]
Machine = csel-kh1250-13
Gridsize = 1000
GeneLength = 5

[Independent Variables]
Gridsizes = [40, 45, 50]
GeneLengths = [2, 3, 4, 5, 6, 7, 8]
```

1.  On my machine (buffalo):
    ```
    python3 DMFsim-benchmarking/Benchmark.py hardware 'python3 DMFsim/Tutorial.py'
    ```
2.  On the machine csel-kh1250-13:
    ```
    python3 DMFsim-benchmarking/Benchmark.py hardware 'python3 DMFsim/Tutorial.py'
    ```
3.  On the machine csel-kh1262-13:
    ```
    python3 DMFsim-benchmarking/Benchmark.py hardware 'python3 DMFsim/Tutorial.py'
    ```

### Independent Variable: Gridsize

We were interested to see how performance would be affected by the simulation's gridsize. We obtained hardware metrics at varying gridsizes with the following config file and command. Remember to change the `Machine` to your hostname if you're following along.

```ini
# config.ini
[Benchmarking]
Rounds = 1
PingInterval = 0.07

[Constant Variables]
Machine = csel-kh1250-13
Gridsize = 1000
GeneLength = 5

[Independent Variables]
Gridsizes = [500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500]
GeneLengths = [2, 3, 4, 5, 6, 7, 8]
```

```
python3 DMFsim-benchmarking/Benchmark.py gridsize 'python3 DMFsim/Tutorial.py'
```

### Independent Variable: Gene-length

We analyzed the performance with respect to the gene length to examine the effects of simulation congestion. We obtained hardware metrics at varying gene lengths with the following command and config file. Remember to change the `Machine` to your hostname if you're following along.

```ini
# config.ini
[Benchmarking]
Rounds = 1
PingInterval = 0.07

[Constant Variables]
Machine = csel-kh1250-13
Gridsize = 45
GeneLength = 5

[Independent Variables]
Gridsizes = [40, 45, 50]
GeneLengths = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
```

```
python3 DMFsim-benchmarking/Benchmark.py gene-length 'python3 DMFsim/Tutorial.py'
```

## Output Data

Data is exported to a directory within the benchmarking repo named `raw-data`.

### File Prefixes

-   `hw`: for "hardware" means that the simulation was run at the default gridsize, for the independent variable: system hardware.
-   `gs-<gridsize>`: for "gridsize" means that the simulation was run at the gridsize `<gridsize>`, for the independent variable: gridsize.
-   `gl-<gene-length>`: for "gene length" means that the simulation was run at the gene length `<gene-length>`, for the independent variable: gene length.

All CSV file names are appended with an integer identifying the benchmarking round of the corresponding independent variable. Runtime is measured in seconds, memory is measured in Gib, CPU usage is measured as a proportion, and congestion is the ratio of the total number of droplets pulled from reservoirs to the number of grid points.

### Formatted Data

Formatted data is exported to a directory within the benchmarking repo named `formatted-data`. The directory structure and file names describe the formatted data. The data is formatted to make organization and graphing more convenient.

## Data Usage

The following list denotes the data used to create each figure and table in the paper.

-   [hardware.csv](data/hardware.csv): TODO
-   [gridsize.csv](data/gridsize.csv): TODO
-   [problem-size.csv](data/problem-size.csv): TODO
-   [gene-length.csv](data/gene-length.csv): TODO

## Aside

The program [gephi](https://gephi.org/) was used in order to determine the runtimes of sub-routines within the simulation.

We were specifically interested in seeing how sub-routine runtimes were affected as the problem size grew (gridsize increased but congestion remained constant). The following commands were run:

```
pycallgraph gephi ./Tutorial.py --gridsize 50 --gene-length 2
```

```
pycallgraph gephi ./Tutorial.py --gridsize 76 --gene-length 4
```

```
pycallgraph gephi ./Tutorial.py --gridsize 96 --gene-length 6
```

These commands produce gephi's file format ".gdf" which can be exported to CSV as provided [here](data/gephi).
