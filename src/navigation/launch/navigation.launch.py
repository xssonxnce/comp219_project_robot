import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, ExecuteProcess
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():

    pkg_robot = get_package_share_directory("my_robot_description")
    pkg_nav   = get_package_share_directory("navigation")

    # Robot description (URDF)
    import xacro
    urdf_file  = os.path.join(pkg_robot, "urdf", "robot.urdf.xacro")
    robot_desc = xacro.process_file(urdf_file).toxml()

    # Paths
    world_file  = os.path.join(pkg_robot, "worlds", "map.sdf")
    map_file    = os.path.join(pkg_nav,   "maps",   "cafe_map.yaml")
    nav2_params = os.path.join(pkg_nav,   "config", "nav2_params.yaml")
    nav2_launch = os.path.join(
        get_package_share_directory("nav2_bringup"), "launch", "navigation_launch.py"
    )

    return LaunchDescription([

        # 1. Gazebo
        ExecuteProcess(
            cmd=["gz", "sim", "-r", world_file],
            output="screen"
        ),

        # 2. Robot State Publisher
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_desc, "use_sim_time": True}]
        ),

        # 3. Spawn robot
        Node(
            package="ros_gz_sim",
            executable="create",
            arguments=[
                "-name", "cafe_robot",
                "-topic", "robot_description",
                "-x", "0.0",
                "-y", "0.0",
                "-z", "0.1"
            ],
            output="screen"
        ),

        # 4. ROS-GZ Bridge
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
            ],
            output="screen"
        ),

        # 5. Map Server
        Node(
            package="nav2_map_server",
            executable="map_server",
            name="map_server",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "yaml_filename": map_file
            }]
        ),

        # 6. AMCL Localization
        Node(
            package="nav2_amcl",
            executable="amcl",
            name="amcl",
            output="screen",
            parameters=[nav2_params]
        ),

        # 7. Nav2 Stack
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(nav2_launch),
            launch_arguments={
                "use_sim_time": "true",
                "params_file": nav2_params,
            }.items()
        ),

        # 8. Lifecycle Manager for map_server and amcl
        Node(
            package="nav2_lifecycle_manager",
            executable="lifecycle_manager",
            name="lifecycle_manager_localization",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                "autostart": True,
                "node_names": ["map_server", "amcl"]
            }]
        ),

        # 9. RViz2
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            parameters=[{"use_sim_time": True}]
        ),

    ])
