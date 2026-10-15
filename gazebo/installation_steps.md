export UE_IFACE=oaitun_ue1
export UE_IP=$(ip -4 addr show $UE_IFACE | awk '/inet / {print $2}' | cut -d/ -f1)
export EDGE_IP=10.1.2.14

# at UE
root@oai-nr-ue-1-bc9f894db-82v57:~# iperf3 -c  $EDGE_IP -B $UE_IP
Connecting to host 10.1.2.14, port 5201
[  5] local 12.1.1.100 port 49293 connected to 10.1.2.14 port 5201
[ ID] Interval           Transfer     Bitrate         Retr  Cwnd
[  5]   0.00-1.00   sec   895 KBytes  7.33 Mbits/sec    0   80.6 KBytes       
[  5]   1.00-2.00   sec  1.12 MBytes  9.38 Mbits/sec    0    132 KBytes       
[  5]   2.00-3.00   sec  2.11 MBytes  17.7 Mbits/sec    0    212 KBytes       
[  5]   3.00-4.00   sec  2.86 MBytes  24.0 Mbits/sec    0    332 KBytes       
[  5]   4.00-5.00   sec  3.11 MBytes  26.1 Mbits/sec    0    461 KBytes       
[  5]   5.00-6.00   sec  3.17 MBytes  26.6 Mbits/sec    0    590 KBytes       
[  5]   6.00-7.00   sec  2.49 MBytes  20.9 Mbits/sec    0    718 KBytes       
[  5]   7.00-8.00   sec  2.50 MBytes  21.0 Mbits/sec    0    847 KBytes       
[  5]   8.00-9.00   sec  2.50 MBytes  21.0 Mbits/sec    0    976 KBytes       
[  5]   9.00-10.00  sec  2.50 MBytes  21.0 Mbits/sec    0   1.08 MBytes       
- - - - - - - - - - - - - - - - - - - - - - - - -
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec  23.2 MBytes  19.5 Mbits/sec    0             sender
[  5]   0.00-10.43  sec  21.5 MBytes  17.3 Mbits/sec                  receiver

iperf Done.


RobotQoS

At UE server:

ROS:
sudo apt update
sudo apt install -y curl gnupg2 lsb-release ca-certificates software-properties-common
sudo add-apt-repository universe
sudo apt update

sudo mkdir -p /usr/share/keyrings

curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc \
  | sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros/ubuntu focal main" \
  | sudo tee /etc/apt/sources.list.d/ros1-latest.list
sudo apt update

apt-cache policy ros-noetic-ros-base
apt-cache search ros-noetic-gazebo-ros-pkgs | head

sudo apt install -y \
  ros-noetic-desktop \
  ros-noetic-gazebo-ros-pkgs \
  ros-noetic-gazebo-ros-control \
  ros-noetic-teleop-twist-keyboard \
  ros-noetic-tf \
  ros-noetic-tf2-tools \
  ros-noetic-rqt-graph \
  ros-noetic-rviz \
  python3-rosdep \
  python3-catkin-tools \
  python3-catkin-pkg \
  python3-osrf-pycommon \
  build-essential \
  git

sudo rosdep init 2>/dev/null || true
rosdep update

echo "source /opt/ros/noetic/setup.bash" >> ~/.bashrc
source /opt/ros/noetic/setup.bash

which roscore
which rostopic
which roslaunch
rosversion -d #expect noetic

Jackal simulation
sudo apt install -y \
  ros-noetic-jackal-simulator \
  ros-noetic-jackal-desktop \
  ros-noetic-jackal-navigation

roscd jackal_gazebo
roslaunch jackal_gazebo jackal_world.launch --ros-args
#If --ros-args gives an error, ignore it. Older ROS 1 launch files do not support that option. The important check is whether roscd jackal_gazebo works.

node-7 filesystem:
  ROS/Gazebo binaries installed here

UE pod network namespace:
  12.1.1.100 UE PDU IP lives here

Run Gazebo from node-7 but inside UE pod netns:
  nsenter -t <UE_POD_PID> -n -- roslaunch ...

ROS_IP=12.1.1.100


CID=$(sudo crictl ps | grep oai-nr-ue | awk '{print $1}' | head -1)
echo $CID
sudo apt install -y jq
PID=$(sudo crictl inspect $CID | jq -r '.info.pid')
echo $PID
sudo nsenter -t $PID -n -- ip -br addr


DN:
EDGE_IP=10.1.2.14
sudo apt update
sudo apt install -y curl gnupg2 lsb-release ca-certificates software-properties-common
sudo add-apt-repository universe
sudo mkdir -p /usr/share/keyrings

curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.asc \
  | sudo gpg --dearmor -o /usr/share/keyrings/ros-archive-keyring.gpg

echo "deb [signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros/ubuntu focal main" \
  | sudo tee /etc/apt/sources.list.d/ros1-latest.list

sudo apt update
sudo apt install -y ros-noetic-ros-base ros-noetic-teleop-twist-keyboard

sudo apt update
sudo apt install -y \
  ros-noetic-gazebo-msgs \
  ros-noetic-gazebo-ros-pkgs

source /opt/ros/noetic/setup.bash
rosmsg show gazebo_msgs/ModelStates

source /opt/ros/noetic/setup.bash

source /opt/ros/noetic/setup.bash

export EDGE_K8S_NS=oai
export EDGE_POD=oai-traffic-server-566fd99f9b-dj55g
export EDGE_IP=10.1.1.14

sudo tee /etc/crictl.yaml >/dev/null <<EOF
runtime-endpoint: unix:///var/run/cri-dockerd.sock
image-endpoint: unix:///var/run/cri-dockerd.sock
timeout: 10
debug: false
EOF

EDGE_CID=$(sudo docker ps \
  --filter "label=io.kubernetes.pod.namespace=$EDGE_K8S_NS" \
  --filter "label=io.kubernetes.pod.name=$EDGE_POD" \
  --filter "label=io.kubernetes.container.name=POD" \
  -q | head -1)

echo $EDGE_CID

EDGE_PID=$(sudo docker inspect -f '{{.State.Pid}}' $EDGE_CID)
echo $EDGE_PID

sudo nsenter -t $EDGE_PID -n -- ip -br addr

Test connection:On node-8:
bash


export EDGE_IP=10.1.2.14
export UE_IP=12.1.1.100

sudo nsenter -t $EDGE_PID -n -- ping -c 3 $UE_IP

#If ping works, start roscore:
sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14
echo ROS_MASTER_URI=$ROS_MASTER_URI
echo ROS_IP=$ROS_IP
roscore
'

On node-7, assuming your UE PID is still $PID:

export UE_PID=$PID
export EDGE_IP=10.1.2.14
export UE_IP=12.1.1.100

sudo nsenter -t $UE_PID -n -- ip route replace 10.1.2.14/32 dev oaitun_ue1 src 12.1.1.100

sudo nsenter -t $UE_PID -n -- iperf3 -c $EDGE_IP -B $UE_IP -t 5

sudo nsenter -t $UE_PID -n -- python3 - <<'PY'
import socket
s=socket.socket()
s.settimeout(5)
try:
    s.connect(("10.1.2.14",11311))
    print("OK: UE namespace can reach ROS master TCP/11311")
except Exception as e:
    print("FAIL:", e)
finally:
    s.close()
PY


sudo -E nsenter -t $UE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=12.1.1.100
echo ROS_MASTER_URI=$ROS_MASTER_URI
echo ROS_IP=$ROS_IP
rostopic list
'

Then test ROS topic UE → Edge

Node-7 / UE side
sudo -E nsenter -t $UE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=12.1.1.100
rostopic pub -r 1 /hello_5g std_msgs/String "data: hello_from_ue_over_oai"
'

Node-8 / Edge side
sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14
rostopic echo /hello_5g
'


After ROS works, launch Gazebo
UE
sudo -E nsenter -t $UE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
source /home/ubuntu/jackal_ws/devel/setup.bash 2>/dev/null || true

export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=12.1.1.100

roslaunch jackal_gazebo jackal_world.launch gui:=false
'

DN
sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

rostopic pub -r 10 /cmd_vel geometry_msgs/Twist "
linear:
  x: 0.4
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.4"
'

In another edge terminal, check odometry
sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

rostopic echo /jackal_velocity_controller/odom
'
If it works, you should see changing values 


Test traffic at UE: sudo nsenter -t $UE_PID -n -- tcpdump -i oaitun_ue1 -nn host 10.1.2.14



####### 5 Jackal ####

1. Start ROS master on edge
On node-8:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14
roscore
'

2. Start Gazebo Jackal world on UE side
On node-7, start your existing Jackal Gazebo world:

sudo -E nsenter -t $UE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
source /home/ubuntu/jackal_ws/devel/setup.bash 2>/dev/null || true

export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=12.1.1.100

roslaunch jackal_gazebo jackal_world.launch gui:=false
'

3. Spawn 4 extra Jackals into the same Gazebo world
Open a new terminal on node-7.
Run:
sudo -E nsenter -t $UE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
source /home/ubuntu/jackal_ws/devel/setup.bash 2>/dev/null || true

export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=12.1.1.100

