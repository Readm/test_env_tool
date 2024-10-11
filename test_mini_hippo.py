import unittest
import tempfile
import os
import subprocess
from mini_hippo import ADBShell, SSHShell, LocalShell, hippo_logger

class TestShells(unittest.TestCase):

    # SSH 配置可以从环境变量读取，确保用户提供这些配置
    def get_ssh_config(self):
        return {
            'host': os.getenv('SSH_HOST', 'localhost'),
            'port': int(os.getenv('SSH_PORT', '22')),
            'username': os.getenv('SSH_USERNAME', ''),
            'password': os.getenv('SSH_PASSWORD', ''),
            'key_filename': os.getenv('SSH_KEY_FILENAME', None)  # 允许使用私钥认证
        }

    # ADB 配置可以从环境变量读取，确保用户提供这些配置
    def get_adb_config(self):
        return {
            'device_id': os.getenv('ADB_DEVICE_ID', None),
            'adb_path': os.getenv('ADB_PATH', '/home/l00599256/ArchPathologyExplorer/tmptools/platform-tools/adb.exe')
        }

    def common_exec_test(self, shell):
        output, return_code = shell.exec("echo 'Hello, LocalShell!'")
        self.assertEqual(output.strip(), "Hello, LocalShell!")
        self.assertEqual(return_code, 0)

    def common_file_transfer_test(self, shell):
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建一个临时文件
            temp_file_path = os.path.join(temp_dir, "test_file.txt")
            dest_folder = "dest_folder"
            with open(temp_file_path, 'w') as temp_file:
                temp_file.write("Test content")
                temp_file.flush()
            # 测试发送文件
            shell.send(temp_file_path, relative_path=dest_folder)

            # 测试拉取文件
            pull_dest = os.path.join(temp_dir, "pull_dest")
            shell.pull(pull_dest, relative_file_path=os.path.join(
                dest_folder, "test_file.txt"))
            self.assertTrue(os.path.join(pull_dest, "text_file.txt"))
            with open(os.path.join(pull_dest, "test_file.txt")) as f:
                self.assertEqual(f.read(), "Test content")
            shell.exec("rm -rf dest_folder/test_file.txt")

    def common_folder_transfer_test(self, shell):
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建临时文件夹并添加文件
            temp_folder_path = os.path.join(temp_dir, "test_folder")
            os.makedirs(temp_folder_path)
            temp_file_path = os.path.join(temp_folder_path, "test_file.txt")
            with open(temp_file_path, 'w') as temp_file:
                temp_file.write("Test folder content")

            dest_folder = "dest_folder"
            shell.send(temp_folder_path,
                       relative_path=dest_folder)

            # 拉取文件夹
            pull_dest = os.path.join(temp_dir, "pull_dest")
            shell.pull(pull_dest, relative_file_path=os.path.join(
                dest_folder, "test_folder"))

            pulled_folder_path = os.path.join(pull_dest, "test_folder")
            pulled_file_path = os.path.join(pulled_folder_path, "test_file.txt")

            self.assertTrue(os.path.exists(pulled_folder_path))
            self.assertTrue(os.path.exists(pulled_file_path))
            with open(pulled_file_path) as f:
                self.assertEqual(f.read(), "Test folder content")
            shell.exec("rm -rf dest_folder")

    # 测试 LocalShell 执行命令
    def test_local_exec(self):
        local_shell = LocalShell(name="local")
        self.common_exec_test(local_shell)

    # 测试 LocalShell 的文件传输功能
    def test_local_file_transfer(self):
        local_shell = LocalShell(name="local")
        self.common_file_transfer_test(local_shell)

    def test_local_folder_transfer(self):
        local_shell = LocalShell(name="local")
        self.common_folder_transfer_test(local_shell)

    # 测试 SSHShell 的命令执行功能
    def test_ssh_exec(self):
        ssh_config = self.get_ssh_config()
        ssh_shell = SSHShell(
            name="ssh_test", host=ssh_config['host'],
            port=ssh_config['port'],
            username=ssh_config['username'],
            password=ssh_config['password'],
            key_filename=ssh_config['key_filename'])

        self.common_exec_test(ssh_shell)

    # 测试 SSHShell 的文件传输功能
    def test_ssh_file_transfer(self):
        ssh_config = self.get_ssh_config()
        ssh_shell = SSHShell(
            name="ssh_test", host=ssh_config['host'],
            port=ssh_config['port'],
            username=ssh_config['username'],
            password=ssh_config['password'],
            key_filename=ssh_config['key_filename'])
        self.common_file_transfer_test(ssh_shell)

    def test_ssh_folder_transfer(self):
        ssh_config = self.get_ssh_config()
        ssh_shell = SSHShell(
            name="ssh_test", host=ssh_config['host'],
            port=ssh_config['port'],
            username=ssh_config['username'],
            password=ssh_config['password'],
            key_filename=ssh_config['key_filename'])
        self.common_folder_transfer_test(ssh_shell)

    # 测试 ADBShell 的命令执行功能
    def test_adb_exec(self):
        adb_config = self.get_adb_config()
        adb_shell = ADBShell(
            device_id=adb_config['device_id'],
            adb_path=adb_config['adb_path'])
        self.common_exec_test(adb_shell)

    # 测试 ADBShell 的文件传输功能
    def test_adb_file_transfer(self):
        adb_config = self.get_adb_config()
        adb_shell = ADBShell(
            device_id=adb_config['device_id'],
            adb_path=adb_config['adb_path'])
        self.common_file_transfer_test(adb_shell)

    def test_adb_folder_transfer(self):
        adb_config = self.get_adb_config()
        adb_shell = ADBShell(
            device_id=adb_config['device_id'],
            adb_path=adb_config['adb_path'])
        self.common_folder_transfer_test(adb_shell)


if __name__ == '__main__':
    unittest.main()
