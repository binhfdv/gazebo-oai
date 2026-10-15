#!/bin/bash
set -ex

source /opt/ros/noetic/setup.bash

# Runs with network_mode: "container:duong-oai-ext-dn" in the core
# compose file, so this container's eth0 IS ext-dn's already-working
# interface (static IP 192.168.80.135, already routable from the UE).
EDGE_IFACE="${EDGE_IFACE:-eth0}"
EDGE_IP="${EDGE_IP:-}"

if [ -z "$EDGE_IP" ]; then
    EDGE_IP=$(ip -4 addr show "$EDGE_IFACE" 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1)
fi

export ROS_IP="$EDGE_IP"
export ROS_MASTER_URI="http://${EDGE_IP}:11311"

echo "[entrypoint] ROS_IP=$ROS_IP  ROS_MASTER_URI=$ROS_MASTER_URI"
echo "[entrypoint] Starting roscore..."
echo "[entrypoint] For interactive rostopic/rosbag commands, in another shell run:"
echo "[entrypoint]   docker exec -it <container_name> bash -lc 'source /opt/ros/noetic/setup.bash; export ROS_MASTER_URI=$ROS_MASTER_URI; export ROS_IP=$ROS_IP; bash'"

exec roscore

# docker exec duong-ros-controller ps aux | grep -i -E "rosmaster|rosout" # to see the roscore process correctly
