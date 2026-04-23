import math
import os
import yaml

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient

from geometry_msgs.msg import PoseStamped
from nav2_msgs.action import NavigateToPose
from ament_index_python.packages import get_package_share_directory

from robot_llm.mistral_client import parse_with_mistral


class LLMCommandNode(Node):

    def __init__(self):
        super().__init__('llm_command_node')
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self.get_logger().info("Mistral LLM Node Started")

        package_share = get_package_share_directory('robot_llm')
        config_path = os.path.join(package_share, 'config', 'locations.yaml')

        with open(config_path, 'r') as f:
            self.locations = yaml.safe_load(f)['locations']

        self.get_logger().info(f"Loaded locations: {list(self.locations.keys())}")

    def send_goal(self, x, y, yaw):
        if not self.nav_client.wait_for_server(timeout_sec=10.0):
            self.get_logger().error("Nav2 not available")
            return

        goal_msg = NavigateToPose.Goal()
        goal_msg.pose = PoseStamped()

        goal_msg.pose.header.frame_id = "map"
        goal_msg.pose.header.stamp = self.get_clock().now().to_msg()

        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.position.z = 0.0

        qz = math.sin(yaw / 2.0)
        qw = math.cos(yaw / 2.0)

        goal_msg.pose.pose.orientation.x = 0.0
        goal_msg.pose.pose.orientation.y = 0.0
        goal_msg.pose.pose.orientation.z = qz
        goal_msg.pose.pose.orientation.w = qw

        self.get_logger().info(f"Sending goal -> {x}, {y}, {yaw}")
        self.nav_client.send_goal_async(goal_msg)

    def run(self):
        while True:
            command = input("Enter command: ").strip()

            if command.lower() in ["exit", "quit"]:
                break

            try:
                destination = parse_with_mistral(command)
                print("Parsed destination:", destination)
            except Exception as e:
                print("Mistral error:", e)
                continue

            if destination in self.locations:
                loc = self.locations[destination]
                self.send_goal(loc['x'], loc['y'], loc['yaw'])
            else:
                print("Unknown destination")


def main(args=None):
    rclpy.init(args=args)
    node = LLMCommandNode()
    node.run()
    node.destroy_node()
    rclpy.shutdown()