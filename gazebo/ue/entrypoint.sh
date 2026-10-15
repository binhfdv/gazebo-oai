#!/bin/bash
set -ex

source /opt/ros/noetic/setup.bash

UE_IFACE="${UE_IFACE:-wwan0}"
EDGE_IP="${EDGE_IP:-192.168.80.135}"
EDGE_PORT="${EDGE_PORT:-11311}"
UE_MTU="${UE_MTU:-1400}"
UE_NAMESPACE="${UE_NAMESPACE:-}"

# Namespaces this UE's whole ROS graph (nodes launched by roslaunch below,
# e.g. robot_state_publisher/controller_manager/ekf_localization) so
# multiple UEs can share one roscore without their topics/services
# colliding. spawn_robots.py and cmd_bridge.py read UE_NAMESPACE directly
# themselves for the Gazebo core service calls (see NOTE in those files -
# whether gazebo_ros's own plugin-advertised services actually respect
# ROS_NAMESPACE is unverified; check `rosservice list | grep gazebo` after
# deploying to confirm before relying on this for more than one UE).
if [ -n "$UE_NAMESPACE" ]; then
    export ROS_NAMESPACE="$UE_NAMESPACE"
    echo "[entrypoint] ROS_NAMESPACE=$ROS_NAMESPACE"
fi

echo "[entrypoint] Waiting for interface $UE_IFACE to have an IPv4 address..."
UE_IP=""
while [ -z "$UE_IP" ]; do
    UE_IP=$(ip -4 addr show "$UE_IFACE" 2>/dev/null | awk '/inet / {print $2}' | cut -d/ -f1)
    [ -z "$UE_IP" ] && sleep 2
done
echo "[entrypoint] UE_IP=$UE_IP on $UE_IFACE"

# There's a PMTU blackhole somewhere in the GTP tunnel path: packets near
# the standard 1500-byte MTU vanish silently (confirmed via `ping -M do`),
# while small ones pass fine. Without this, large ROS XML-RPC payloads
# (e.g. the robot_description parameter) stall for minutes on TCP
# retransmission timeouts instead of just failing cleanly. Needs
# cap_add: NET_ADMIN in docker-compose.yml, since network_mode: host
# alone doesn't grant permission to change interface settings.
# NOTE: no sudo here - the container already runs as root, and root with
# CAP_NET_ADMIN (via cap_add in docker-compose.yml) is sufficient; sudo
# isn't installed in the image at all, so prefixing with it would just
# fail with "command not found" (silently, since it's OR'd with a warning).
# Must run after the IP-wait loop above: $UE_IFACE may not exist yet at
# container start (it's created when the 5G PDU session comes up), and
# `ip link set` on a nonexistent device fails silently with no retry -
# which reopens this exact blackhole for the whole session.
echo "[entrypoint] Setting MTU $UE_MTU on $UE_IFACE (works around a PMTU blackhole on this link)..."
until ip link set "$UE_IFACE" mtu "$UE_MTU" 2>/dev/null; do
    echo "[entrypoint] WARNING: could not set MTU on $UE_IFACE yet, retrying..."
    sleep 2
done
echo "[entrypoint] MTU set."

export ROS_IP="$UE_IP"
export ROS_MASTER_URI="http://${EDGE_IP}:${EDGE_PORT}"
echo "[entrypoint] ROS_MASTER_URI=$ROS_MASTER_URI  ROS_IP=$ROS_IP"

echo "[entrypoint] Waiting for ROS master to be reachable..."
until rostopic list >/dev/null 2>&1; do
    sleep 2
done
echo "[entrypoint] ROS master reachable."

echo "[entrypoint] Launching Jackal Gazebo world (headless)..."

roslaunch jackal_gazebo jackal_world.launch gui:=false --screen &
GAZEBO_PID=$!

echo "[entrypoint] Waiting for Gazebo spawn service..."
until rosservice list 2>/dev/null | grep -q "/gazebo/spawn_urdf_model"; do
    sleep 2
done
echo "[entrypoint] Gazebo ready."

echo "[entrypoint] Computing robot placement and spawning..."
python3 /usr/local/bin/spawn_robots.py

echo "[entrypoint] Starting cmd_vel bridge..."
python3 /usr/local/bin/cmd_bridge.py &
BRIDGE_PID=$!

wait "$GAZEBO_PID" "$BRIDGE_PID"
