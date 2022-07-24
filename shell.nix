{ pkgs ? import <nixpkgs> {} }:
  pkgs.mkShell {
    # nativeBuildInputs is usually what you want -- tools you need to run
    nativeBuildInputs = with pkgs; [
      # program dependencies
      python37
      python37Packages.numpy
      python37Packages.matplotlib

      # callgraph
      python37Packages.pycallgraph
      graphviz 
      gephi

      # mem profiling
      python37Packages.psutil
      valgrind
      massif-visualizer

      # cpu profiling
      # using perf, I have this install system wide

      # ...
    ];
}
