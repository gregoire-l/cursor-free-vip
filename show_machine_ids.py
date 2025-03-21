import os
import sys
import json
import platform
import sqlite3
from colorama import Fore, Style

# Import from reset_machine_manual
from reset_machine_manual import (
    get_config_paths,
    EMOJI
)

def show_machine_ids(translator):
    """Show all machine IDs and related information that would be modified by reset"""
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    # Get paths using helper functions
    try:
        # Get config paths for user data files
        storage_json_path, sqlite_path, local_machine_id_path = get_config_paths()
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.path_error', error=str(e))}{Style.RESET_ALL}")
        raise
    
    # Show file paths
    print(f"\n{Fore.CYAN}{EMOJI['FILE']} {translator.get('show_ids.file_paths')}:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. {translator.get('show_ids.config_path')}: {Style.RESET_ALL}{storage_json_path}")
    print(f"{Fore.GREEN}2. {translator.get('show_ids.sqlite_path')}: {Style.RESET_ALL}{sqlite_path}")
    print(f"{Fore.GREEN}3. {translator.get('show_ids.machine_id_path')}: {Style.RESET_ALL}{local_machine_id_path}")

    
    # Show JSON config IDs (from storage.json)
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.json_config_ids')}:{Style.RESET_ALL}")
        if os.path.exists(storage_json_path):
            with open(storage_json_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            # Show all relevant IDs that would be modified during reset
            machine_ids = {
                "telemetry.devDeviceId": config.get("telemetry.devDeviceId", ""),
                "telemetry.machineId": config.get("telemetry.machineId", ""),
                "telemetry.macMachineId": config.get("telemetry.macMachineId", ""),
                "telemetry.sqmId": config.get("telemetry.sqmId", ""),
                "storage.serviceMachineId": config.get("storage.serviceMachineId", "")
            }
            
            for key, value in machine_ids.items():
                print(f"{Fore.GREEN}{key}: {Style.RESET_ALL}{value}")
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.config_not_found')}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.json_error', error=str(e))}{Style.RESET_ALL}")
    
    # Show SQLite database IDs
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.sqlite_ids')}:{Style.RESET_ALL}")
        if os.path.exists(sqlite_path):
            conn = sqlite3.connect(sqlite_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Query all machine IDs in the database including new storage.serviceMachineId
                cursor.execute("SELECT key, value FROM ItemTable WHERE key LIKE '%machineId%' OR key LIKE '%telemetry%'")
                rows = cursor.fetchall()
                
                if rows:
                    for key, value in rows:
                        print(f"{Fore.GREEN}{key}: {Style.RESET_ALL}{value}")
                else:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('show_ids.no_sqlite_ids')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('show_ids.no_sqlite_table')}{Style.RESET_ALL}")
            
            conn.close()
        else:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.sqlite_not_found')}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.sqlite_error', error=str(e))}{Style.RESET_ALL}")
    
    # Show local machineId file content
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.machine_id_file')}:{Style.RESET_ALL}")
        if os.path.exists(local_machine_id_path):
            with open(local_machine_id_path, "r", encoding="utf-8") as f:
                machine_id = f.read().strip()
                print(f"{Fore.GREEN}{translator.get('show_ids.machine_id')}: {Style.RESET_ALL}{machine_id}")
        else:
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('show_ids.machine_id_not_found')}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.machine_id_error', error=str(e))}{Style.RESET_ALL}")
    
    # Show system-specific IDs
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.system_ids')}:{Style.RESET_ALL}")
        if platform.system() == "Windows":
            import winreg
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    "SOFTWARE\\Microsoft\\Cryptography",
                    0,
                    winreg.KEY_READ | winreg.KEY_WOW64_64KEY
                )
                machine_guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                winreg.CloseKey(key)
                print(f"{Fore.GREEN}Windows MachineGuid: {Style.RESET_ALL}{machine_guid}")
            except Exception as e:
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.windows_guid_error', error=str(e))}{Style.RESET_ALL}")
        elif platform.system() == "Darwin":
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('show_ids.macos_uuid_info')}{Style.RESET_ALL}")
        elif platform.system() == "Linux":
            # Check if /etc/machine-id exists
            machine_id_path = "/etc/machine-id"
            if os.path.exists(machine_id_path):
                try:
                    with open(machine_id_path, "r") as f:
                        machine_id = f.read().strip()
                    print(f"{Fore.GREEN}Linux machine-id: {Style.RESET_ALL}{machine_id}")
                except:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('show_ids.linux_machine_id_access')}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('show_ids.linux_uuid_info', os=platform.system())}{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.system_ids_error', error=str(e))}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('show_ids.press_enter')}...")

def run(translator=None):
    """Convenient function for directly calling the show_machine_ids function"""
    try:
        show_machine_ids(translator)
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('menu.error_occurred', error=str(e))}{Style.RESET_ALL}")