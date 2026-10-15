# This is my notes and command by using peafowl to test with real RU, Benetel RAN550 at Coridor 312 Ceiling


```bash
ssh -A duong@tolix.sboai.cs.eurecom.fr -p 22424
ssh -A duong@peafowl.sboai.cs.eurecom.fr
ssh -J duong@tolix.sboai.cs.eurecom.fr:22424 duong@peafowl.sboai.cs.eurecom.fr
auto_reserve --reserve duong --timeout 240
ssh -A duong@sithonia
docker compose -p duong-oai-core -f docker-compose-basic-nrf.yaml up -d
docker inspect -f '{{(index .NetworkSettings.Networks "duong-oai-public-net").IPAddress}}' duong-oai-ext-dn
docker inspect oai-ext-dn --format 'Working dir: {{ index .Config.Labels "com.docker.compose.project.working_dir" }}
Compose file(s): {{ index .Config.Labels "com.docker.compose.project.config_files" }}
Project name: {{ index .Config.Labels "com.docker.compose.project" }}'
docker compose -p duong-oai-core -f docker-compose-basic-nrf.yaml --profile ros up -d
```

```bash
# some environmental variables needs seting up for each session
export TEST_DIR=/home/duong/test_oai
export DPDK_INST=/home/duong/test_oai/dpdk-stable-20.11.9
```


```bash
mkdir test_oai && cd test_oai
export TEST_DIR=$(pwd)
```

### Build gNB F release
```bash
git clone https://gerrit.o-ran-sc.org/r/o-du/phy.git $TEST_DIR/phy-f-1.0
cd $TEST_DIR/phy-f-1.0
git checkout oran_f_release_v1.0
git apply $TEST_DIR/openairinterface5g/cmake_targets/tools/oran_fhi_integration_patches/F/oaioran_F.patch

cd fhi_lib/lib
export C_INCLUDE_PATH="$DPDK_INST/include"
WIRELESS_SDK_TOOLCHAIN=gcc RTE_SDK=$DPDK_INST XRAN_DIR=$TEST_DIR/phy-f-1.0/fhi_lib make XRAN_LIB_SO=1

# tag 2025.w24
cd $TEST_DIR/openairinterface5g/cmake_targets
PKG_CONFIG_PATH=$DPDK_INST/lib/x86_64-linux-gnu/pkgconfig/ ./build_oai --gNB --build-e2 --cmake-opt -DE2AP_VERSION=E2AP_V2 --cmake-opt -DKPM_VERSION=KPM_V2_03 --ninja -t oran_fhlib_5g --cmake-opt -Dxran_LOCATION=$TEST_DIR/phy-f-1.0/fhi_lib/lib
```
### Config the test_oai/openairinterface5g/cmake_targets/setup_sriov_oru.sh for RU

What's a VF (Virtual Function)?

It's part of SR-IOV (Single Root I/O Virtualization) — a feature of the NIC hardware that lets one physical network port (a "PF", Physical Function) be split into multiple lightweight virtual copies (VFs), each with its own MAC address and PCI device ID, that can be handed directly to an application (bypassing the normal kernel network stack). That's why the SR-IOV script does things like sriov_numvfs, assigns a MAC/VLAN per VF, then binds each VF to vfio-pci for DPDK to use directly.

In this setup specifically: Peafowl's fronthaul NIC creates 2 VFs — one carries the U-plane (user data) and one carries the C-plane (control) of the O-RAN 7.2 fronthaul link to the O-RU, each needing its own MAC/VLAN

