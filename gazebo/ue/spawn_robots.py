#!/usr/bin/env python3
"""
Compute robot spawn positions and spawn/relocate the Jackal models in
Gazebo accordingly.

Placement rule (agreed in planning):
  - No positions given (ROBOT_POSITIONS unset/empty): full circle of
    NUM_ROBOTS robots around the origin, radius=CIRCLE_RADIUS.
  - 0 < len(given) < NUM_ROBOTS: keep the given positions exactly as
    specified, auto-fill the remaining robots on a small circle
    (radius=AUTO_FILL_RADIUS) around the centroid of the given
    positions, nudging the radius out if an auto-filled spot would
    land too close to an existing one.
  - len(given) >= NUM_ROBOTS: use the first NUM_ROBOTS given positions
    directly, no auto-fill needed.

Env vars:
  NUM_ROBOTS       - total robot count (default 1)
  ROBOT_POSITIONS  - optional JSON list of {"x":.., "y":.., "z":..}
                      (z optional, defaults to 0.0)
  CIRCLE_RADIUS    - radius (m) for the default full-circle placement
                      (default 2.0)
  AUTO_FILL_RADIUS - starting radius (m) around the centroid of given
                      positions for auto-filled robots (default 1.5)
"""
import json
import math
import os
import subprocess
import time

LAYOUT_FILE = "/tmp/robots_layout.json"
MIN_SPACING = 0.6  # metres - minimum distance kept between any two robots

NUM_ROBOTS = int(os.environ.get("NUM_ROBOTS", "1"))
CIRCLE_RADIUS = float(os.environ.get("CIRCLE_RADIUS", "2.0"))
AUTO_FILL_RADIUS = float(os.environ.get("AUTO_FILL_RADIUS", "1.5"))

# Lets multiple UEs share one roscore without colliding on Gazebo's core
# service names - IF gazebo_ros's own plugin-advertised services actually
# honor this namespace prefix rather than hardcoding absolute names
# internally. resolve_ns() below checks which is actually true at runtime
# instead of assuming, and falls back to the plain name if the namespaced
# one was never registered.
UE_NAMESPACE = os.environ.get("UE_NAMESPACE", "").strip()
NS = f"/{UE_NAMESPACE}" if UE_NAMESPACE else ""


def resolve_ns(timeout=15.0, interval=1.0):
    """Confirm NS against the live `rosservice list` instead of assuming.

    gazebo_ros_api_plugin may or may not register its services under the
    namespace this process's ROS_NAMESPACE implies - that's been an open
    question since namespacing was added. If the namespaced service never
    shows up within `timeout`, fall back to the plain global name so a
    single-UE deployment still works even if multi-UE namespacing turns
    out not to be supported by the plugin.
    """
    if not UE_NAMESPACE:
        return ""
    deadline = time.monotonic() + timeout
    target = f"{NS}/gazebo/set_model_state"
    while time.monotonic() < deadline:
        result = subprocess.run(["rosservice", "list"], capture_output=True,
                                 text=True, check=False)
        services = result.stdout.splitlines()
        if target in services:
            print(f"[spawn_robots] gazebo services are namespaced under "
                  f"{NS} - using that.")
            return NS
        time.sleep(interval)
    print(f"[spawn_robots] WARNING: {target} never showed up in "
          f"`rosservice list` after {timeout}s - gazebo_ros doesn't appear "
          f"to namespace its core services here. Falling back to the plain "
          f"/gazebo/... names. NOTE: this means multiple UEs sharing this "
          f"roscore WILL collide on these names.")
    return ""


def circle_positions(n, radius, center=(0.0, 0.0)):
    cx, cy = center
    positions = []
    for i in range(n):
        theta = 2.0 * math.pi * i / n
        positions.append({
            "x": cx + radius * math.cos(theta),
            "y": cy + radius * math.sin(theta),
            "z": 0.0,
        })
    return positions


def too_close(p, others, min_dist=MIN_SPACING):
    return any(
        math.hypot(p["x"] - o["x"], p["y"] - o["y"]) < min_dist
        for o in others
    )


def compute_positions(num_robots, given):
    k = len(given)

    if k == 0:
        return circle_positions(num_robots, CIRCLE_RADIUS)

    if k >= num_robots:
        return given[:num_robots]

    # 0 < k < num_robots: keep given positions, auto-fill the rest near
    # their centroid instead of on the global circle.
    positions = list(given)
    cx = sum(p["x"] for p in given) / k
    cy = sum(p["y"] for p in given) / k

    remaining = num_robots - k
    radius = AUTO_FILL_RADIUS
    filled = 0
    attempt = 0
    while filled < remaining and attempt < remaining * 8:
        theta = 2.0 * math.pi * filled / remaining
        candidate = {
            "x": cx + radius * math.cos(theta),
            "y": cy + radius * math.sin(theta),
            "z": 0.0,
        }
        if too_close(candidate, positions):
            radius += 0.5
            attempt += 1
            continue
        positions.append(candidate)
        filled += 1
        attempt += 1

    return positions


