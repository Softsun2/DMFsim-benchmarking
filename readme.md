# DMFsim-benchmarking

[![DOI](https://zenodo.org/badge/517434821.svg)](https://zenodo.org/badge/latestdoi/517434821)

This is the repository containing the DMFsim code and the DMFsim benchmarking code. This README.md provides a comprehensive introduction

## File Structure

Please type the following command to view the structure of the repository:

```
$ tree -L 1 .
.
├── DMFsim
├── DMFsim-benchmarking
├── Dockerfile
├── config.ini
├── data
├── readme.md
├── setup.py
└── toprc
```

Here we explain the purpose of each folder/file:

-   DMFsim: The simulation source code, slightly tweaked to capture congestion data.
-   DMFsim-benchmarking: The benchmarking source code.
-   Dockerfile: Docker image declaration to setup the benchmarking environment and install the benchmarking program.
-   config.ini: The benchmarking program's configuration file.
-   data: Contains organized data used in the paper.
-   setup.py: Benchmarker installer.
-   toprc: The provided top configuration file.

Additional directories will be generated upon running the benchmarking script exporting data. This is explained in the [output data section](readme.md#output-data).

## Environment and Installation

There are two installation options: 
1. Manually installing the dependencies 
2. Running a docker container. 
   
   The manual setup was tested on Ubuntu 20.04 however it should work on other Linux distributions. The docker container should work on Windows, MacOS, or Linux.

### Option 1: Manual Setup and Installation

The manual setup was tested on Ubuntu 20.04 however it should work on other Linux distributions.

#### Environment

1.    python3: `apt-get install python3`.
        1.    Ensure the "tkinter" package is installed. If running `python3 -m tkinter` in ubuntu displays "No module named tkinter", then tkinter is not installed. Please run `apt-get install python3-tk` to install tkinter.
3.    pip: `apt-get install python3-pip`.

#### Installation
Install the program with the following steps:

1.  Obtain the source code (clone or download and extract repo).
2.  From the command line cd into the top-level repository.
    ```
    cd path/to/DMFsim-benchmarking
    ```
3.  Install the package and its dependencies. This will run setup.py
    ```
    pip install .
    ```
4.  Install the provided toprc. Save the existing toprc if desired before running the following command.
    ```
    test -d ~/.config/procps || mkdir -p ~/.config/procps
    cp ./toprc ~/.config/procps
    ```
5.  Run the benchmarking script. Refer to [Usage](readme.md#usage) for usage information. Ensure that your hostname in 'config.ini' matches your hostname. You can find your hostname by running `hostname` in the Ubuntu terminal. Open config.ini and update the machine name with `hostname` then try running the command below again.
    ```
    python3 DMFsim-benchmarking/Benchmark.py all 'python3 DMFsim/Tutorial.py'
    ```

### Option 2: Docker Container 

[Docker](https://www.docker.com/) is a virtualization software that delivers software in packages called containers. Docker is supported on Windows, MacOS, and Linux. Docker will virtualize an Ubuntu machine with the benchmarking software pre-installed in a docker container.

1.  [Install docker](https://docs.docker.com/engine/install/).
2.  Make sure you have the docker engine running by opening it on your system.
3.  From the command line cd into the repo.
    ```
    cd path/to/DMFsim-benchmarking-data-review
    ```
4.  Build the docker image. This may take a few minutes to complete.
    ```
    docker build -t dmfsim-benchmarking .
    ```
5.  Run the docker container. This will drop you into a bash shell inside the container within the copied DMFsim-benchmarking repo.
    ```
    docker run -it dmfsim-benchmarking bash
    ```
6.  Run the benchmarking script. Refer to [Usage](readme.md#usage) for usage information.
    ```
    python3 DMFsim-benchmarking/Benchmark.py all 'python3 DMFsim/Tutorial.py'
    ```
7.  Exit the container by exiting the shell. Docker images and containers can consume your resources, [clean up the image and container](https://www.digitalocean.com/community/tutorials/how-to-remove-docker-images-containers-and-volumes) when you are done if you desire.

## Configuration

[config.ini](config.ini) is the benchmarking program's configuration file. The configurations determine the behavior of the program. config.ini contains three sections.

1.  `[Benchmarking]`: Benchmarking configurations, number of rounds, and data collection frequency.
2.  `[Constant Variables]`: Values for contants. **The constant variable `Machine` must match your hostname**. To obtain your hostname run `hostname`.
3.  `[Independent Variables]`: Values for independent variables.

## Usage

```
usage: Benchmark.py [-h] {all,hardware,gridsize,gene-length} cmd

positional arguments:
  {all,hardware,gridsize,gene-length}
                        benchmark all independent variables, hardware, gridsize, or gene-length
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

For example.

```
python3 DMFsim-benchmarking/Benchmark.py all 'python3 DMFsim/Tutorial.py'
```

## Recreating Data

**This program is not deterministic and the machines used are not publicly accessible, meaning our exact data is impossible to recreate. However, the process used to gather our data is reproducible.**

We leave our own data in the data folder. 

### Independent Variable: Machine Hardware

In our analysis, we deemed it valuable to see how the simulation runs on different hardware. What components affect the simulation the most? We obtained hardware metrics running the simulation on three machines of varying hardware specs.

To gather this data, the following commands were run with the following configuration file.

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

Data is exported to a directory within the benchmarking repo named `raw-data` and then this raw data is formatted and placed in the `formatted-data` folder for easier understanding.

### File Prefixes

-   `hw`: for "hardware" means that the simulation was run at the default gridsize, for the independent variable: system hardware.
-   `gs-<gridsize>`: for "gridsize" means that the simulation was run at the gridsize `<gridsize>`, for the independent variable: gridsize.
-   `gl-<gene-length>`: for "gene length" means that the simulation was run at the gene length `<gene-length>`, for the independent variable: gene length.
-   `cg-<gene-length>`: for "congestion" means that the simulation was measuring congestion at a specific gene length `<gene-length>`, for the independent variable: gene length.

All CSV file names are appended with an integer identifying the benchmarking round of the corresponding independent variable. Runtime is measured in seconds, memory is measured in Gib, CPU usage is measured as a proportion, and congestion is the ratio of the total number of droplets pulled from reservoirs to the number of grid points.

### Formatted Data

Formatted data is exported to a directory within the benchmarking repo named `formatted-data`. The directory structure and file names describe the formatted data. The data is formatted to make organization and graphing more convenient.

## Data Usage

The following list denotes the data used to create each figure and table in the paper.

-   [hardware.csv](data/hardware.csv): Table 2, Table 3, Fig. 15.
-   [gridsize.csv](data/gridsize.csv): Fig. 16, Fig. 17, Fig. 18.
-   [problem-size.csv](data/problem-size.csv): Table 4, Fig. 19, Fig. 21.
-   [gene-length.csv](data/gene-length.csv): Fig. 22, Fig. 23.

## Aside

The program [gephi](https://gephi.org/) was used in order to determine the runtimes of sub-routines within the simulation. We were specifically interested in seeing how sub-routine runtimes were affected as the problem size grew (gridsize increased but congestion remained constant). Gephi and pycallgraph are required to run following commands, these commands produce gephi's file format ".gdf" which can be exported to CSV. [Our GDF and CSV files](data/gephi).

```
pycallgraph gephi -- DMFsim/Tutorial.py --gridsize 50 --gene-length 2
```

```
pycallgraph gephi -- DMFsim/Tutorial.py --gridsize 76 --gene-length 4
```

```
pycallgraph gephi -- DMFsim/Tutorial.py --gridsize 96 --gene-length 6
```

## Additional Information

It is possible to view the GUI of the Tutorial.py separately. After ensuring that the benchmarking command runs to completion, please execute the following command to view the Tutorial.py simulation. The simulation can be terminated at anytime using ctrl+C in the command line.
```
python3 tutorial.py --gui
```
Note: If you are using the "tkinter" GUI library for Python within a WSL, you may run into issues visualizing the code output. To avoid this, add the line: 
```
export DISPLAY=:0
```
to the WSL's .bashrc file. This should allow the visualization to be seen as desired.
