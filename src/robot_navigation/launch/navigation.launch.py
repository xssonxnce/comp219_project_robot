import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.actions import SetEnvironmentVariable
import xacro

def generate_launch_description():

    # define paths for gazebo, turtlebot, and world
    pkg_ros_gz_sim = get_package_share_directory('ros_gz_sim')
    pkg_robot_description = get_package_share_directory('robot_description')
    pkg_robot_navigation = get_package_share_directory('robot_navigation')
    
    # get turtlebot
    pkg_turtlebot = get_package_share_directory('turtlebot3_gazebo')
    tb_model = os.getenv('TURTLEBOT3_MODEL','burger')

    # define path to robot urdf file
    urdf_file_name = f'turtlebot3_{tb_model}.urdf'
    urdf_path = os.path.join(get_package_share_directory('turtlebot3_description'), 'urdf', urdf_file_name)

    robot_desc = xacro.process_file(urdf_path).toxml()

    
    #get world and map
    world_path = os.path.join(pkg_robot_description,'worlds','map.sdf')
    map_path = os.path.join(pkg_robot_navigation,   "maps",   "map.yaml")


    set_gz_resource_path = SetEnvironmentVariable(
    name='GZ_SIM_RESOURCE_PATH',
    value=[os.path.join(pkg_robot_description, 'worlds'), ':', 
           os.path.join(get_package_share_directory('turtlebot3_description'),'models'),':',
           os.path.join(pkg_turtlebot, 'models')]
    )
    
    # launch gazebo with map
    gazebo_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': f'-r {world_path}'}.items() # -r starts it running immediately
    )

    # Node - robot state publisher
    state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[{"robot_description": robot_desc, "use_sim_time": True}]
    )


    # Node - spawn robot
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-file', os.path.join(pkg_turtlebot, 'models',f'turtlebot3_{tb_model}','model.sdf'),
            '-name', 'turtlebot3_burger',
            '-x', '0', '-y', '0', '-z', '0.05'
        ],
        output='screen'
        
     
    )

   # 4. Node - ros-gz bridge 
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/model/turtlebot3_burger/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/model/turtlebot3_burger/odometry@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/cmd_vel@geometry_msgs/msg/Twist@gz.msgs.Twist',
            '/odom@nav_msgs/msg/Odometry@gz.msgs.Odometry',
            '/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan',

            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'
        ],
        remappings=[('/model/turtlebot3_burger/tf', '/tf'),
                    ('/model/turtlebot3_burger/odometry', '/odom'),
                    ('/model/turtlebot3_burger/cmd_vel', '/cmd_vel'),
                    ('/model/turtlebot3_burger/scan', '/scan'),
        ],
        parameters=[{'use_sim_time':True}],
        output='screen'
    )

    # Node. map server
    map_server = Node(
        package="nav2_map_server",
        executable="map_server",
        name="map_server",
        output="screen",
        parameters=[{
            "use_sim_time": True,
            "yaml_filename": map_path
        }]
    )

    amcl = Node(
            package='nav2_amcl',
            executable='amcl',
            name='amcl',
            output='screen',
            parameters=[{
                'use_sim_time':True,
            }]

    )

    lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_navigation',
        output='screen',
        parameters=[{
            'use_sim_time':True,
            'autostart':True,
            'node_names': ['map_server','amcl']
        }]
    )
    
    
    
    ld = LaunchDescription()

    ld.add_action(set_gz_resource_path)
    ld.add_action(gazebo_cmd)
    ld.add_action(state_publisher)
    ld.add_action(spawn_robot)
    ld.add_action(bridge)
    ld.add_action(map_server)
    ld.add_action(amcl)
    ld.add_action(lifecycle_manager)
    
    return ld
