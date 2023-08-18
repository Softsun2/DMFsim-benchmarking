# Round 2 Revisions

## Archiving
- [ ] The DMFsim package must be made available (versioned archive w/ own DOI)
    - Zenodo integrates with Github fortunately. Zenodo archives and registers a DOI per repository release.

## Revisions
- [X] 1. Omitting the GUI flag is not verbose enough. `--gui` option doesn't work on WSL.
    - Verbosity solved by the solution to #2.
    - Added instructions for the user to follow in order to avoid the tkinter display issue. 
- [X] 2. Implement verbosity with chess-like terminology...
    - I added a verbose memeber to the lab. If the lab's memeber `verbose` is set to true, when droplets are moved the move information is printed. I could add print statements for merging and pulling but I'd instead only implement these if it's truly desired.
- [X] 3. Merging visualization bug? Merges into approaching instead of the target.
    - This is intentional. "Estimate the new droplet center as the weighted average of the two droplets' centers".
- [X] 4. Code hangs on gl=3 and gs<32 without obvious reason.
    - When the gridsize is less than 32 the PCR and Purify pull sites are not generated. Added a warning when the gridsize is less than 32. Also now raising an assertion error when there are no pull sites for a droplet.
    - Added warnings for when hangs may occur. Warnings are printed when Andrew's original timeout conditions are met.
- [X] 5. `--host-string` crashes the program if the file structure is not set up.
    - Added the following snippet to `Tutorial.py`. Generates the data dir if necessary instead of crashing.

# Releasing

When the revisions have been made, run through the readme and ensure everything still works. If so merge data-review into main and make a new release.
