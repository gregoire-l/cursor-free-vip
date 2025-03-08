import os
import sys
import json
import platform
import sqlite3
from colorama import Fore, Style

# Import from reset_machine_manual
from reset_machine_manual import (
    get_cursor_machine_id_path,
    get_workbench_cursor_path,
    MachineIDResetter,
    EMOJI
)

def show_machine_ids(translator):
    """Show all machine IDs and related information that would be modified by reset"""
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    
    # Get paths using MachineIDResetter
    try:
        resetter = MachineIDResetter(translator)
        db_path = resetter.db_path
        sql_path = resetter.sqlite_path
        machine_id_path = get_cursor_machine_id_path(translator)
        workbench_path = get_workbench_cursor_path(translator)
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('show_ids.path_error', error=str(e))}{Style.RESET_ALL}")
        raise
    
    # Show file paths
    print(f"\n{Fore.CYAN}{EMOJI['FILE']} {translator.get('show_ids.file_paths')}:{Style.RESET_ALL}")
    print(f"{Fore.GREEN}1. {translator.get('show_ids.config_path')}: {Style.RESET_ALL}{db_path}")
    print(f"{Fore.GREEN}2. {translator.get('show_ids.sqlite_path')}: {Style.RESET_ALL}{sql_path}")
    print(f"{Fore.GREEN}3. {translator.get('show_ids.machine_id_path')}: {Style.RESET_ALL}{machine_id_path}")
    print(f"{Fore.GREEN}4. {translator.get('show_ids.workbench_path')}: {Style.RESET_ALL}{workbench_path}")
    
    # Show JSON config IDs
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.json_config_ids')}:{Style.RESET_ALL}")
        if os.path.exists(db_path):
            with open(db_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
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
        if os.path.exists(sql_path):
            conn = sqlite3.connect(sql_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ItemTable'")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Query all machine IDs in the database
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
    
    # Show machineId file content
    try:
        print(f"\n{Fore.CYAN}{EMOJI['INFO']} {translator.get('show_ids.machine_id_file')}:{Style.RESET_ALL}")
        if os.path.exists(machine_id_path):
            with open(machine_id_path, "r", encoding="utf-8") as f:
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