```bash
#!/bin/sh
#### 100G interface --> enp1s0f0 | VFs pcie-address --> 01:01.0, 01:01.1
#### 25G interface (PTP) --> enp193s0f1 | VFs pcie-address --> c1:11.0,c1:11.1

set -x
IF_NAME=enp193s0f1
NUM_VFs=2
U_PLANE_MAC_ADD=00:11:22:33:44:66
C_PLANE_MAC_ADD=00:11:22:33:44:67
VLAN=9
MTU=9216
U_PLANE_PCI=0000:c1:11.0
C_PLANE_PCI=0000:c1:11.1
## It will be something like this --> $DPDK_INST/bin
DPDK_DEVBIND_PREFIX=$DPDK_INST/bin
sudo ethtool -G $IF_NAME rx 8160 tx 8160
sudo sh -c "echo 0 > /sys/class/net/$IF_NAME/device/sriov_numvfs"
sudo sh -c "echo $NUM_VFs > /sys/class/net/$IF_NAME/device/sriov_numvfs"
sudo modprobe -r iavf
sudo modprobe iavf
# this next 2 lines is for C/U planes
sudo ip link set $IF_NAME vf 0 mac $U_PLANE_MAC_ADD vlan $VLAN spoofchk off mtu $MTU
sudo ip link set $IF_NAME vf 1 mac $C_PLANE_MAC_ADD vlan $VLAN spoofchk off mtu $MTU
sleep 1
sudo ${DPDK_DEVBIND_PREFIX}/dpdk-devbind.py --unbind $U_PLANE_PCI
sudo ${DPDK_DEVBIND_PREFIX}/dpdk-devbind.py --unbind $C_PLANE_PCI
sudo modprobe vfio-pci
sudo ${DPDK_DEVBIND_PREFIX}/dpdk-devbind.py --bind vfio-pci $U_PLANE_PCI
sudo ${DPDK_DEVBIND_PREFIX}/dpdk-devbind.py --bind vfio-pci $C_PLANE_PCI
```

```bash
ls /etc/ran_development/CONFs
grep -rl "3950" /etc/ran_development/CONFs
grep -rl "dl_frequencyBand.*77\|band.*=.*77" /etc/ran_development/CONFs
cat /etc/ran_development/CONFs/gnb.sa.band77.273prb.fhi72.4x4-benetel550_c0.conf
```


```bash
cd $TEST_DIR/openairinterface5g/cmake_targets
bash setup_sriov_oru.sh
sudo LD_LIBRARY_PATH=.:$DPDK_INST/lib/x86_64-linux-gnu/ ./ran_build/build/nr-softmodem -O $TEST_DIR/gnb.sa.band77.273prb.fhi72.4x4-benetel550_c0.conf --thread-pool 11,12,13,14,15,16,17,18

/etc/ran_development/CONFs/gnb.sa.band77.273prb.fhi72.4x4-benetel550_c0.conf
$TEST_DIR/gnb.sa.band77.273prb.fhi72.4x4-benetel550_c0.conf
$TEST_DIR/open_shift_core_config.conf
```


### UE

UP1 (Lab 312, N77/N78) or UP3 (outdoor, external-only, Benetel n77 units specifically).
Aquila/Corvus/Sirius are N78-only

```bash
sudo ip link set wwan0 mtu 1400

# tesing ue 1, 3, 5, 6, 7
ssh up1@up1.sboai.cs.eurecom.fr

scp -J duong@tolix.sboai.cs.eurecom.fr:22424 /home/lapdk/workspace/oai-eurecom-setups-tutorials/gazebo-ue.tar up1@up1.sboai.cs.eurecom.fr:~/binh/

docker load -i gazebo-ue.tar

# this does not work
# sudo ./start_quectel_mbim_oai.sh

sudo ./start_quectel_mbim.sh

ping -I wwan0 8.8.8.8 -c 3

ping -I wwan0 172.21.6.12 -c 3
ping -I wwan0 192.168.80.135 -c 3

sudo ./replay_from_ue.sh pcap_stream wwan0 100

sudo ./stop_quectel_mbim.sh
```

### iperf
Ping to traffic sever at 172.21.6.12 (helm-charts/oai-5g-eurecom/oai-5g-basic/README.md)

