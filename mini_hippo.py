'''This file is a minimal hippo tool set for test on different enviorment.
The main aim is to help running the mini_test packages on different platform,
includnig adb, local linux and ssh.

Basic functions:
+ Framwork Logging
+ Differnt Platform
'''

''' ONLY import default libaries here, dynamic import in other parts,
to avoid install when not required'''

'''========================Logger===================================='''
import logging
import os
import subprocess
import shutil
from abc import ABC, abstractmethod
hippo_logger = logging.getLogger("hippo")
hippo_logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    '[hippo] %(asctime)s - %(levelname)5s - %(message)s', datefmt='%H:%M:%S')
console_handler.setFormatter(formatter)
hippo_logger.addHandler(console_handler)

'''========================Shells===================================='''


class Shell(ABC):
    def __init__(self, name, root_path="/tmp"):
        self.name = name
        self.root_path = root_path
        self.type = None

    def __str__(self):
        return self.name

    @abstractmethod
    def exec(self, cmd, relative_path=''):
        pass

    @abstractmethod
    def send(self, local_file_path, relative_path=''):
        pass

    @abstractmethod
    def pull(self, local_folder_path, relative_file_path):
        pass


class ADBShell(Shell):
    def __init__(self, name="adb", device_id=None, env_cmd="",
                 root_path='/data/local/tmp', adb_path="adb"):
        super().__init__(name, root_path)
        self.type = "ADB"
        self.device_id = device_id
        self.env_cmd = env_cmd
        self.root_path = root_path
        self.adb_path = adb_path if adb_path else "adb"

    def __str__(self):
        return f"{self.type}_Env_{self.name}"

    def exec(self, command, relative_path=".", ignore_error=False):
        exec_path = os.path.join(
            self.root_path, relative_path).replace(
            '\\', '/')
        command = f"cd {exec_path} && " + command
        if self.env_cmd:
            command = self.env_cmd + " " + command
        if self.device_id:
            command = f"{self.adb_path} -s {self.device_id} shell \"{command}\""
        else:
            command = f"{self.adb_path} shell \"{command}\""
        hippo_logger.debug(f"exec @ adb_{self.device_id}: {command}")
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                shell=True)
            stdout, stderr = process.communicate(timeout=600)
            return_code = process.wait()
            output = stdout.decode('utf-8')
            error = stderr.decode('utf-8')
            if return_code != 0 and not ignore_error:
                hippo_logger.warning(
                    f"Execution return code not 0: exec @ adb_{self.device_id}: {command}, STDERR: \n======\n{error}\n======")

            return output, return_code

        except Exception as e:
            if ignore_error:
                return str(e), -1
            else:
                raise e

    def send(self, local_file_path, relative_path="."):
        remote_path = os.path.join(
            self.root_path, relative_path).replace(
            '\\', '/')
        hippo_logger.debug(
            f"sending file: {local_file_path}, to adb_{self.device_id}:{remote_path}")
        self.exec(f"mkdir -p {remote_path}")
        command = f"{self.adb_path} push {local_file_path} {remote_path}"
        hippo_logger.debug(f"sending cmd: {command}")
        if self.device_id:
            command = f"{self.adb_path} push -s {self.device_id} {local_file_path} {remote_path}"

        try:
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) as process:
                process.wait(timeout=600)
        except Exception as e:
            hippo_logger.error(str(e))

    def pull(self, local_folder_path, relative_file_path="."):
        remote_path = os.path.join(
            self.root_path, relative_file_path).replace(
            '\\', '/')
        hippo_logger.debug(
            f"pull file:  adb_{self.device_id}:{remote_path} to {local_folder_path}")
        command = f"{self.adb_path} pull {remote_path} {local_folder_path}"
        os.makedirs(local_folder_path, exist_ok=True)
        if self.device_id:
            command = f"{self.adb_path} pull -s {self.device_id} {remote_path} {local_folder_path}"
        try:
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True) as process:
                process.wait()
        except Exception as e:
            hippo_logger.error(str(e))


