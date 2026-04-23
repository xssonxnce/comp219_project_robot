from setuptools import find_packages, setup
import os

package_name = 'robot_llm'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
    ('share/ament_index/resource_index/packages',
        ['resource/' + package_name]),
    ('share/' + package_name, ['package.xml']),
    ('share/' + package_name + '/config', ['config/locations.yaml']),
],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='hannah',
    maintainer_email='hannah@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'llm_command_node = robot_llm.llm_command_node:main',
        ],
    },
)