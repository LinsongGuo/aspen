### Compiling and Running Steps:

1. **Download the data populated for BadgerDB**  
  The data used to populate BadgerDB is available at:  
  [Google Drive Link](https://drive.google.com/file/d/1umPzzNkfNgkitHGt_wl-5t2stFBN6o4w/view?usp=share_link).
   After downloading, update the `DATASET_PATH` in `run.py` to match the download location.

2. **Build the Aspen-Go runtime and BadgerDB server**  
   On the server machine, run:  
   ```sh
   ./build_server.sh
   ```
This compiles the Aspen-Go runtime and uses Aspen-Go to compile the BadgerDB server.

3. **Build the load generator** 
   On the client machine, run:  
   ```sh
   ./build_client.sh
   ```
   This compiles the load generator linked with the Aspen runtime. It also sets up huge pages for shared memory and loads the ksched module into the kernel.

4. **Run the experiment**  
   On the client machine, execute:  
   ```sh
   python3 run.py
   ```
   Before running, you need to update the CONFIGURATION SETTINGS at the beginning of the Python script to reflect your machine's information.
   The script launches the load generator on the client machine and the BadgerDB server on the server machine. The results are saved in `experiments/result/fig7` on the client machine. 
   The logs of the BadgerDB server are located at aspen-go/badger-bench/server/server_log on the server machine.

5. **Plot the results**  
   Once the results of all options are collected, on the client machine, run:  
   ```sh
   python3 plot.py
   ```
    The generated figure is stored in: `experiments/result/fig7`.