```bash
UE_RUN="$HOME/iperf_dl_100M_$(date +%Y%m%d_%H%M%S)"
iperf3 --bind-dev wwan0 -c 172.21.6.12 -u -b 100M -l 1427 -O 5 -t 60 -R 2>&1 | tee "${UE_RUN}.log"

SWEEP_DIR="$HOME/iperf_dl_sweep_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$SWEEP_DIR"
for RATE in 100 300 500 700 900 1100; do
  echo "=== DL ${RATE}M ===" | tee -a "$SWEEP_DIR/sweep.log"
  iperf3 --bind-dev wwan0 -c 172.21.6.12 -u -b "${RATE}M" -l 1427 -O 5 -t 30 -R \
    2>&1 | tee "$SWEEP_DIR/dl_${RATE}M.log"
  sleep 5
done


```
```bash
up1@up1:~$ cat iperf_dl_100M_20260909_083203.log
warning: UDP block size 1427 exceeds TCP MSS 1404, may result in fragmentation / drops
Connecting to host 172.21.6.12, port 5201
Reverse mode, remote host 172.21.6.12 is sending
[  5] local 12.1.1.24 port 40068 connected to 172.21.6.12 port 5201
[ ID] Interval           Transfer     Bitrate         Jitter    Lost/Total Datagrams
[  5]   0.00-1.00   sec  12.7 MBytes   107 Mbits/sec  0.153 ms  0/9355 (0%)  (omitted)
[  5]   1.00-2.00   sec  11.9 MBytes   100 Mbits/sec  0.107 ms  0/8761 (0%)  (omitted)
[  5]   2.00-3.00   sec  11.9 MBytes   100 Mbits/sec  0.136 ms  0/8760 (0%)  (omitted)
[  5]   3.00-4.00   sec  11.9 MBytes   100 Mbits/sec  0.134 ms  0/8760 (0%)  (omitted)
[  5]   4.00-5.00   sec  11.9 MBytes   100 Mbits/sec  0.133 ms  0/8759 (0%)  (omitted)
[  5]   0.00-1.00   sec  11.9 MBytes  99.6 Mbits/sec  0.120 ms  0/8725 (0%)  
[  5]   1.00-2.00   sec  12.0 MBytes   100 Mbits/sec  0.128 ms  0/8786 (0%)  
[  5]   2.00-3.00   sec  11.9 MBytes   100 Mbits/sec  0.125 ms  0/8759 (0%)  
[  5]   3.00-4.00   sec  11.9 MBytes  99.7 Mbits/sec  0.229 ms  0/8734 (0%)  
[  5]   4.00-5.00   sec  12.0 MBytes   100 Mbits/sec  0.090 ms  0/8794 (0%)  
[  5]   5.00-6.00   sec  11.9 MBytes   100 Mbits/sec  0.121 ms  0/8760 (0%)  
[  5]   6.00-7.00   sec  11.9 MBytes   100 Mbits/sec  0.116 ms  0/8760 (0%)  
[  5]   7.00-8.00   sec  11.9 MBytes   100 Mbits/sec  0.123 ms  0/8759 (0%)  
[  5]   8.00-9.00   sec  11.9 MBytes   100 Mbits/sec  0.123 ms  0/8760 (0%)  
[  5]   9.00-10.00  sec  11.9 MBytes   100 Mbits/sec  0.127 ms  0/8759 (0%)  
[  5]  10.00-11.00  sec  11.9 MBytes   100 Mbits/sec  0.111 ms  0/8760 (0%)  
[  5]  11.00-12.00  sec  11.9 MBytes   100 Mbits/sec  0.132 ms  0/8760 (0%)  
[  5]  12.00-13.00  sec  11.9 MBytes   100 Mbits/sec  0.130 ms  0/8759 (0%)  
[  5]  13.00-14.00  sec  11.9 MBytes   100 Mbits/sec  0.125 ms  0/8760 (0%)  
[  5]  14.00-15.00  sec  11.9 MBytes   100 Mbits/sec  0.122 ms  0/8760 (0%)  
[  5]  15.00-16.00  sec  11.9 MBytes   100 Mbits/sec  0.118 ms  0/8760 (0%)  
[  5]  16.00-17.00  sec  11.9 MBytes   100 Mbits/sec  0.137 ms  0/8759 (0%)  
[  5]  17.00-18.00  sec  11.9 MBytes   100 Mbits/sec  0.144 ms  0/8759 (0%)  
[  5]  18.00-19.00  sec  11.9 MBytes   100 Mbits/sec  0.135 ms  0/8761 (0%)  
[  5]  19.00-20.00  sec  11.9 MBytes   100 Mbits/sec  0.136 ms  0/8759 (0%)  
[  5]  20.00-21.00  sec  11.9 MBytes   100 Mbits/sec  0.142 ms  0/8759 (0%)  
[  5]  21.00-22.00  sec  11.9 MBytes   100 Mbits/sec  0.067 ms  0/8760 (0%)  
[  5]  22.00-23.00  sec  11.9 MBytes  99.9 Mbits/sec  0.145 ms  0/8751 (0%)  
[  5]  23.00-24.00  sec  11.9 MBytes  99.9 Mbits/sec  0.111 ms  0/8751 (0%)  
[  5]  24.00-25.00  sec  11.9 MBytes   100 Mbits/sec  0.142 ms  0/8777 (0%)  
[  5]  25.00-26.00  sec  11.9 MBytes  99.8 Mbits/sec  0.151 ms  0/8741 (0%)  
[  5]  26.00-27.00  sec  11.9 MBytes   100 Mbits/sec  0.136 ms  0/8779 (0%)  
[  5]  27.00-28.00  sec  11.9 MBytes   100 Mbits/sec  0.136 ms  0/8759 (0%)  
[  5]  28.00-29.00  sec  11.9 MBytes   100 Mbits/sec  0.132 ms  0/8760 (0%)  
[  5]  29.00-30.00  sec  11.9 MBytes  99.8 Mbits/sec  0.150 ms  0/8742 (0%)  
[  5]  30.00-31.00  sec  11.9 MBytes   100 Mbits/sec  0.134 ms  0/8777 (0%)  
[  5]  31.00-32.00  sec  11.9 MBytes   100 Mbits/sec  0.193 ms  0/8778 (0%)  
[  5]  32.00-33.00  sec  11.9 MBytes  99.8 Mbits/sec  0.136 ms  0/8741 (0%)  
[  5]  33.00-34.00  sec  11.9 MBytes  99.8 Mbits/sec  0.118 ms  0/8742 (0%)  
[  5]  34.00-35.00  sec  11.9 MBytes   100 Mbits/sec  0.063 ms  0/8778 (0%)  
[  5]  35.00-36.00  sec  11.9 MBytes   100 Mbits/sec  0.068 ms  0/8759 (0%)  
[  5]  36.00-37.00  sec  11.9 MBytes   100 Mbits/sec  0.137 ms  0/8760 (0%)  
[  5]  37.00-38.00  sec  11.9 MBytes   100 Mbits/sec  0.132 ms  0/8759 (0%)  
[  5]  38.00-39.00  sec  11.9 MBytes   100 Mbits/sec  0.190 ms  0/8778 (0%)  
[  5]  39.00-40.00  sec  11.9 MBytes  99.8 Mbits/sec  0.137 ms  0/8741 (0%)  
[  5]  40.00-41.00  sec  11.9 MBytes   100 Mbits/sec  0.081 ms  0/8760 (0%)  
[  5]  41.00-42.00  sec  11.9 MBytes   100 Mbits/sec  0.135 ms  0/8760 (0%)  
[  5]  42.00-43.00  sec  11.9 MBytes   100 Mbits/sec  0.128 ms  0/8760 (0%)  
[  5]  43.00-44.00  sec  11.9 MBytes   100 Mbits/sec  0.130 ms  0/8759 (0%)  
[  5]  44.00-45.00  sec  11.9 MBytes   100 Mbits/sec  0.135 ms  0/8760 (0%)  
[  5]  45.00-46.00  sec  11.9 MBytes   100 Mbits/sec  0.131 ms  0/8760 (0%)  
[  5]  46.00-47.00  sec  11.9 MBytes   100 Mbits/sec  0.125 ms  0/8759 (0%)  
[  5]  47.00-48.00  sec  11.9 MBytes   100 Mbits/sec  0.133 ms  0/8760 (0%)  
[  5]  48.00-49.00  sec  11.9 MBytes   100 Mbits/sec  0.124 ms  0/8759 (0%)  
[  5]  49.00-50.00  sec  11.9 MBytes   100 Mbits/sec  0.129 ms  0/8760 (0%)  
[  5]  50.00-51.00  sec  11.9 MBytes   100 Mbits/sec  0.138 ms  0/8759 (0%)  
[  5]  51.00-52.00  sec  11.9 MBytes   100 Mbits/sec  0.138 ms  0/8760 (0%)  
[  5]  52.00-53.00  sec  11.9 MBytes  99.9 Mbits/sec  0.102 ms  0/8751 (0%)  
[  5]  53.00-54.00  sec  11.9 MBytes   100 Mbits/sec  0.120 ms  0/8777 (0%)  
[  5]  54.00-55.00  sec  11.9 MBytes  99.9 Mbits/sec  0.131 ms  0/8752 (0%)  
[  5]  55.00-56.00  sec  11.9 MBytes  99.9 Mbits/sec  0.104 ms  0/8750 (0%)  
[  5]  56.00-57.00  sec  11.9 MBytes   100 Mbits/sec  0.070 ms  0/8768 (0%)  
[  5]  57.00-58.00  sec  11.9 MBytes   100 Mbits/sec  0.126 ms  0/8769 (0%)  
[  5]  58.00-59.00  sec  11.9 MBytes  99.9 Mbits/sec  0.135 ms  0/8751 (0%)  
[  5]  59.00-60.00  sec  11.9 MBytes   100 Mbits/sec  0.166 ms  0/8769 (0%)  
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Jitter    Lost/Total Datagrams
[  5]   0.00-60.10  sec   716 MBytes   100 Mbits/sec  0.000 ms  0/525815 (0%)  sender
[  5]   0.00-60.00  sec   715 MBytes   100 Mbits/sec  0.166 ms  0/525588 (0%)  receiver

iperf Done.
```


