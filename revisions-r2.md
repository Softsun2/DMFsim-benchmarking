# Round 2 Revisions

## Archiving
- [ ] The DMFsim package must be made available (versioned archive w/ own DOI)
    - Zenodo integrates with Github fortunately. Zenodo archives and registers a DOI per repository release.

## Revisions
- [ ] 1. Omitting the GUI flag is not verbose enough. `--gui` option doesn't work on WSL.
    - Verbosity solved by the solution to #2.
    - I don't have convenient access to WSL to solve this.
        - [`$DISPLAY` Related](https://stackoverflow.com/questions/48254530/tkinter-in-ubuntu-inside-windows-10-error-no-display-name-and-no-display-env)?
        - [Driver Related](https://learn.microsoft.com/en-us/windows/wsl/tutorials/gui-apps)?
        - If either of these works update the readme.
- [X] 2. Implement verbosity with chess-like terminology...
    - I added a verbose flag to `Tutorial.py` (see `python3 Tutorial.py -h`) which passes it to the Lab. If the flag is present when droplets are moved the move information is printed. I could add print statements for merging and pulling but I'd instead only implement these if it's truly desired.
    - Verbosity of movement is handled mostly by the following snippets:
        ```python3
        # Lab.py
        ## Lab.Advance
        for droplet in self.droplets:
            if self.verbose:
                droplet.Verbose_Move(self.grid, self.time)
            else:
                droplet.Move(self.grid, self.time)
        ```
        ```python3
        # Lab.py
        ## Droplet.Verbose_Move
        def Verbose_Move(self, grid, time = None):     
            x_0, y_0 = self.coords
            self.Move(grid, time)
            x_1, y_1 = self.coords
            
            droplets_moved = x_0 != x_1 or y_0 != y_1
            if droplets_moved and not self.to_delete:
                print(f'Droplet {self.species} moved from {[x_0, y_0]} to {[x_1, y_1]}.')
        ```
- [X] 3. Merging visualization bug? Merges into approaching instead of the target.
    - This is intentional. "Estimate the new droplet center as the weighted average of the two droplets' centers".
- [X] 4. Code hangs on gl=3 and gs<32 without obvious reason.
    - I disabled the timeouts on the simulation so we could benchmark difficult problems. Considering Andrew added timeouts over detecting if the synthesis was possible suggests to me that it would be difficult to know if a synthesis was possible. I added warnings that the synthesis may not be possible when Andrew's original timeout conditions are met.
    - Added the following snippet.
        ```python3
        # Scheduler.py
        ## Scheduler.Compile_Instructions
        if not warned_runtime_time and time.time() - start_time > self.time_limit:
            warned_runtime_time = True
            print(f'RUNTIMEWARNING! The runtime has exceeded {self.time_limit}! ' \
                    f'This may indicate the synthesis is impossible!')
        if not warned_runtime_steps and self.time > num:
            warned_runtime_steps = True
            print(f'RUNTIMEWARNING! The runtime has exceeded {num} time steps! ' \
                    f'This may indicate the synthesis is impossible!')
        if not warned_no_progress and self.no_progress_tracker > self.no_progress_limit:
            warned_no_progress = True
            print(f'RUNTIMEWARNING! No progress has been made in over ' \
                    f'{self.no_progress_limit} time steps! ' \
                    f'This may indicate the synthesis is impossible!')
        ```
- [X] 5. `--host-string` crashes the program if the file structure is not set up.
    - Added the following snippet to `Tutorial.py`. Generates the data dir if necessary instead of crashing.
        ```python3
        gene_length_data_path = f'raw-data/{host_string}/'
    
        # create data dir if necessary
        if not os.path.isdir(gene_length_data_path):
            os.makedirs(gene_length_data_path)
        ```

# Releasing

When the revisions have been made, run through the readme and ensure everything still works. If so merge data-review into main and make a new release.
