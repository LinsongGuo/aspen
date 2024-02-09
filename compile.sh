make clean
make -j

pushd ksched
make clean
make -j
popd
sudo ./scripts/setup_machine.sh 

pushd binding/cc
make clean
make -j
popd

pushd shim
make clean
make -j
popd