# Clean old extra models if they exist
rosservice call /gazebo/delete_model "model_name: jackal_2" 2>/dev/null || true
rosservice call /gazebo/delete_model "model_name: jackal_3" 2>/dev/null || true
rosservice call /gazebo/delete_model "model_name: jackal_4" 2>/dev/null || true
rosservice call /gazebo/delete_model "model_name: jackal_5" 2>/dev/null || true

# Spawn extra Jackals using the robot_description already loaded by jackal_world.launch
rosrun gazebo_ros spawn_model -urdf -model jackal_2 -param robot_description -x 2.0  -y 0.0  -z 0.2
rosrun gazebo_ros spawn_model -urdf -model jackal_3 -param robot_description -x 0.0  -y 2.0  -z 0.2
rosrun gazebo_ros spawn_model -urdf -model jackal_4 -param robot_description -x -2.0 -y 0.0  -z 0.2
rosrun gazebo_ros spawn_model -urdf -model jackal_5 -param robot_description -x 0.0  -y -2.0 -z 0.2
'

Now check from edge:

sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

rostopic echo -n 1 /gazebo/model_states
'
You should see:
jackal
jackal_2
jackal_3
jackal_4
jackal_5

4. Create a simple 5-robot command bridge on UE side
This bridge subscribes to:
text


/robot1/cmd_vel
/robot2/cmd_vel
/robot3/cmd_vel
/robot4/cmd_vel
/robot5/cmd_vel
and moves the Gazebo models.
On node-7 host, create the script:
bash


mkdir -p ~/swarm_test
nano ~/swarm_test/five_jackal_cmd_bridge.py
Paste this:
python


#!/usr/bin/env python3

import math
import rospy
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import SetModelState
from tf.transformations import quaternion_from_euler

class RobotState:
    def __init__(self, model_name, x, y, yaw):
        self.model_name = model_name
        self.x = x
        self.y = y
        self.yaw = yaw
        self.v = 0.0
        self.w = 0.0
        self.last_cmd_time = rospy.Time.now()

    def cmd_cb(self, msg):
        self.v = msg.linear.x
        self.w = msg.angular.z
        self.last_cmd_time = rospy.Time.now()

def main():
    rospy.init_node("five_jackal_cmd_bridge")

    robots = {
        "robot1": RobotState("jackal",   0.0,  0.0, 0.0),
        "robot2": RobotState("jackal_2", 2.0,  0.0, 0.0),
        "robot3": RobotState("jackal_3", 0.0,  2.0, 0.0),
        "robot4": RobotState("jackal_4", -2.0, 0.0, 0.0),
        "robot5": RobotState("jackal_5", 0.0, -2.0, 0.0),
    }

    for robot_name, state in robots.items():
        topic = "/" + robot_name + "/cmd_vel"
        rospy.Subscriber(topic, Twist, state.cmd_cb)
        rospy.loginfo("Subscribed to %s -> model %s", topic, state.model_name)

    rospy.wait_for_service("/gazebo/set_model_state")
    set_state = rospy.ServiceProxy("/gazebo/set_model_state", SetModelState)

    rate_hz = 20.0
    dt = 1.0 / rate_hz
    rate = rospy.Rate(rate_hz)

    cmd_timeout = rospy.Duration(0.5)

    while not rospy.is_shutdown():
        now = rospy.Time.now()

        for robot_name, r in robots.items():
            # Stop robot if command is old
            if now - r.last_cmd_time > cmd_timeout:
                v = 0.0
                w = 0.0
            else:
                v = r.v
                w = r.w

            # Simple unicycle integration
            r.x += v * math.cos(r.yaw) * dt
            r.y += v * math.sin(r.yaw) * dt
            r.yaw += w * dt

            q = quaternion_from_euler(0.0, 0.0, r.yaw)

            msg = ModelState()
            msg.model_name = r.model_name
            msg.pose.position.x = r.x
            msg.pose.position.y = r.y
            msg.pose.position.z = 0.12
            msg.pose.orientation.x = q[0]
            msg.pose.orientation.y = q[1]
            msg.pose.orientation.z = q[2]
            msg.pose.orientation.w = q[3]

            msg.twist.linear.x = v
            msg.twist.angular.z = w
            msg.reference_frame = "world"

            try:
                set_state(msg)
            except rospy.ServiceException as e:
                rospy.logwarn_throttle(2.0, "Failed to move %s: %s", r.model_name, str(e))

        rate.sleep()

if __name__ == "__main__":
    main()
Save and make executable:

chmod +x ~/swarm_test/five_jackal_cmd_bridge.py

5. Run the bridge inside the UE namespace
On node-7:
bash


