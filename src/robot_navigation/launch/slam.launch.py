import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, TimerAction, SetEnvironmentVariable
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import xacro
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from nav2_common.launch import RewrittenYaml

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
   # Define missing gazebo plugin for model
    plugin_injection = """
    <gazebo>
        <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher">
          <topic>/model/turtlebot3_burger/joint_states</topic>
        </plugin>

        <plugin filename="gz-sim-diff-drive-system" name="gz::sim::systems::DiffDrive">
          <left_joint>wheel_left_joint</left_joint>
          <right_joint>wheel_right_joint</right_joint>
          <wheel_separation>0.160</wheel_separation>
          <wheel_radius>0.033</wheel_radius>
          <topic>/model/turtlebot3_burger/cmd_vel</topic>
          <odom_topic>/model/turtlebot3_burger/odometry</odom_topic>
          <tf_topic>/model/turtlebot3_burger/tf</tf_topic>
          <frame_id>odom</frame_id>
          <child_frame_id>base_footprint</child_frame_id>
        </plugin>
      </gazebo>
      
      <gazebo reference="base_scan">
        <sensor name="hls_lfcd_lds" type="gpu_lidar">
          <always_on>true</always_on>
          <visualize>true</visualize>
          <update_rate></update_rate>
          <topic>/scan</topic>
          <frame_id>base_scan</frame_id>
          <lidar>
            <scan>
              <horizontal>
                <samples>120</samples>
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
    
    nav2_params_file = os.path.join(
        get_package_share_directory('nav2_bringup'),
        'params',
        'nav2_params.yaml'
    )

    # Dynamically inject use_sim_time into the default parameters
    configured_params = RewrittenYaml(
        source_file=nav2_params_file,
        root_key='',
        param_rewrites={'use_sim_time': 'true'},
        convert_types=True
    )
    return LaunchDescription([


        # Set TurtleBot3 model
        SetEnvironmentVariable("TURTLEBOT3_MODEL", "burger"),

        # Launch Gazebo with world
        ExecuteProcess(
            cmd=["gz", "sim", "-r", world_file],
            #parameters=[{'use_sim_time':True}], # added this one
            output="screen",
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
            parameters=[{"robot_description": robot_desc, "use_sim_time": True}],
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
            parameters=[{'use_sim_time':True}], # added this one
            output="screen",
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
            output='screen'
            ),
    
        
        # 2. Add a NEW transform to connect Gazebo's stubborn Lidar frame name to the ROS URDF
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0',
                '--yaw', '0', '--pitch', '0', '--roll', '0',
                '--frame-id', 'base_scan',
                '--child-frame-id', 'turtlebot3_burger/base_footprint/hls_lfcd_lds',
                '--ros-args', '-p', 'use_sim_time:=true'
            ]
        ),
        

        # 1. Weld the TF tree back together (odom -> base_footprint -> base_link)
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '--x', '0', '--y', '0', '--z', '0',
                '--yaw', '0', '--pitch', '0', '--roll', '0',
                '--frame-id', 'base_footprint',
                '--child-frame-id', 'base_link',
                '--ros-args', '-p', 'use_sim_time:=true'
            ]
        ),

        # 2. Aesthetic Left Wheel Transform
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '--x', '0', '--y', '0.08', '--z', '0.033',
                '--yaw', '0', '--pitch', '0', '--roll', '0',
                '--frame-id', 'base_link',
                '--child-frame-id', 'wheel_left_link',
                '--ros-args', '-p', 'use_sim_time:=true'
            ]
        ),

        # 3. Aesthetic Right Wheel Transform
        Node(
            package='tf2_ros',
            executable='static_transform_publisher',
            arguments=[
                '--x', '0', '--y', '-0.08', '--z', '0.033',
                '--yaw', '0', '--pitch', '0', '--roll', '0',
                '--frame-id', 'base_link',
                '--child-frame-id', 'wheel_right_link',
                '--ros-args', '-p', 'use_sim_time:=true'
            ]
        ),
        
        # 6. SLAM Toolbox
       # 6. SLAM Toolbox (Official Lifecycle Launch)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory("slam_toolbox"),
                    "launch",
                    "online_async_launch.py"
                )
            ),
            # The official launch file natively handles sim time and default parameters!
            launch_arguments={
                'use_sim_time': 'true'
            }.items()
        ),
        
        # 7. RViz2
        Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="screen",
            parameters=[{"use_sim_time": True}],
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
            launch_arguments={'use_sim_time': 'true',
                              'params_file':configured_params}.items()
        ),

    ])
