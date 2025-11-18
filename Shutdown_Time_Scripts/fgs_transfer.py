import os
import sys
import time
import shutil
import tarfile
import telnetlib
import subprocess
from ftplib import FTP
import serial
from pathlib import Path


class FGSTransfer:
    
    def __init__(self, config, logger, host_ip: str, telnet_user: str, telnet_passwd: str, ftp_user: str, ftp_passwd: str):
        self.config = config
        self.logger = logger
        self.script_path = Path(__file__).parent
        self.temp_dir = os.path.join(self.script_path, "Extract")
        self.remote_dir = "/ksar/opt"
        self.remote_fgs_dir = f"{self.remote_dir}/functiongroupswitcher"
        self.local_fgs_dir = os.path.join(self.script_path, "functiongroupswitcher")
        self.archive_name = "functiongroupswitcher.tar"
        self.host_ip = host_ip
        self.telnet_user = telnet_user
        self.telnet_passwd = telnet_passwd
        self.ftp_user = ftp_user
        self.ftp_passwd = ftp_passwd
    
    def create_archive(self, source_dir: str, output_dir: str, archive_name: str) -> str:
        """Create tar archive from source directory"""
        output_path = None
        try:
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, archive_name)
            
            if os.path.exists(output_path):
                os.remove(output_path)
                
            with tarfile.open(output_path, "w") as tar:
                tar.add(source_dir, arcname=os.path.basename(source_dir))
                
            print(f"[TAR] Created archive: {output_path}")
        except Exception as e:
            print(f"[TAR] Error creating archive: {e}")
            if output_path and os.path.exists(output_path):
                os.remove(output_path)
                print(f"[CLEANUP] Removed failed archive: {output_path}")
        return output_path
    
    def upload_file(self, local_file: str) -> bool:
        """Upload file via FTP"""
        try:
            print(f"[FTP] Connecting to {self.host_ip} …")
            ftp = FTP(self.host_ip)
            ftp.login(self.ftp_user, self.ftp_passwd)
            print(f"[FTP] Logged in as {self.ftp_user}")
            
            ftp.voidcmd('TYPE I')
            ftp.cwd(self.remote_dir)
            print(">>", local_file)
            
            with open(local_file, 'rb') as file:
                print(">>", os.path.basename(local_file))
                ftp.storbinary('STOR functiongroupswitcher.tar', file)
            
            ftp.quit()
            print(f'File uploaded successfully: {local_file} -> {self.remote_dir}')
            
        except Exception as e:
            print(f'Error uploading file: {e}')
            return False
        return True
    
    def execute_remote_commands(self, fgs_transfer: bool) -> bool:
        """Execute remote commands via telnet"""
        tn = None
        try:
            print("Establishing connection...")
            tn = telnetlib.Telnet(self.host_ip, timeout=30)
            
            # Login sequence
            tn.read_until(b"login: ")
            print("Login prompt received.")
            tn.write(self.telnet_user.encode('ascii') + b"\n")
            print("Username sent.")
            
            tn.read_until(b"Password:")
            print("Password prompt received.")
            tn.write(self.telnet_passwd.encode('ascii') + b"\n")
            print("Password sent.")
            
            print("Waiting for shell prompt...")
            tn.read_until(b"# ")
            print("Shell prompt received.")
            
            # Execute commands
            self._execute_command(tn, f"cd {self.remote_dir}", "cwd completed.")
            self._execute_command(tn, f"rm -rf {self.remote_fgs_dir}", "Deletion completed.")
            
            if fgs_transfer:
                self._execute_command(tn, f"tar -xvf {self.remote_fgs_dir}.tar", "Extraction completed.")
                self._execute_command(tn, f"rm -rf {self.remote_fgs_dir}.tar", "Deletion completed.")
                self._execute_command(tn, f"chmod -R 777 {self.remote_fgs_dir}", "Permissions updated.")
                
                
        except Exception as e:
            print(f"Error during telnet session: {e}")
            return False
        finally:
            if tn:
                try:
                    print("Closing connection...")
                    tn.close()
                    print("Connection closed(memory terminal).")
                except Exception as e:
                    print(f"Failed to stop telnet session: {e}")
        return True
    
    def _execute_command(self, tn: telnetlib.Telnet, command: str, success_msg: str) -> None:
        """Execute single telnet command"""
        tn.write(f"{command}\n".encode('ascii'))
        tn.read_until(b"# ")
        print(success_msg)
    
    def control_rcar_relay(self) -> bool:
        """Control RCAR relay using usbrelay"""
        try:
            self.logger.info("Turning OFF relay...")
            subprocess.run(["usbrelay", "BITFT_1=0"])
            time.sleep(float(self.config.get('power-on-off-delay-in-seconds', 25)))
            
            self.logger.info("Turning ON relay...")
            subprocess.run(["usbrelay", "BITFT_1=1"])
            time.sleep(0.2)
            
        except Exception as e:
            self.logger.error(f"Error executing usbrelay commands: {e}")
            return False
        return True
    
    def control_power_relay(self) -> bool:
        """Control power relay via serial"""
        try:
            signal = serial.Serial(self.config['serial-port-relay'], self.config['baudrate-relay'], bytesize=8, stopbits=1, timeout=1)
            if not signal.is_open:
                self.logger.error(f"Failed to open serial port: {self.config['serial-port-relay']}")
                return False
            
            self.logger.info("Turning OFF relay...")
            signal.write("AT+CH1=0".encode())
            time.sleep(float(self.config.get('power-on-off-delay-in-seconds', 25)))
            
            self.logger.info("Turning ON relay...")
            signal.write("AT+CH1=1".encode())
            time.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"Failed to open serial port: {e}")
            return False
        
        return True
    
    def remote_fgs_transfer(self) -> bool:       
        if not self.config:
            print("Failed to load configuration")
            return False
        if not os.path.isdir(self.local_fgs_dir):
            print("functiongroupswitcher directory not found in current directory")
            return False
        try:
            
            local_archive = self.create_archive(
                source_dir=self.local_fgs_dir, 
                output_dir=self.temp_dir, 
                archive_name=self.archive_name
            )
            if not local_archive:
                print("Failed to create archive")
                return False
            
            if not self.upload_file(local_file=local_archive) or not self.execute_remote_commands(fgs_transfer=True):
                return False
        except Exception as e:
            print(f"Error during remote fgs transfer: {e}")
            return False
        finally:
            if os.path.isdir(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                print(f"[CLEANUP] Removed temporary directory: {self.temp_dir}")
        return True
        
    def remote_fgs_cleanup(self) -> bool:
        try:
            if not self.execute_remote_commands(fgs_transfer=False) or not self.control_power_relay():
                return False
            # if not self.control_rcar_relay():
            #     return False
        except Exception as e:
            print(f"Error during remote fgs cleanup: {e}")
            return False
        return True