class SSHShell(Shell):
    def __init__(
            self, name, root_path="/tmp", host="localhost", port=22,
            username="root", password="", key_filename=None, env_cmd=""):

        super().__init__(name, root_path)
        self.type = "SSH"
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.root_path = root_path
        self.env_cmd = env_cmd
        self.client = self._connect()

    def __str__(self):
        return f"{self.type}_Env_{self.name}_{self.username}_at_{self.host}"

    def __del__(self):
        self.client.close()

    def _connect(self):
        import paramiko
        import scp
        """建立 SSH 连接，支持密钥和密码登录"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            # 如果指定了 key_filename 则使用密钥，否则使用密码
            if self.key_filename:
                hippo_logger.debug(
                    f"Using SSH key for authentication: {self.key_filename}")
                client.connect(
                    self.host, port=self.port, username=self.username,
                    key_filename=self.key_filename, timeout=5,
                    banner_timeout=200)
            else:
                hippo_logger.debug(
                    f"Using password for authentication to {self.host}")
                client.connect(
                    self.host, port=self.port, username=self.username,
                    password=self.password, timeout=5, banner_timeout=200)
            return client
        except paramiko.SSHException as ssh_error:
            hippo_logger.error(f"SSH connection failed: {str(ssh_error)}")
            raise ssh_error
        except Exception as e:
            hippo_logger.error(
                f"Unexpected error during SSH connection: {str(e)}")
            raise e

    def exec(self, command, relative_path=".", ignore_error=False):
        exec_path = os.path.join(
            self.root_path, relative_path).replace('\\', '/')
        if self.env_cmd:
            command = self.env_cmd + " " + command
        hippo_logger.debug(f"exec @ {self.host}: {command}")
        try:
            stdin, stdout, stderr = self.client.exec_command(
                f"cd {exec_path} &&" + command)
            output = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            return_code = stdout.channel.recv_exit_status()
            if return_code != 0:
                hippo_logger.warning(
                    f"Execution return code not 0: exec @ {self.host}: {command}, STDERR: \n======\n{error}\n======")

            return output, return_code

        except Exception as e:
            if ignore_error:
                return str(e), -1
            else:
                raise e

    def send(self, local_file_path, relative_path="."):
        import paramiko
        import scp
        remote_path = os.path.join(
            self.root_path, relative_path).replace('\\', '/')
        hippo_logger.debug(
            f"sending file: {local_file_path}, to {self.username}@{self.host}:{remote_path}")
        self.exec(f"mkdir -p {remote_path}")
        try:
            scpclient = scp.SCPClient(
                self.client.get_transport(),
                socket_timeout=15.0)
            scpclient.put(local_file_path, remote_path, recursive=True)

        except Exception as e:
            hippo_logger.error(str(e))

    def pull(self, local_folder_path, relative_file_path="."):
        import paramiko
        import scp
        remote_path = os.path.join(
            self.root_path, relative_file_path).replace('\\', '/')
        hippo_logger.debug(
            f"downloading file: {local_folder_path}, from {self.username}@{self.host}:{remote_path}")
        try:
            os.makedirs(local_folder_path, exist_ok=True)
            scpclient = scp.SCPClient(
                self.client.get_transport(),
                socket_timeout=15.0)
            scpclient.get(remote_path, local_folder_path, recursive=True)

        except Exception as e:
            hippo_logger.error(str(e))


class LocalShell(Shell):
    def __init__(self, name, root_path="/tmp", env_cmd=""):
        super().__init__(name, root_path)
        self.type = "Local"
        self.root_path = root_path
        self.env_cmd = env_cmd

    def __str__(self):
        return f"{self.type}"

    def exec(self, command, relative_path=".", ignore_error=False):
        exec_path = os.path.join(
            self.root_path, relative_path).replace(
            '\\', '/')
        if self.env_cmd:
            command = self.env_cmd + " " + command

        full_command = f"cd {exec_path} && {command}"
        hippo_logger.debug(f"exec @ {self}: {full_command}")

        try:
            result = subprocess.run(
                full_command, shell=True, capture_output=True, text=True,
                check=True)
            output = result.stdout
            error = result.stderr
            return_code = result.returncode

            if return_code != 0:
                hippo_logger.warning(
                    f"Execution return code not 0: exec @ {self}: {command}, STDERR: \n======\n{error}\n======")

            return output, return_code
        except subprocess.CalledProcessError as e:
            hippo_logger.error(f"Error executing command: {str(e)}")
            if ignore_error:
                return e.stderr, e.returncode  # 提供stderr作为输出
            else:
                raise e  # 重新抛出异常
        except Exception as e:
            hippo_logger.error(f"Unexpected error: {str(e)}")
            if ignore_error:
                return str(e), -1
            else:
                raise e

    def send(self, local_file_path, relative_path="."):
        # 构建远程路径
        remote_path = os.path.join(
            self.root_path, relative_path).replace(
            '\\', '/')
        hippo_logger.debug(f"Copying file: {local_file_path}, to {remote_path}")

        try:
            # 确保远程目录存在
            os.makedirs(remote_path, exist_ok=True)

            # 自动判断是文件夹还是文件
            if os.path.isdir(local_file_path):
                # 如果是文件夹，使用 shutil.copytree 递归复制
                shutil.copytree(local_file_path, os.path.join(
                    remote_path, os.path.basename(local_file_path)))
            else:
                # 如果是文件，使用 shutil.copy2 复制文件
                shutil.copy2(local_file_path, remote_path)

        except Exception as e:
            hippo_logger.error(f"Error copying file: {str(e)}")

    def pull(self, local_folder_path, relative_file_path="."):

        remote_path = os.path.join(
            self.root_path, relative_file_path).replace(
            '\\', '/')
        hippo_logger.debug(
            f"Copying file: {remote_path}, to {local_folder_path}")
        try:
            os.makedirs(local_folder_path, exist_ok=True)

            if os.path.isdir(remote_path):
                shutil.copytree(remote_path, os.path.join(
                    local_folder_path, os.path.basename(remote_path)))
            else:
                shutil.copy2(remote_path, local_folder_path)

        except Exception as e:
            hippo_logger.error(f"Error pulling file: {str(e)}")
