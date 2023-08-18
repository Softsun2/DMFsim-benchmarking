# Round 2 Revisions

## Archiving
- [ ] The DMFsim package must be made available (versioned archive w/ own DOI)
    - Zenodo integrates with Github fortunately. Zenodo archives and registers a DOI per repository release.

## Revisions
- [X] 1. Omitting the GUI flag is not verbose enough. `--gui` option doesn't work on WSL.
    - Verbosity solved by the solution to #2.
    - Added instructions for the user to follow in order to avoid the tkinter display issue. 
- [X] 2. Implement verbosity with chess-like terminology...
    - I added a [verbose member to the lab](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Lab.py#L53). If the lab's member `verbose` is set to true, when droplets are moved [the move information is printed](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Lab.py#L588). I could add print statements for merging and pulling but I'd instead only implement these if it's truly desired.
- [X] 3. Merging visualization bug? Merges into approaching instead of the target.
    - This is [intentional](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Lab.py#L721). "Estimate the new droplet center as the weighted average of the two droplets' centers".
- [X] 4. Code hangs on gl=3 and gs<32 without obvious reason.
    - When the gridsize is less than 32 [the PCR and Purify pull sites are not generated](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Tutorial.py#L179C1-L181C1). Added a [warning](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Tutorial.py#L122) when the gridsize is less than 32. Also [now raising an assertion error](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Scheduler.py#L503) when there are no pull sites for a droplet.
    - Added [warnings](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Scheduler.py#L89C13-L104C1) for when hangs may occur. Warnings are printed when Andrew's original timeout conditions are met.
- [X] 5. `--host-string` crashes the program if the file structure is not set up.
    - Added the following snippet to `Tutorial.py`. [Generates the data dir if necessary](https://github.com/Softsun2/DMFsim-benchmarking/blob/986ee1641f368d5c76a27bd272c0e7ee5dbcd89a/DMFsim/Tutorial.py#L227C9-L229C47) instead of crashing.

# Releasing

When the revisions have been made, run through the readme and ensure everything still works. If so merge data-review into main and make a new release.
