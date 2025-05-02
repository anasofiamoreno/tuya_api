import appdaemon.plugins.hass.hassapi as hass
import requests
import time
import hmac
import hashlib
import base64
import json
from datetime import timedelta

class TuyaMedidor(hass.Hass):

    def initialize(self):
        # Ejecuta cada 60 segundos
        self.run_every(self.actualizar_datos, self.datetime() + timedelta(seconds=5), 60)

    def generate_sign(self, message, secret):
        return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest().upper()

    def get_token(self, access_id, access_key):
        timestamp = str(int(time.time() * 1000))
        sign = self.generate_sign(access_id + timestamp, access_key)
        headers = {
            "client_id": access_id,
            "sign": sign,
            "t": timestamp,
            "sign_method": "HMAC-SHA256"
        }
        url = "https://openapi.tuyaus.com/v1.0/token?grant_type=1"
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        if data.get("success"):
            return data["result"]["access_token"], timestamp
        else:
            raise Exception(f"Error al obtener token: {data}")

    def get_device_status(self, token, timestamp, access_id, access_key, device_id):
        message = access_id + token + timestamp
        sign = self.generate_sign(message, access_key)
        headers = {
            "client_id": access_id,
            "access_token": token,
            "sign": sign,
            "t": timestamp,
            "sign_method": "HMAC-SHA256"
        }
        url = f"https://openapi.tuyaus.com/v1.0/devices/{device_id}/status"
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        result_dict = {item['code']: item['value'] for item in data.get('result', [])}
        if 'phase_a' in result_dict:
            voltage, current, active_power = self.decode_phase_a(result_dict['phase_a'])
            result_dict['voltage'] = voltage
            result_dict['current'] = current
            result_dict['active_power'] = active_power
        return result_dict

    def decode_phase_a(self, value_base64):
        decoded = base64.b64decode(value_base64)
        voltage_raw = int.from_bytes(decoded[13:15], 'big')
        current_raw = int.from_bytes(decoded[11:13], 'big')
        active_power_raw = int.from_bytes(decoded[2:4], 'big')
        voltage = round(voltage_raw * 0.1, 1)
        current = round(current_raw * 0.001, 3)
        active_power = round(active_power_raw, 1)
        return voltage, current, active_power

    def actualizar_datos(self, kwargs):
        aid = self.args.get("access_id")
        akey = self.args.get("access_key")
        did = self.args.get("device_id")
        nombre = self.args.get("nombre", did)

        try:
            token, timestamp = self.get_token(aid, akey)
            status = self.get_device_status(token, timestamp, aid, akey, did)

            keys = ['voltage', 'current', 'active_power', 'reactive_power',
                    'total_power', 'total_forward_energy', 'backward_energy', 'total_energy']

            for key in keys:
                if key in status:
                    state = status[key]
                    unit = ""
                    device_class = None
                    state_class = "measurement"

                    if key == "voltage":
                        unit = "V"
                        device_class = "voltage"
                    elif key == "current":
                        unit = "A"
                        device_class = "current"
                    elif key in ["active_power", "reactive_power", "total_power"]:
                        unit = "W"
                        device_class = "power"
                    elif key in ["total_forward_energy", "backward_energy", "total_energy"]:
                        state = round(state / 100, 2)
                        unit = "kWh"
                        device_class = "energy"
                        state_class = "total_increasing"

                    entity_id = f"sensor.{nombre}_{key}"
                    self.set_state(entity_id, state=state, attributes={
                        "unit_of_measurement": unit,
                        "device_class": device_class,
                        "state_class": state_class,
                        "friendly_name": f"{nombre.replace('_', ' ').title()} {key.replace('_', ' ').title()}"
                    })

        except Exception as e:
            self.log(f"❌ Error inesperado en '{nombre}': {e}")
