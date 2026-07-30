class IDMMCUInfo:
    def __init__(self, config):
        self.printer = config.get_printer()

    def get_status(self, eventtime):
        mcus = []
        for name, mcu in self.printer.lookup_objects(module='mcu'):
            serialport, baud = mcu._conn_helper.get_serialport()
            status = mcu.get_status(eventtime)
            constants = status.get('mcu_constants', {})
            model = next((str(constants[key]) for key in (
                'MCU', 'MCU_TYPE', 'CONFIG_MCU', 'CHIP', 'CHIP_TYPE'
            ) if constants.get(key)), '')
            mcus.append({
                'name': name,
                'uuid': serialport if not baud else '',
                'application': 'Klipper',
                'mcu_model': model,
                'mcu_version': status.get('mcu_version', ''),
            })
        return {'mcus': mcus}


def load_config(config):
    return IDMMCUInfo(config)
