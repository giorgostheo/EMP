from setuptools import setup, find_packages
from setuptools.command.install import install as _install
import os
import shutil

class CustomInstall(_install):
    def run(self):
        _install.run(self)
        user_home = os.path.expanduser("~")
        emp_dir = os.path.join(user_home, '.emp')

        # Create .emp directory if not exists
        os.makedirs(emp_dir, exist_ok=True)

        # Locate hosts.json using pkg_resources
        import pkg_resources
        src_hosts = pkg_resources.resource_filename('emp_package', 'hosts.json')
        dest_hosts = os.path.join(emp_dir, 'hosts.json')

        # Copy only if destination file doesn't exist
        if not os.path.exists(dest_hosts):
            try:
                if os.path.exists(src_hosts):
                    shutil.copy(src_hosts, dest_hosts)
            except Exception as e:
                print(f"Warning: Could not copy hosts.json to {emp_dir}: {str(e)}")

setup(
    name='emp_package',
    version='0.1.0',
    description='A CLI tool for managing hosts and executing tasks',
    author='Your Name',
    packages=find_packages(),
    package_data={'emp_package': ['hosts.json']},  # Include hosts.json in the package
    install_requires=[
        'paramiko',
        'termcolor',
        'scp',
        'argparse',
        'numpy'  # Remove if not needed
    ],
    entry_points={
        'console_scripts': [
            'emp=emp_package.emp:main',
        ],
    },
    cmdclass={'install': CustomInstall},
)