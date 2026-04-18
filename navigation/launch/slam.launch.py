import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, SetEnvironmentVariable
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    pkg_robot = get_package_share_directory("my_robot_description")
    pkg_nav   = get_package_share_directory("navigation")
    pkg_tb3   = get_package_share_directory("turtlebot3_gazebo")

    world_file = os.path.join(pkg_robot, "worlds", "map.sdf")

    urdf_file = os.path.join(
        get_package_share_directory("turtlebot3_description"),
        "urdf", "turtlebot3_burger.urdf"
    )
    with open(urdf_file, "r") as f:
        robot_desc = f.read()

    return LaunchDescription([

        # Set TurtleBot3 model
        SetEnvironmentVariable("TURTLEBOT3_MODEL", "burger"),

        # 1. Launch Gazebo with cafe world
        ExecuteProcess(
            cmd=["gz", "sim", "-r", world_file],
            output="screen"
        ),

        # 2. Auto-unpause after 5 seconds
        TimerAction(
            period=5.0,
            actions=[
                ExecuteProcess(
                    cmd=["gz", "service", "-s", "/world/map/control",
                         "--reqtype", "gz.msgs.WorldControl",
                         "--reptype", "gz.msgs.Boolean",
                         "--timeout", "2000",
                         "--req", "pause: false"],
                    output="screen"
                )
            ]
        ),

        # 3. Robot State Publisher
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_desc, "use_sim_time": True}]
        ),

        # 4. Spawn TurtleBot3 in cafe world
        Node(
            package="ros_gz_sim",
            executable="create",
            arguments=[
                "-name", "turtlebot3_burger",
                "-topic", "robot_description",
                "-x", "0.0",
                "-y", "0.0",
                "-z", "0.1"
            ],
            output="screen"
        ),

        # 5. ROS-GZ Bridge
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=[
                "/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan",
                "/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist",
                "/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry",
                "/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock",
                "/tf@tf2_msgs/msg/TFMessage@gz.msgs.Pose_V",
                "/joint_states@sensor_msgs/msg/JointState@gz.msgs.Model",
                "/imu@sensor_msgs/msg/Imu@gz.msgs.IMU",
            ],
            output="screen"
        ),

        # 6. SLAM Toolbox
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "odom_frame": "odom",
                "map_frame": "map",
                "base_frame": "base_footprint",
                "scan_topic": "/scan",
                "mode": "mapping",
            }]
        ),

        # 7. RViz2
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            parameters=[{"use_sim_time": True}]
        ),

    ])