### RU
```bash
# Benetel RAN550, ORU_Benetel_550_c0, root/Bntl@2025
ssh root@10.10.0.109

Last login: Wed Sep  9 09:12:33 2026 from 10.0.0.140
 ____                  _       _ 
|  _ \                | |     | |
| |_) | ___ _ __   ___| |_ ___| |
|  _ < / _ \ '_ \ / _ \ __/ _ \ |
| |_) |  __/ | | |  __/ ||  __/ |
|____/ \___|_| |_|\___|\__\___|_|

       OpenRAN Radio Units.
      Opening Possibilities.

Use 'benetel-help' for a list of
useful commands.
root@ran550-n77-455:~# benetel-help
+-----------------------------------+-----------------------------------+
| Commands                          | Description                       |
+-----------------------------------+-----------------------------------+
| ifconfig eth0                     | Shows O-RU MAC address/IP         |
| benetel_set_ru_ip                 | Tool for setting permanent        |
|                                   | IP address to the RU              |
| cat /etc/benetel-rootfs-version   | Shows software version installed  |
| vi /etc/ru_config.cfg             | Edits O-RU config file            |
| frequencycontrol                  | Tool for dynamic (w/o reboot)     |
|                                   | centre frequency change           |
| set_bandwidth_dynamic.sh          | Tool for dynamic (w/o reboot)     |
|                                   | bandwidth change                  |
| set_mimo.sh                       | Tool for dynamic (w/o reboot)     |
|                                   | mimo mode change                  |
| set_compr_mode.sh                 | Tool for dynamic (w/o reboot)     |
|                                   | FH compression change             |
| swu_manager slot_info             | Display SW slot information       |
| vi /etc/eaxc.cfg                  | Edits eAxC ID config file         |
| setSyncModePtp                    | Sets sync mode to PTP             |
| setSyncModeGps                    | Sets sync mode to GPS/1PPS        |
| oru_dpd_reset                     | Resets DPD algorithm              |
| oru_fem_reset                     | Resets FEM                        |
| ptp_stack_reset.sh                | Enables to reset the PTP synch    |
+-----------------------------------+-----------------------------------+
| O-RU Config File parameters                                           |
| User can edit the /etc/ru_config.cfg file.                            |
| O-RU reboot is needed to activate new configuration.                  |
| Please refer User Guide document for complete list of paramters       |
+-----------------------------------+-----------------------------------+
| Parameter                         | Description                       |
+-----------------------------------+-----------------------------------+
| mimo_mode                         | Sets O-RU MIMO mode               |
| downlink_scaling                  | Sets O-RU FH scaling              |
| ul_gain_correction                | Sets O-RU FH UL gain correction   |
| prach_format                      | Sets O-RU short/Long Prach mode   |
| compression                       | Sets O-RU compression modes       |
| c_plane_du_mac                    | Sets O-DU c_plane mac address     |
| u_plane_du_mac                    | Sets O-DU u_plane mac address     |
| c_plane_du_vlan                   | Sets O-DU c_plane Vlan tag        |
| u_plane_du_vlan_uplink            | Sets O-DU u_plane ul Vlan tag     |
| u_plane_du_vlan_downlink          | Sets O-DU u_plane dl Vlantag      |
| tx_power_dbm                      | Sets O-RU output power            |
| centre_frequency_hz               | Sets O-RU center frequency        |
| bandwidth_hz                      | Sets O-RU bandwidth               |
| tdd_pattern_1, tdd_pattern_2      | Sets O-RU TDD configuration       |
|    and special_slots_symbols[1/2] |                                   |
| m_plane_u_plane_config_v16        | Configure M-Plane array carriers  |
|                                   | activation behavior to align      |
|                                   | with v16.01 specification         |
| synce_enable                      | Enables/Disables SyncE for PTP    |
+-----------------------------------+-----------------------------------+
| O-RU Status/Statistics            | Description                       |
+-----------------------------------+-----------------------------------+
| benetel-help                      | Shows this help menu              |
| cat /tmp/logs/ru_information      | Shows O-RU product information    |
| cat /var/syncmon/sync-state       | Shows sync status (0 - locked,    |
|                                   |   1 - Holdover, 2 - Freerun)      |
| tail -F /var/log/pcm4l            | Shows PTP logs                    |
| cat /etc/ru-sync-mode             | Shows current sync mode           |
| cat /tmp/logs/radio_status        | Shows radio bringup log           |
| oru_status                        | Shows current radio status        |
| oru_dpd_stats                     | Shows DPD status                  |
| kpi.sh                            | Shows Key Performance Indicators  |
| RXMeanPower                       | Shows current O-RU mean RX power  |
| TXMeanPower                       | Shows current O-RU mean TX power  |
| reportRuStatus                    | Shows CSR status for debug        |
| oru_vlan_mac_info                 | Shows DU VLAN and MAC settings    |
+-----------------------------------+-----------------------------------+
| O-RU Logging                      | Description                       |
+-----------------------------------+-----------------------------------+
| /etc/benetel_capture_RU_logs.sh   | Captures O-RU debug logs directly |
|                                   | on RU into /tmp directory         |
|                                   | Copy the script to O-DU and run it|
|                                   | to get the logs from O-RU to O-DU |
|                                   | Refer to User's guide for details |
+-----------------------------------+-----------------------------------+
```


### FlexRIC
```bash
git clone git@gitlab.eurecom.fr:mosaic5g/flexric.git

sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt update
sudo apt install -y gcc-13 g++-13 cpp-13
sudo update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-13 100 --slave /usr/bin/g++ g++ /usr/bin/g++-13 --slave /usr/bin/gcov gcov /usr/bin/gcov-13
sudo update-alternatives --config gcc # chose gcc-13

sudo apt install libsctp-dev cmake-curses-gui libpcre2-dev

cd $TEST_DIR/flexric
mkdir build && cd build && cmake -DE2AP_VERSION=E2AP_V2 -DKPM_VERSION=KPM_V2_03 .. && make -j8
sudo make install

./build/examples/ric/nearRT-RIC

XAPP_DURATION=20000 ./build/examples/xApp/c/monitor/xapp_kpm_moni

# save logs
XAPP_DURATION=20000 ./build/examples/xApp/c/monitor/xapp_kpm_moni 2>&1 | tee ~/xapp_run_$(date -u +%Y%m%d_%H%M%S).log

# stop hanging process when core dumb
pgrep -af nearRT-RIC
kill -INT <pid>
```