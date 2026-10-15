FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=noetic

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        gnupg2 \
        lsb-release \
        ca-certificates \
        software-properties-common \
    && add-apt-repository universe \
    && apt-get update \
    && mkdir -p /usr/share/keyrings \
    && curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc \
        | gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros/ubuntu focal main" \
        > /etc/apt/sources.list.d/ros1-latest.list \
    && apt-get update \
    # ros-base + gazebo-msgs only (message/service definitions) - NOT
    # gazebo-ros-pkgs, which would pull in the full Gazebo simulator
    # binary that never actually runs on the edge side, only roscore +
    # rostopic/rosbag do.
    && apt-get install -y --no-install-recommends \
        ros-noetic-ros-base \
        ros-noetic-teleop-twist-keyboard \
        ros-noetic-gazebo-msgs \
        iproute2 \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
