### Compiling and Running Steps:

1. **Build Dataframe library**  
   On the server machinem, navigate to the parent directory (`experiments/scripts`) and run:  
   ```sh
   ./dataframe.sh
   ```

2. **Build the Dataframe server**  
   On the server machine, run:  
   ```sh
   ./build_server.sh
   ```
   This compiles the Dataframe server linked with the Aspen runtime. It also sets up huge pages for shared memory and loads the ksched module into the kernel.

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
   Before running, you need to update the CONFIGURATION SETTINGS at the beginning of the Python script to reflect your machine's information.
   `<option>` can be `non-preemptive`, `signal`, `uintr`, `concord-fine_tuned`, or `concord`. 
   The script launches the load generator on the client machine and the Dataframe server on the server machine.The results are saved in `experiments/result/fig6/<option>` on the client machine.

5. **Plot the results**  
   Once the results of all options are collected, on the client machine, run:  
   ```sh
   python3 plot.py
   ```
    The generated figure is stored in: `experiments/result/fig6`.
