class StepNameMap:
    def __init__(self, name_map: dict = None):

        if name_map is None:
            self.name_map = {1: "CC_Chg",
                             2: "CC_Dchg",
                             4: "Rest",
                             5: "Cycle",
                             7: "CCCV_Chg"}

            # TODO: 3, 6

    def get_step_name(self, s):
        if s in self.name_map:
            return self.name_map[s]
        else:
            str(s)


EIS_TAG_MAPS = {
    'gamry': {
        'Freq': 'frequency',
        'Zreal': 'z_real',
        'Zimag': 'z_im',
        'Vdc': 'voltage',
        'Temp': 'temperature'
    }
}
