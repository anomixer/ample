import subprocess
import os
import re

class MameLauncher:
    def __init__(self):
        self.mame_path = "mame"
        self.working_dir = "."
        self.valid_slots_cache = {}

    def get_valid_slots(self, machine):
        if machine in self.valid_slots_cache:
            return self.valid_slots_cache[machine]
        
        # Check if the mame_path is actually a valid file or command
        if not os.path.exists(self.mame_path) and self.mame_path != "mame":
             print(f"MAME path not found: {self.mame_path}")
             return None

        try:
            # Query MAME for valid slots
            cmd = [self.mame_path, machine, "-listslots"]
            # Use shell=True or appropriate startupinfo if needed to hide console
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            slots = set()
            # MAME -listslots output format:
            # SLOT NAME        SLOT OPTIONS
            # sl1              ...
            # sl2              ...
            lines = result.stdout.splitlines()
            for line in lines:
                # Look for lines that start with some indentation then the slot name
                # or just use a simple split
                parts = line.split()
                if len(parts) >= 1:
                    # Slot names in MAME -listslots are usually in the second column or started after some spaces
                    # Actually, the format is:
                    # apple2p          gameio           ...
                    #                  sl0              ...
                    
                    # Pattern matching for slot names: they are the second or first word after machine name
                    match = re.search(r'^\s*(\w+)\s+', line)
                    if match:
                        slots.add(match.group(1))
                    elif machine in line:
                         parts = line.split()
                         if len(parts) >= 2:
                             slots.add(parts[1])
            
            # Special case for ramsize which is often an argument but not always in -listslots in the same way
            # In many drivers it's a slot, in others it's an option.
            # But MAME usually lists it.
            
            self.valid_slots_cache[machine] = slots
            return slots
        except Exception as e:
            print(f"Error getting slots for {machine}: {e}")
            return None

    def build_args(self, machine, slots=None, media=None, extra_options=None):
        args = [machine]
        args.append("-skip_gameinfo")
        
        valid_slots = self.get_valid_slots(machine)
        
        if slots:
            for slot_name, option in slots.items():
                if option:
                    # Validation: check if slot_name is recognized by MAME
                    # We also allow 'ramsize' as it's very common and might be an argument
                    if valid_slots is None or slot_name in valid_slots or slot_name == 'ramsize':
                        args.extend([f"-{slot_name}", option])
                    else:
                        print(f"Skipping invalid slot: {slot_name}")
        
        if media:
            for media_type, path in media.items():
                if path:
                    args.extend([f"-{media_type}", path])
                    
        if extra_options:
            for opt in extra_options:
                args.append(opt)
                
        return args

    def launch(self, machine, slots=None, media=None, extra_options=None):
        args = self.build_args(machine, slots, media, extra_options)
        cmd = [self.mame_path] + args
        print(f"Launching: {' '.join(cmd)}")
        try:
            subprocess.Popen(cmd, cwd=self.working_dir)
            return True
        except Exception as e:
            print(f"Error launching MAME: {e}")
            return False