sudo -E nsenter -t $UE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
source /home/ubuntu/jackal_ws/devel/setup.bash 2>/dev/null || true

export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=12.1.1.100

python3 /home/ubuntu/binh/swarm_test/five_jackal_cmd_bridge.py
'
Keep it running.
From edge, check topics:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

rostopic list | grep cmd_vel
'
You should see:
text


/robot1/cmd_vel
/robot2/cmd_vel
/robot3/cmd_vel
/robot4/cmd_vel
/robot5/cmd_vel

6. Control the 5 robots from edge
Move robot 1
On node-8:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

rostopic pub -r 10 /robot1/cmd_vel geometry_msgs/Twist "
linear:
  x: 0.5
  y: 0.0
  z: 0.0
angular:
  x: 0.0
  y: 0.0
  z: 0.4"
'
You should see the first Jackal move in Gazebo.
Stop with Ctrl-C.

Move all 5 robots with different commands
Open separate edge terminals, or run this from node-8:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

rostopic pub -r 10 /robot1/cmd_vel geometry_msgs/Twist "{linear: {x: 0.5}, angular: {z: 0.2}}" &
rostopic pub -r 10 /robot2/cmd_vel geometry_msgs/Twist "{linear: {x: 0.4}, angular: {z: -0.3}}" &
rostopic pub -r 10 /robot3/cmd_vel geometry_msgs/Twist "{linear: {x: 0.3}, angular: {z: 0.5}}" &
rostopic pub -r 10 /robot4/cmd_vel geometry_msgs/Twist "{linear: {x: 0.2}, angular: {z: -0.5}}" &
rostopic pub -r 10 /robot5/cmd_vel geometry_msgs/Twist "{linear: {x: 0.6}, angular: {z: 0.0}}" &

wait
'
To stop, press:
text


Ctrl-C
Then send zeros:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

for i in 1 2 3 4 5; do
  rostopic pub -1 /robot${i}/cmd_vel geometry_msgs/Twist "{linear: {x: 0.0}, angular: {z: 0.0}}"
done
'

7. Verify positions from edge
On node-8:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

rostopic echo /gazebo/model_states
'
Or use this cleaner Python watcher:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

python3 - << "PY"
import rospy
from gazebo_msgs.msg import ModelStates

wanted = ["jackal", "jackal_2", "jackal_3", "jackal_4", "jackal_5"]

def cb(msg):
    line = []
    for name in wanted:
        if name in msg.name:
            i = msg.name.index(name)
            p = msg.pose[i].position
            line.append("%s:(%.2f,%.2f)" % (name, p.x, p.y))
    print(" | ".join(line))

rospy.init_node("watch_five_jackals", anonymous=True)
rospy.Subscriber("/gazebo/model_states", ModelStates, cb)
rospy.spin()
PY
'

8. Confirm all traffic uses the UE tunnel
On node-7:
bash


sudo nsenter -t $UE_PID -n -- tcpdump -i oaitun_ue1 -nn host 10.1.2.14
Then publish robot commands from edge.
You should see traffic between:
text


10.1.2.14 <-> 12.1.1.100
That confirms:
text


edge ROS control
  -> OAI/O-RAN/5G user plane
  -> UE oaitun_ue1
  -> Gazebo 5-Jackal simulation

9. Record a small dataset
From edge, record robot commands and Gazebo ground truth:
bash


sudo -E nsenter -t $EDGE_PID -n -- bash -lc '
source /opt/ros/noetic/setup.bash
export ROS_MASTER_URI=http://10.1.2.14:11311
export ROS_IP=10.1.2.14

mkdir -p /home/ubuntu/swarm_bags

rosbag record -O /home/ubuntu/binh/swarm_bags/five_jackals_one_ue.bag \
  /clock \
  /gazebo/model_states \
  /robot1/cmd_vel \
  /robot2/cmd_vel \
  /robot3/cmd_vel \
  /robot4/cmd_vel \
  /robot5/cmd_vel
'
This creates your first simple dataset:
text


5 simulated Jackal models
1 UE path
edge-originated control commands
Gazebo ground-truth model states

10. Important note
This first version is intentionally simple.
It gives you:
text

[OK] one UE namespace
[OK] five Jackals visible in Gazebo
[OK] edge controls each robot with ROS topics
[OK] all traffic crosses one UE PDU session
But it does not yet give each robot its own full Jackal controller stack, odometry stack, TF tree, and sensor namespace. That is the next step.
After this works, the next cleaner version is:
text

/robot1/jackal_velocity_controller/cmd_vel
/robot2/jackal_velocity_controller/cmd_vel
...
/robot1/odom
/robot2/odom
...
