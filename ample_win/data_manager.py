import plistlib
import os

class DataManager:
    def __init__(self, resources_path):
        self.resources_path = resources_path
        self.models = self.load_plist('models.plist')
        self.roms = self.load_plist('roms.plist')
        self.machine_cache = {}

    def load_plist(self, filename):
        path = os.path.join(self.resources_path, filename)
        if not os.path.exists(path):
            return None
        with open(path, 'rb') as f:
            return plistlib.load(f)

    def get_machine_description(self, machine_name):
        if machine_name in self.machine_cache:
            return self.machine_cache[machine_name]
        
        desc = self.load_plist(f'{machine_name}.plist')
        if desc:
            self.machine_cache[machine_name] = desc
        return desc

    def get_flat_machines(self, models=None):
        if models is None:
            models = self.models
        
        machines = []
        for model in models:
            if 'value' in model and model['value']:
                machines.append({
                    'name': model['value'],
                    'description': model.get('description', model['value'])
                })
            if 'children' in model:
                machines.extend(self.get_flat_machines(model['children']))
        return machines
