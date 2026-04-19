import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, SetEnvironmentVariable
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import xacro
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

def generate_launch_description():

    pkg_robot = get_package_share_directory("robot_description")
    pkg_nav   = get_package_share_directory("robot_navigation")
    pkg_tb3   = get_package_share_directory("turtlebot3_gazebo")

    world_file = os.path.join(pkg_robot, "worlds", "map.sdf")

    urdf_file = os.path.join(
    get_package_share_directory("turtlebot3_description"),
    "urdf", "turtlebot3_burger.urdf" 
    )

    # Process the file with xacro to resolve ${namespace}
    robot_desc = xacro.process_file(urdf_file, mappings={'namespace': ''}).toxml()

    # Define missing gazebo plugin for model
    plugin_injection = """
    <gazebo>
        <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher">
          <topic>joint_states</topic>
        </plugin>
      </gazebo>
      
      <gazebo reference="base_scan">
        <sensor name="hls_lfcd_lds" type="gpu_lidar">
          <always_on>true</always_on>
          <visualize>true</visualize>
          <update_rate>5</update_rate>
          <topic>/scan</topic>
          <gz_frame_id>base_scan</gz_frame_id>
          <lidar>
            <scan>
              <horizontal>
                <samples>360</samples>
                <resolution>1.000000</resolution>
                <min_angle>0.000000</min_angle>
                <max_angle>6.280000</max_angle>
              </horizontal>
            </scan>
            <range>
              <min>0.120000</min>
              <max>3.5</max>
              <resolution>0.015000</resolution>
            </range>
          </lidar>
        </sensor>
      </gazebo>
    </robot>
    """
    robot_desc = robot_desc.replace('</robot>',plugin_injection)
    
                            
    return LaunchDescription([


        # Set TurtleBot3 model
        SetEnvironmentVariable("TURTLEBOT3_MODEL", "burger"),

        # Launch Gazebo with world
        ExecuteProcess(
            cmd=["gz", "sim", "-r", world_file],
            output="screen"
        ),

        # Auto-unpause after 5 seconds
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

        #Robot State Publisher
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            name="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_desc, "use_sim_time": True}]
        ),

        # Spawn TurtleBot3 in cafe world
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

        # ROS-GZ Bridge
        
        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=[
                '/model/turtlebot3_burger/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
                '/model/turtlebot3_burger/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry',
                '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',                 
                '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
                '/model/turtlebot3_burger/joint_states@sensor_msgs/msg/JointState[gz.msgs.Model',
                '/model/turtlebot3_burger/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist'
            ],
            remappings=[
                ('/model/turtlebot3_burger/tf', '/tf'),
                ('/model/turtlebot3_burger/odometry', '/odom'),
                ('/model/turtlebot3_burger/joint_states', '/joint_states'),
                ('/model/turtlebot3_burger/cmd_vel', '/cmd_vel'),
            ],
        parameters=[{'use_sim_time':True}],
        output='screen'),

        # Transform publisher bridge
        Node(
        package='tf2_ros',
        executable='static_transform_publisher',
            arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--yaw', '0', '--pitch', '0', '--roll', '0',
            '--frame-id', 'base_footprint',
            '--child-frame-id', 'base_link',
            ]
        ),

       # Force the odom frame into existence so Nav2 can boot
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0',
                '--yaw', '0', '--pitch', '0', '--roll', '0',
                '--frame-id', 'odom',
                '--child-frame-id', 'base_footprint'
            ]
        ),
        # 6. SLAM Toolbox
        Node(
            package="slam_toolbox",
            executable="async_slam_toolbox_node",
            name="slam_toolbox",
            output="screen",
            parameters=[{
                "use_sim_time": True,
                'max_laser_range': 3.5,
                'resolution': 0.05,
                'map_update_interval': 5.0,
                'odom_frame': 'odom',
                'map_frame': 'map',
                'base_frame': 'base_footprint',
                'scan_topic': '/scan',
                'mode': 'mapping',
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

        # 8. Joint state publisher
        Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[{'use_sim_time': True}],
        # It automatically subscribes to /robot_description published by robot_state_publisher
        ),

        #9. Nav2 stack
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory("nav2_bringup"),
                    "launch",
                    "navigation_launch.py"
                )
            ),
            # Pass use_sim_time to all Nav2 nodes
            launch_arguments={'use_sim_time': 'true'}.items()
        ),

    ])
