class BatteryType:
    required_fields = ['chemical_type_cathode', 'content_object', 'specific_type', 'supplier', 'theoretical_capacity']
    additional_fields = ['cathode_proportions']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields


class Battery:
    required_fields = ['weight', 'vmin', 'vmax', 'private', 'owner']
    additional_fields = ['chemical_type_anode', 'anode_proportions', 'vnom', 'comments']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields


class Dataset:
    required_fields = ['name', 'organisation']
    additional_fields = ['license', 'authors', 'owner', 'url', 'doi']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields


class CellTest:
    required_fields = ['battery', 'date', 'dataset', 'file']
    additional_fields = ['equipment']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields


class CyclingTest:
    required_fields = ['cellTest']
    additional_fields = ['cycle_offset', 'comments']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields


class AggData:
    required_fields = ['cycling_test', 'cycle_id', 'start_time', 'end_time', 'min_voltage', 'max_voltage']
    additional_fields = ['charge_capacity', 'discharge_capacity', 'efficiency', 'charge_c_rate', 'discharge_c_rate', 'ambient_temperature', 'error_codes']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields


class CyclingRawData:
    required_fields = ['agg_data', 'voltage', 'cycle_id', 'step_flag', 'current', 'capacity', 'energy', 'time']  # todo why time_in_step is req? 'time_in_step',
    additional_fields = ['cell_temperature', 'ambient_temperature']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields


class HPPCRawData:
    required_fields = ['agg_data', 'voltage', 'cycle_id', 'step_flag', 'current', 'time']
    additional_fields = ['cell_temperature', 'ambient_temperature', 'capacity', 'energy']

    def allowed_fields(self):
        return self.required_fields + self.additional_fields