def wait_for_model(model_name, timeout=30.0, interval=0.5):
    """Poll /gazebo/get_model_state until the model actually exists.

    jackal_world.launch spawns "jackal" via its own internal
    urdf_spawner node, asynchronously - gzserver being up (which is all
    entrypoint.sh's wait loop confirms) doesn't mean that spawn has
    finished yet. Without this, an immediate set_model_state call can
    race ahead and fail with "model does not exist".
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["rosservice", "call", f"{NS}/gazebo/get_model_state",
             json.dumps({"model_name": model_name})],
            capture_output=True, text=True, check=False,
        )
        if "success: True" in result.stdout:
            return True
        time.sleep(interval)
    return False


def spawn_or_move(index, model_name, pos):
    x, y, z = pos["x"], pos["y"], pos.get("z", 0.0)

    if index == 0 and not UE_NAMESPACE:
        # No namespace in play - jackal_world.launch's own internal spawn
        # of "jackal" works fine here (nothing is namespaced), so just
        # relocate it if the computed position differs from its default.
        if abs(x) > 1e-6 or abs(y) > 1e-6:
            if not wait_for_model(model_name):
                print(f"[spawn_robots] WARNING: {model_name} never showed "
                      f"up in Gazebo - skipping relocate, it will stay at "
                      f"the world's default spawn position.")
                return
            subprocess.run([
                "rosservice", "call", f"{NS}/gazebo/set_model_state",
                json.dumps({
                    "model_state": {
                        "model_name": model_name,
                        "pose": {"position": {"x": x, "y": y, "z": 0.2}},
                    }
                }),
            ], check=False)
        return

    if index == 0:
        # UE_NAMESPACE is set: jackal_world.launch's own internal spawn of
        # "jackal" uses rosrun gazebo_ros spawn_model with no
        # -gazebo_namespace override, which defaults to the absolute
        # "/gazebo" regardless of ROS_NAMESPACE - so it calls
        # "/gazebo/spawn_urdf_model" while our gzserver only advertises
        # "{NS}/gazebo/spawn_urdf_model" (confirmed via resolve_ns()
        # above), and just hangs forever waiting on a service that will
        # never be registered under that name. "jackal" never appears.
        # Give it a brief chance in case that's ever fixed upstream, then
        # spawn it ourselves explicitly instead, same as every other robot.
        if wait_for_model(model_name, timeout=5.0):
            subprocess.run([
                "rosservice", "call", f"{NS}/gazebo/set_model_state",
                json.dumps({
                    "model_state": {
                        "model_name": model_name,
                        "pose": {"position": {"x": x, "y": y, "z": 0.2}},
                    }
                }),
            ], check=False)
            return

    spawn_cmd = [
        "rosrun", "gazebo_ros", "spawn_model",
        "-urdf", "-model", model_name,
        "-param", "robot_description",
        "-x", str(x), "-y", str(y), "-z", "0.2",
    ]
    if UE_NAMESPACE:
        # spawn_model's -gazebo_namespace flag defaults to the literal
        # "/gazebo" (not empty) and builds the service name as
        # f"{gazebo_namespace}/spawn_urdf_model" - so the value here must
        # include the "/gazebo" segment itself, not just the bare
        # namespace prefix (NS alone), or it targets a service name
        # ("{NS}/spawn_urdf_model") that was never registered and hangs
        # forever in rospy.wait_for_service().
        spawn_cmd += ["-gazebo_namespace", f"{NS}/gazebo"]
    try:
        subprocess.run(spawn_cmd, check=False, timeout=90.0)
    except subprocess.TimeoutExpired:
        print(f"[spawn_robots] WARNING: spawn_model for {model_name} did "
              f"not finish within 90s - it may still appear late, or the "
              f"-gazebo_namespace target may be wrong. Check `rosservice "
              f"list | grep gazebo` to confirm the service name in use.")


def main():
    global NS
    NS = resolve_ns()

    raw_positions = os.environ.get("ROBOT_POSITIONS", "").strip()
    given = json.loads(raw_positions) if raw_positions else []
    for p in given:
        p.setdefault("z", 0.0)

    positions = compute_positions(NUM_ROBOTS, given)

    layout = []
    for i, pos in enumerate(positions):
        model_name = "jackal" if i == 0 else f"jackal_{i + 1}"
        robot_topic = f"robot{i + 1}"
        layout.append({
            "robot_topic": robot_topic,
            "model_name": model_name,
            "x": pos["x"],
            "y": pos["y"],
            "z": pos.get("z", 0.0),
        })
        spawn_or_move(i, model_name, pos)

    with open(LAYOUT_FILE, "w") as f:
        json.dump(layout, f, indent=2)

    print(f"[spawn_robots] Wrote layout for {len(layout)} robots to {LAYOUT_FILE}")
    for r in layout:
        print(f"  {r['robot_topic']} -> {r['model_name']} at "
              f"({r['x']:.2f}, {r['y']:.2f}), z={r['z']:.2f}")


if __name__ == "__main__":
    main()
