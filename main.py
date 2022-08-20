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

        self.director_id = '33|'
        self.commence_code = '40000001'
        self.wipe_code = '40000005'
        self.wipe_code_2 = '40000014' # This might be a better wipe code.
        self.recommence_code = '40000006'
        self.victory_code = '40000003'
        self.instance_codes = [
            '800375A0',
            '800375A2',
            '8003759E',
            '8003759C'
        ]

        self.system_msg_id = '41|'
        self.door_code = 'B1C'
        self.instance_end_code = '5FE'

        # Use boss strings for damage indicating combat start.
        self.boss_strs = [
            'Erichthonios',
            'Hippokampos',
            'Phoinix',
            'Hesperos',
            'Hesperos'
        ]
        self.instance_strs = [
            'Asphodelos: The First Circle (Savage)',
            'Asphodelos: The Second Circle (Savage)',
            'Asphodelos: The Third Circle (Savage)',
            'Asphodelos: The Fourth Circle (Savage) Part 1',
            'Asphodelos: The Fourth Circle (Savage) Part 2'
        ]
        self.ignore_death_strs = [
            'Sunbird',
            'Darkened Fire',
            'Fountain of Fire'
        ]

    # ------------------------------------------------------------------------------
    # Instances.
    num_instances = [0, 0, 0, 0, 0]

    # Deaths - "Name": Count
    deaths = dict()

    # Pulls.
    pulls = []
    pull_cols = ['Instance',
                 'Clear',
                 'Start Time',
                 'End Time',
                 'Duration',
                 'Deaths']

    # Pull conditions.
    curr_instance = -1
    in_combat = False
    start_time = 0
    num_deaths = 0

    # ------------------------------------------------------------------------------
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

            # Add to the new filename list.
            filtered_filenames.append(filename)

        return filtered_filenames

    # --------------------------------------------------------------------------
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
                            print(f'{line[3:22]} - INSTANCE STARTED - {self.instance_strs[instance_num]}')
                            self.curr_instance = instance_num
                            self.num_instances[self.curr_instance] += 1
                            break

            # In instance.
            else:
                # Not yet in combat.
                if not self.in_combat:
                    # Check for combat start.
                    # Look for the damage network type ID.
                    # Look for the boss string.
                    if line[0:3] == self.dmg_id and line.find(self.boss_strs[instance_num]) != -1:
                        # print(f'{line[3:22]} - COMBAT STARTED - {self.boss_strs[instance_num]}')
                        self.in_combat = True
                        self.start_time = datetime.fromisoformat(line[3:22])

                # In combat.
                else:
                    # Check for wipe.
                    # Look for the director network type ID.
                    # Look for the wipe code.
                    if line[0:3] == self.director_id:
                        if line.find(self.wipe_code_2) != -1:
                            print(f'{line[3:22]} - WIPE')
                            end_time = datetime.fromisoformat(line[3:22])
                            delta_time = end_time - self.start_time
                            self.pulls.append((
                                self.curr_instance,
                                False,
                                str(self.start_time),
                                str(end_time),
                                str(delta_time),
                                self.num_deaths
                            ))
                            self.in_combat = False
                            self.num_deaths = 0
                        
                        # Check for clear.
                        # Look for the victory code.
                        elif line.find(self.victory_code) != -1:
                            print(f'{line[3:22]} - CLEAR')
                            end_time = datetime.fromisoformat(line[3:22])
                            delta_time = end_time - self.start_time
                            self.pulls.append((
                                self.curr_instance,
                                True,
                                str(self.start_time),
                                str(end_time),
                                str(delta_time),
                                self.num_deaths
                            ))
                            self.in_combat = False
                            self.num_deaths = 0

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
                        end_time = datetime.fromisoformat(line[3:22])
                        delta_time = end_time - self.start_time
                        self.pulls.append((
                            self.curr_instance,
                            True,
                            str(self.start_time),
                            str(end_time),
                            str(delta_time),
                            self.num_deaths
                        ))
                        self.in_combat = False
                        self.num_deaths = 0
                        self.curr_instance += 1

                # Check for instance end.
                # Look for system message type ID.
                # Look for instance end code.
                if line[0:3] == self.system_msg_id and \
                        line.find(self.instance_end_code) != -1:

                    # Check for inconsistent wipe.
                    if self.in_combat:
                        print('WARNING: UNCLEAR WIPE')
                        end_time = datetime.fromisoformat(line[3:22])
                        delta_time = end_time - self.start_time
                        self.pulls.append((
                            self.curr_instance,
                            False,
                            str(self.start_time),
                            str(end_time),
                            str(delta_time),
                            self.num_deaths
                        ))

                    print(f'{line[3:22]} - INSTANCE ENDED - {self.instance_strs[instance_num]}')
                    self.curr_instance = -1
                    self.in_combat = False
                    self.num_deaths = 0

        # Always close out combats and instances at the end of a log.
        if self.in_combat:
            print('WARNING: UNCLEAR COMBAT ENDED')
            self.in_combat = False
        if self.curr_instance != -1:
            print(f'????-??-??T??:??:?? - INSTANCE ENDED - {self.instance_strs[self.curr_instance]}')
            self.curr_instance = -1

    # --------------------------------------------------------------------------
    def process(self):
        filenames = self.get_filenames()

        # Loop per file.
        for filename in filenames:
            print(f'\n{filename}')
            filepath = os.path.join(self.log_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                self.parse_file(f)

        # Print per instance.
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
            print(f'clears: {clears.shape[0]}')
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


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    start = time.perf_counter()
    parser = ActParser()
    parser.process()
    stop = time.perf_counter()
    duration = stop - start
    print(f'\nDone in {str(timedelta(seconds=duration))}')
