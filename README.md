# Aspen

Aspen is a preemptive user-space runtime system that enables fine-grained, microsecond-level preemption. 
For more details, refer to the paper. 
Aspen is built on top of [Caladan](https://github.com/shenango/caladan.git).
The following instructions have some content directly copied from the Caladan repository.

## How to Build and Run 

The followings outlines the steps to build Aspen/Caladan and run a simple application. 
For instructions on running Aspen's experiments, see [Aspen Experiments](#aspen-experiments).

1) Clone the repository (developed based on Caladan).

2) Install dependencies.

```
sudo apt install make gcc cmake pkg-config libnl-3-dev libnl-route-3-dev libnuma-dev uuid-dev libssl-dev libaio-dev libcunit1-dev libclang-dev libncurses-dev meson python3-pyelftools
```

3) Set up submodules (e.g., DPDK, and rdma-core).

```
make submodules
```

4) Build iokernel, runtime, and ksched and perform some machine setup.
Before building, set the parameters in build/config 
(e.g., `CONFIG_DIRECTPATH=y` to use directpath (see below for details), 
and the MLX4 or MLX5 flags to use MLX4 or MLX5 NICs, respectively, ). 
To enable debugging, set `CONFIG_DEBUG=y` before building. 
Before building, you mignt need to modify the NIC port ID used for dpdk,
in the source file iokernel/dpdk.c:283 (`dp.port = 1;`). 
The port is typically either 0 or 1.

```
# Build the iokernel and runtime.
make clean && make

# Build the ksched module and load it into kernel.
pushd ksched
make clean && make
popd
sudo ./scripts/setup_machine.sh

# If you are building rust applications like `apps/synthetic`, you can skip the following steps of building c++ binding and shim.
pushd bindings/cc
make clean && make
popd

pushd shim
make clean && make
popd
```

5) Install Rust and build a synthetic client-server application.

```
curl https://sh.rustup.rs -sSf | sh
rustup default nightly
```
```
cd apps/synthetic
cargo clean
cargo update
cargo build --release
```

6) Run the synthetic application with a client and server. The client
sends requests to the server, which performs a specified amount of
fake work (e.g., computing square roots for 10us), before responding.

On the server:
```
sudo ./iokerneld simple noht nobw 
./apps/synthetic/target/release/synthetic 192.168.1.100:5000 --config server.config --mode spawner-server
```

On the client:
```
sudo ./iokerneld simple noht nobw
./apps/synthetic/target/release/synthetic 192.168.1.100:5000 --config client.config --mode runtime-client
```

Explanation of iokerneld parameters: 
- `simple`: Uses a simplified scheduler policy. 
Since Aspen does not require Caladan’s methods for addressing CPU interference, this `simple` mode is sufficient for experimentation.
- `noht`: Disables hyperthreading.
- `nobw`: Disables the bandwidth controller.


### NICs
This code has been tested with Intel 82599ES 10 Gbits/s NICs, Mellanox ConnectX-3 Pro 10 Gbits/s NICs, and Mellanox Connect X-5 40 Gbits/s NICs. **Aspen's all experiments were conducted with Mellanox ConnectX-6**. If you use Mellanox NICs, you should install the Mellanox OFED compataible with your OS. 


### Directpath
Directpath allows runtime cores to directly send packets to/receive packets from the NIC, enabling
higher throughput than when the IOKernel handles all packets.
Directpath is currently only supported with Mellanox ConnectX-5 using Mellanox OFED v4.6 or newer.
NIC firmware must include support for User Context Objects (DEVX) and Software Managed Steering Tables.
For the ConnectX-5, the firmware version must be at least 16.26.1040. Additionally, directpath requires
Linux kernel version 5.0.0 or newer.

To enable directpath, set `CONFIG_DIRECTPATH=y` in build/config before building and add `enable_directpath 1`
to the config file for all runtimes that should use directpath. Each runtime launched with directpath must
currently run as root and have a unique IP address.


## Aspen Experiments

This repository (along with its multiple submodules) contains instructions and scripts for the experiments presented in the paper. The scripts are located in `experiments/scripts`.  
Within this directory, each subfolder corresponds to a figure from the paper and includes the scripts along with a README explaining how to use them.
For example, `experiments/scripts/fig5` contains the scripts for the Figure 5 experiment, along with a README.

### Benchmarking Study

This study evaluates three preemption mechanisms: signals, compiler instrumentation, and user interrupts.

- **Figure 1**: Basic preemption cost of different preemption mechanisms on some microbenchmark programs.  
  *TODO: A submodule for concord will be added.*
- **Figure 8**: The preemption cost and context-switch cost on three applications.

### Aspen-KB

This study evaluates preemption mechanisms in a low-overhead, kernel-bypass user-space runtime system:

- **Figure 5**: RocksDB performance in Aspen-KB under different preemption mechanisms.
- **Figure 6**: DataFrame performance in Aspen-KB under different preemption mechanisms.
- **Figure 10**: RocksDB performance achieved by Aspen compared to other systems.

To run these experiments, in additon to the prerequisites mentioned in [How to Build and Run](#how-to-build-and-run), you need to have `clang-11`, `clang++-11` and `opt-11`. You can verify their availability by running the following commands:

```sh
clang-11 --version
clang++-11 --version
opt-11 --version
```

### Aspen-Go 

This study is conducted in the context of the widely used Go runtime, which serves millions of developers. Aspen-Go extends the standard Go runtime (version 1.21) by enabling finer-grained preemption and network polling.

- **Figure 7**: BadgerDB performance with unmodified Go and Aspen-Go. 
The data used to populate BadgerDB is available at:  
  [Google Drive Link](https://drive.google.com/file/d/1umPzzNkfNgkitHGt_wl-5t2stFBN6o4w/view?usp=share_link).


### Experiment Setup

End-to-end experiments (Figures 5, 6, 7, and 10) require two machines: a **client machine** for load generation and a **server machine** running the evaluated applications (RocksDB, DataFrame, and BadgerDB). 

The following setup may not be necessary for the experiments but describes the environment used to obtain the results in the paper: Both machines have **28-core Intel Xeon Gold 5420+ CPUs (2.0 GHz)**, **256 GB RAM**, and **100 Gbit/s Mellanox ConnectX-6 Dx NICs** connected via a **100GbE Mellanox SN2700 switch**.
Both machines use **Ubuntu 22.04.4**. The client machine uses **kernel 6.8.0**, while the server machine requires OS support for user interrupts and runs a [custom Intel kernel](https://github.com/intel/uintr-linux-kernel) based on a lower **version 6.0.0**. Hyperthreading, TurboBoost, frequency scaling, and C-states are disabled.