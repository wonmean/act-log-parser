import os
import pandas as pd
import time
from datetime import datetime
from datetime import timedelta


class ActParser:
    def __init__(self):
        self.log_dir = f'{os.getenv("APPDATA")}\\Advanced Combat Tracker\\FFXIVLogs'

        # Codes.
        self.dmg_id = '21|'
        self.death_id = '25|'
        self.action_id = '20|'

        self.director_id = '33|'
        self.commence_code = '40000001'
        self.wipe_code = '40000005'
        self.wipe_code_2 = '40000013'
        self.wipe_code_3 = '40000014' # This might be a better wipe code for tier 1.
        self.recommence_code = '40000006'
        self.victory_code = '40000003'
        self.instance_codes = [
            '80037573'
        ]

        self.system_msg_id = '41|'
        self.door_code = 'B1C'
        self.instance_end_code = '5FE'

        # Use boss strings for damage indicating combat start.
        self.boss_strs = [
            'Garuda'
        ]
        self.phase_strs = [
            'Garuda',
            'Ifrit',
            'Titan',
            'Ultima'
        ]
        self.instance_strs = [
            'The Weapon\'s Refrain (Ultimate)'
        ]
        self.ignore_death_strs = [
            'Satin Plume',
            'Infernal Nail',
            'Granite Gaol',
            'Magitek Bit',
            'Aetheroplasm',
            'Spiny Plume',
            'Razor Plume',
            'Ultimaplasm',
            'Lightningstrike Death'
        ]
        self.num_instances = [0] * len(self.instance_strs)

    #-------------------------------------------------------------------------------
    # Instances.

    # Deaths - 'Name': Count
    deaths = dict()

    # Events.
    pulls = []
    pull_cols = ['Instance',
                 'Start Time',
                 'End Time',
                 'Duration',
                 'Deaths',
                 'Clear',
                 'Start Ifrit',
                 'Start Titan',
                 'Start Ultima']

    # Pull conditions.
    curr_instance = -1
    phase_index = -1
    start_time = datetime.now()
    end_time = datetime.now()
    delta_time = timedelta(seconds=0)
    num_deaths = 0
    start_ifrit = timedelta(seconds=0)
    start_titan = timedelta(seconds=0)
    start_ultima = timedelta(seconds=0)

    #-------------------------------------------------------------------------------
    # Get and filter filenames.
    def get_filenames(self):
        filenames = os.listdir(self.log_dir)
        filenames.sort()
        filtered_filenames = []
        for filename in filenames:
            # Get the full file path.
            filepath = os.path.join(self.log_dir, filename)

            # Ignore non-files.
            if not os.path.isfile(filepath):
                continue

            # Temp filter.
            # if 'Network_27001_20240406' not in filepath:
            #     continue

            # Add to the new filename list.
            filtered_filenames.append(filename)

        return filtered_filenames

    #---------------------------------------------------------------------------
    @staticmethod
    def get_time(line):
        return datetime.fromisoformat(line[3:22])

    #---------------------------------------------------------------------------
    def set_end_time(self, line):
        self.end_time = datetime.fromisoformat(line[3:22])
        self.delta_time = self.end_time - self.start_time

    #---------------------------------------------------------------------------
    def reset_combat(self):
        self.phase_index = -1
        self.start_time=datetime.now()
        self.end_time=datetime.now()
        self.num_deaths = 0
        self.start_ifrit=timedelta(seconds=0)
        self.start_titan=timedelta(seconds=0)
        self.start_ultima=timedelta(seconds=0)

    #---------------------------------------------------------------------------
    def add_pull(self, clear=False):
        self.pulls.append((
            self.curr_instance,
            str(self.start_time),
            str(self.end_time),
            str(self.delta_time),
            self.num_deaths,
            clear,
            str(self.start_ifrit),
            str(self.start_titan),
            str(self.start_ultima)
        ))

    #---------------------------------------------------------------------------
    def parse_file(self, f):
        for line in f:
            # Not yet in instance.
            if self.curr_instance == -1:
                # Check for instance start.
                # Look for the director network type ID.
                # Look for the appropriate instance codes.
                if line[0:3] == self.director_id:
                    for instance_num in range(len(self.instance_codes)):
                        if line.find(self.instance_codes[instance_num]) != -1:
                            print(f'{line[3:22]} - INSTANCE START - {self.instance_strs[instance_num]}')
                            self.curr_instance = instance_num
                            self.num_instances[self.curr_instance] += 1
                            break

            # In instance.
            else:
                # Not yet in combat.
                if self.phase_index == -1:
                    # Check for combat start.
                    # Look for the damage network type ID.
                    # Look for the boss string.
                    if line[0:3] == self.dmg_id and line.find(self.boss_strs[instance_num]) != -1:
                        print(f'{line[3:22]} - START - {self.boss_strs[instance_num]}')
                        self.phase_index += 1
                        self.start_time = self.get_time(line)

                # In combat.
                else:
                    # Check for wipe.
                    # Look for the director network type ID.
                    # Look for the wipe code.
                    if line[0:3] == self.director_id:
                        if line.find(self.wipe_code_2) != -1:
                            self.set_end_time(line)
                            print(f'{line[3:22]} - WIPE - {self.delta_time}')
                            self.add_pull()
                            self.reset_combat()

                        # Check for clear.
                        # Look for the victory code.
                        elif line.find(self.victory_code) != -1:
                            self.set_end_time(line)
                            print(f'{line[3:22]} - CLEAR - {self.delta_time}')
                            self.add_pull(True)
                            self.reset_combat()

                    # Check for death.
                    # Look for the death network type ID.
                    elif line[0:3] == self.death_id:
                        dead_person = line.split('|')[3]
                        if dead_person not in self.ignore_death_strs:
                            # print(f'{line[3:22]} - DEATH - {dead_person}')
                            self.deaths[dead_person] = self.deaths.get(dead_person, 0) + 1
                            self.num_deaths += 1

                    # Check for P4S door.
                    # Look for the system message type ID.
                    # Increment the current instance.
                    elif line[0:3] == self.system_msg_id and \
                            line.find(self.door_code) != -1:
                        print(f'{line[3:22]} - DOOR CLEAR')
                        self.set_end_time(line)
                        self.add_pull(True)
                        self.curr_instance += 1
                        self.reset_combat()
                    
                    # Check for phase changes.
                    # -1 = None
                    #  0 = Garuda
                    #  1 = Ifrit
                    #  2 = Titan
                    #  3 = Ultima
                    elif line[0:3] == self.action_id:
                        if self.phase_index < len(self.phase_strs) - 1:
                            next_phase_str = self.phase_strs[self.phase_index + 1]
                            if line.find(f'|{next_phase_str}|') != -1:
                                end_time = datetime.fromisoformat(line[3:22])
                                delta_time = end_time - self.start_time
                                if self.phase_index == 0:
                                    self.start_ifrit = delta_time
                                elif self.phase_index == 1:
                                    self.start_titan = delta_time
                                elif self.phase_index == 2:
                                    self.start_ultima = delta_time
                                print(f'{line[3:22]} - PHASE - {next_phase_str} - {delta_time}')
                                self.phase_index += 1

                # Check for instance end.
                # Look for system message type ID.
                # Look for instance end code.
                if line[0:3] == self.system_msg_id and \
                        line.find(self.instance_end_code) != -1:

                    # Check for inconsistent wipe.
                    if self.phase_index != -1:
                        print('WARNING: AMBIGUOUS WIPE')
                        self.set_end_time(line)
                        self.add_pull()

                    print(f'{line[3:22]} - INSTANCE END - {self.instance_strs[instance_num]}')
                    self.curr_instance = -1
                    self.reset_combat()

        # Always close out combats and instances at the end of a log.
        if self.phase_index != -1:
            print('WARNING: AMBIGUOUS WIPE')
            self.reset_combat()
        if self.curr_instance != -1:
            print(f'????-??-??T??:??:?? - INSTANCE END - {self.instance_strs[self.curr_instance]}')
            self.curr_instance = -1

    #---------------------------------------------------------------------------
    def process(self):
        filenames = self.get_filenames()

        # Loop per file.
        for filename in filenames:
            print(f'\n{filename}')
            filepath = os.path.join(self.log_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                self.parse_file(f)

        # Print per instance.
        # We include the first instance to give a time frame of when we started this content.
        pulls = pd.DataFrame(self.pulls, columns=self.pull_cols)
        print('')
        for instance_num in range(len(self.instance_strs)):
            instance = pulls[pulls['Instance'] == instance_num]
            instance = instance.reset_index(drop=True)
            clears = instance[(instance['Clear'] == True) | (instance.index == 0)]
            print(f'{self.instance_strs[instance_num]}')
            print(f'instances: {self.num_instances[instance_num]}')
            print(f'pulls: {instance.shape[0]}')
            print(f'wipes: {instance[instance["Clear"] == False].shape[0]}')
            print(f'clears: {clears.shape[0] - 1}')
            print(f'deaths: {instance["Deaths"].sum()}')
            print('')
            # print(instance)
            print(clears)
            print('')
        

        # Print deaths.
        deaths = pd.DataFrame.from_dict(self.deaths, orient='index', columns=['Deaths'])
        deaths_sorted = deaths.sort_values(by='Deaths', kind='mergesort', ascending=False)
        print(deaths_sorted)

        # Export
        pulls.sort_values(by='Instance', kind='mergesort').to_csv('pulls.csv')
        deaths_sorted.to_csv('deaths.csv')


#-------------------------------------------------------------------------------
if __name__ == '__main__':
    start = time.perf_counter()
    parser = ActParser()
    parser.process()
    stop = time.perf_counter()
    duration = stop - start
    print(f'\nDone in {str(timedelta(seconds=duration))}')
