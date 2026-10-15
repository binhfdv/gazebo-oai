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
    && apt-get update

# Matches the package set already validated in binh/gazebo/installation_steps.md
RUN apt-get install -y --no-install-recommends \
        ros-noetic-desktop \
        ros-noetic-gazebo-ros-pkgs \
        ros-noetic-gazebo-ros-control \
        ros-noetic-teleop-twist-keyboard \
        ros-noetic-tf \
        ros-noetic-tf2-tools \
        ros-noetic-rqt-graph \
        ros-noetic-rviz \
        ros-noetic-jackal-simulator \
        ros-noetic-jackal-desktop \
        ros-noetic-jackal-navigation \
        python3-rosdep \
        python3-catkin-tools \
        python3-catkin-pkg \
        python3-osrf-pycommon \
        python3-pip \
        build-essential \
        git \
        iproute2 \
        iputils-ping \
    && rm -rf /var/lib/apt/lists/*

RUN rosdep init || true && rosdep update

COPY spawn_robots.py /usr/local/bin/spawn_robots.py
COPY cmd_bridge.py /usr/local/bin/cmd_bridge.py
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh /usr/local/bin/spawn_robots.py /usr/local/bin/cmd_bridge.py

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
