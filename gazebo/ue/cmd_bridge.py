#!/usr/bin/env python3
"""
Generalized version of the five_jackal_cmd_bridge.py from
binh/gazebo/installation_steps.md - reads the robot layout written by
spawn_robots.py instead of hardcoding robot count/names, so it works for
however many robots were actually spawned.

Subscribes to /robotN/cmd_vel for each robot in the layout and drives the
corresponding Gazebo model via /gazebo/set_model_state (simple unicycle
integration), same approach as the original script.
"""
import json
import math
import os
import subprocess
import time

import rospy
from geometry_msgs.msg import Twist
from gazebo_msgs.msg import ModelState
from gazebo_msgs.srv import SetModelState, GetModelState
from tf.transformations import quaternion_from_euler

LAYOUT_FILE = "/tmp/robots_layout.json"

# Must match spawn_robots.py's namespacing - see resolve_ns() below, which
# confirms this against the live system instead of assuming it.
UE_NAMESPACE = os.environ.get("UE_NAMESPACE", "").strip()
NS = f"/{UE_NAMESPACE}" if UE_NAMESPACE else ""


def resolve_ns(timeout=15.0, interval=1.0):
    """Same check as spawn_robots.py's resolve_ns() - confirm gazebo_ros
    actually advertises its services under NS before relying on it, falling
    back to the plain global name otherwise."""
    if not UE_NAMESPACE:
        return ""
    deadline = time.monotonic() + timeout
    target = f"{NS}/gazebo/set_model_state"
    while time.monotonic() < deadline:
        result = subprocess.run(["rosservice", "list"], capture_output=True,
                                 text=True, check=False)
        if target in result.stdout.splitlines():
            rospy.loginfo("gazebo services are namespaced under %s - using that.", NS)
            return NS
        time.sleep(interval)
    rospy.logwarn("%s never showed up in `rosservice list` after %ss - "
                  "falling back to the plain /gazebo/... names.", target, timeout)
    return ""


def wait_for_models(model_names, get_model_state, timeout=90.0, interval=1.0):
    """Block until every model in model_names is reported as existing by
    gazebo, instead of letting the 20Hz set_model_state loop below hammer
    it with "model does not exist" on every tick until it shows up."""
    pending = set(model_names)
    deadline = time.monotonic() + timeout
    while pending and time.monotonic() < deadline:
        for name in list(pending):
            try:
                resp = get_model_state(model_name=name)
            except rospy.ServiceException:
                continue
            if resp.success:
                rospy.loginfo("Model %s is up in Gazebo.", name)
                pending.discard(name)
        if pending:
            time.sleep(interval)
    if pending:
        rospy.logwarn("Still waiting on models after %ss: %s - starting "
                      "the control loop anyway.", timeout, sorted(pending))


class RobotState:
    def __init__(self, model_name, x, y, z):
        self.model_name = model_name
        self.x = x
        self.y = y
        self.z = z
        self.v = 0.0
        self.w = 0.0
        self.last_cmd_time = rospy.Time.now()

    def cmd_cb(self, msg):
        self.v = msg.linear.x
        self.w = msg.angular.z
        self.last_cmd_time = rospy.Time.now()


def main():
    global NS
    rospy.init_node("gazebo_cmd_bridge")
    NS = resolve_ns()

    with open(LAYOUT_FILE) as f:
        layout = json.load(f)

    robots = {}
    for entry in layout:
        robots[entry["robot_topic"]] = RobotState(
            entry["model_name"], entry["x"], entry["y"], entry["z"]
        )

    for robot_name, state in robots.items():
        topic = f"{NS}/{robot_name}/cmd_vel"
        rospy.Subscriber(topic, Twist, state.cmd_cb)
        rospy.loginfo("Subscribed to %s -> model %s", topic, state.model_name)

    gazebo_set_state_srv = f"{NS}/gazebo/set_model_state"
    gazebo_get_state_srv = f"{NS}/gazebo/get_model_state"
    rospy.wait_for_service(gazebo_set_state_srv)
    rospy.wait_for_service(gazebo_get_state_srv)
    set_state = rospy.ServiceProxy(gazebo_set_state_srv, SetModelState)
    get_state = rospy.ServiceProxy(gazebo_get_state_srv, GetModelState)

    wait_for_models([r.model_name for r in robots.values()], get_state)

    rate_hz = 20.0
    dt = 1.0 / rate_hz
    rate = rospy.Rate(rate_hz)
    cmd_timeout = rospy.Duration(0.5)

    while not rospy.is_shutdown():
        now = rospy.Time.now()

        for robot_name, r in robots.items():
            if now - r.last_cmd_time > cmd_timeout:
                v, w = 0.0, 0.0
            else:
                v, w = r.v, r.w

            r.x += v * math.cos(r.z) * dt
            r.y += v * math.sin(r.z) * dt
            r.z += w * dt

            q = quaternion_from_euler(0.0, 0.0, r.z)

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
