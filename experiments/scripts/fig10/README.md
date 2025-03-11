### Compiling and Running Steps:

1. **Build RocksDB library**  
   On the server machinem, navigate to the parent directory (`experiments/scripts`) and run:  
   ```sh
   ./rocksdb.sh
   ```
   This builds the **RocksDB (version 5.15.10) static library**.

2. **Build the RocksDB server**  
   On the server machine, run:  
   ```sh
   ./build_server.sh
   ```
   This compiles the RocksDB server linked with the Aspen runtime. It also sets up huge pages for shared memory and loads the ksched module into the kernel.

3. **Build the load generator**  
   On the client machine, run:  
   ```sh
   ./build_client.sh
   ```
   This compiles the load generator linked with the Aspen runtime. It also sets up huge pages for shared memory and loads the ksched module into the kernel.

4. **Run the experiment**  
   On the client machine, execute:  
   ```sh
   python3 run.py <option>
   ```
   where `<option>` can be `non-preemptive`, `aspen`, `aspen_wo2queue`, `aspen_wo2queue_woskip`, or `libpreemptible`. 
   Before running, you need to update the CONFIGURATION SETTINGS at the beginning of the Python script to reflect your machine's information. 
   The script launches the load generator on the client machine and the RocksDB server on the server machine.  The results are saved in `experiments/result/fig10/<option>` on the client machine.

5. **Plot the results**  
   Once the results of all options are collected, on the client machine, run:  
   ```sh
   python3 plot.py
   ```
   The generated figure is stored in: `experiments/result/fig10`.
