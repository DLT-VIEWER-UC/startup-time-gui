import os
import shutil
import threading
import json
from time import sleep
from Cyclic_Turnaround_Time_Scripts.Qnxopen import open_qnx
from pathlib import Path
from datetime import datetime
from Cyclic_Turnaround_Time_Scripts.KevfileGeneration import kevgeneration
from Cyclic_Turnaround_Time_Scripts.QNX import Qnx_Momentics_turnAround_cyclicTime

base_path = os.path.dirname(os.path.abspath(__file__))
cur_dir = Path(os.getcwd())
new_folder_path = None
log_files_folder_path = None

# Thread subclass that captures return value
class ResultThread(threading.Thread):
    def __init__(self, target, name=None):
        super().__init__(target=target, name=name)
        self.result = None

    def run(self):
        try:
            self.result = self._target()
        except Exception as e:
            print(f"Error in {self.name}: {e}")
            self.result = False

# Wrapper functions for threading
def check_kev_files(path):
    results = {}
    # Check if the provided paths exist and are directories
    if not os.path.exists(path) or not os.path.isdir(path):
        print("The provided path does not exist or is not a directory",path)
        return False
    else:
        # Check if there are any .kev files in the rcar directory
        kev_files = [file for file in os.listdir(path) if file.lower().endswith('.kev')]
        if kev_files:
            print("Found .kev file in Pre_KEV_Files folder", kev_files)
            return True
        else:
            print("KEV files missing or invalid. please upload valid kev file in path in ",path)
            return False  

def create_backup_folder(start_time):
    global new_folder_path, log_files_folder_path
    current_datetime = start_time.strftime("%Y-%m-%d_%H-%M-%S")
    cur_dir = Path.cwd()
    reports_folder_path = cur_dir / "Reports" / "04_Cyclic_and_Turnaround_Time"
    reports_folder_path.mkdir(parents=True, exist_ok=True)
 
    new_folder_path = reports_folder_path / current_datetime
    new_folder_path.mkdir(parents=True, exist_ok=True)
 
    log_files_folder_path = new_folder_path / "Log_Files"
    log_files_folder_path.mkdir(parents=True, exist_ok=True)
 
    return new_folder_path, log_files_folder_path          

def move_files_to_backup(log_files_folder_path, configuration):
    try:
        if configuration["GenerateKEVFile"]:
            return False  # Early exit if KEV generation is enabled

        pre_kev_folder = Path(base_path) / "Pre_KEV_Files"
        target_folder = log_files_folder_path / "Pre_KEV_Files"

        if not pre_kev_folder.exists():
            print("Pre_KEV_Files not found")
            return False

        shutil.copytree(pre_kev_folder, target_folder)
        print("Pre_KEV_Files Copied successfully")
        return True

    except Exception as e:
        print(f"Error Copying Pre_KEV_Files: {e}")
        return False

def run_kev_generation():
    return kevgeneration(log_files_folder_path)

def run_open_QNX_tool():
    return open_qnx()

def run_qnx_cyclicTime():
    return Qnx_Momentics_turnAround_cyclicTime(new_folder_path, log_files_folder_path)

def load_config(path='./Cyclic_Turnaround_Time_Scripts/cyclic_turnaround_config.json'):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (Exception, FileNotFoundError) as e:
        print(f"Config load error: {e}")
        return None
   
def load_config_sleep(path='./Cyclic_Turnaround_Time_Scripts/load_config_sleep.json'):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (Exception, FileNotFoundError) as e:
        print(f"Config load error: {e}")
        return None

def cyclic_turnaround_time_measurement():
    start_time = datetime.now()
    print(f"script start time starts{start_time}")
    configuration = load_config()
    if configuration is None:
        return False
   
    sleep_config = load_config_sleep()
    launching_momentics_tool = sleep_config["launching_momentics_tool"]
   
    new_folder_path, log_files_folder_path = create_backup_folder(start_time)

    if configuration["GenerateKEVFile"]:
        kev_thr = ResultThread(target=run_kev_generation, name='KevGen')
        kev_thr.start()
        kev_thr.join()

        if not kev_thr.result:
            print(" Kev generation failed — terminating script....")
            return False  
               
        open_thr = ResultThread(target=run_open_QNX_tool, name='OpenQNX')
        open_thr.start()
        open_thr.join()

        if not open_thr.result:
            print(" Failed to open QNX - terminating script.")
            return False
               
        sleep(launching_momentics_tool)
        os.chdir(cur_dir)

        qnx_thr = ResultThread(target=run_qnx_cyclicTime, name='RunQNXCyclic')
        qnx_thr.start()
        qnx_thr.join()

        if not qnx_thr.result:
            print(" QNX execution failed.")
            return False
       
        print("KEV file processed successfully.......")
        end_time = datetime.now()
        total_time = end_time - start_time
        print(f"Script Start time: {start_time}")
        print(f"Script END time: {end_time}")
        print(f"Total script execution time: {total_time}")
       
    else:        
        print("Skipping KEV generation as per configuration.")
        folder_path_for_Rcar = Path(base_path)/ 'Pre_KEV_Files' / 'RCAR'
        folder_path_for_SoC0 = Path(base_path) / 'Pre_KEV_Files' / 'SoC0'
        folder_path_for_SoC1 = Path(base_path)/ 'Pre_KEV_Files' / 'SoC1'

        if configuration["ECU_setting"]["Elite"]["RCAR"] or configuration["ECU_setting"]["PADAS"]["RCAR"] :
            result = check_kev_files(folder_path_for_Rcar)
            if not result:
                return False  
           
        if configuration["ECU_setting"]["Elite"]["SoC0"]:
            result = check_kev_files(folder_path_for_SoC0)
            if not result:
                return False
           
        if configuration["ECU_setting"]["Elite"]["SoC1"]:
            result = check_kev_files(folder_path_for_SoC1)
            if not result:
                return False

        open_thr = ResultThread(target=run_open_QNX_tool, name='OpenQNX')
        open_thr.start()
        open_thr.join()

        if not open_thr.result:
            move_files_to_backup(log_files_folder_path, configuration)
            print(" Failed to open QNX — terminating script..")
            return False

        os.chdir(cur_dir)
        qnx_thr = ResultThread(target=run_qnx_cyclicTime, name='RunQNXCyclic')
        qnx_thr.start()
        qnx_thr.join()

        if not qnx_thr.result:
            move_files_to_backup(log_files_folder_path, configuration)
            print(" QNX execution failed. Terminating script.")
            return False
       
        print(" All steps completed successfully.")
        end_time = datetime.now()
        total_time = end_time - start_time
        print(f"Script Start time: {start_time}")
        print(f"Script END time: {end_time}")
        print(f"Total script execution time: {total_time}")
       
    return move_files_to_backup(log_files_folder_path, configuration)