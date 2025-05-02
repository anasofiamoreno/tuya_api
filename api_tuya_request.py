import base64
import json
import time
import hmac
import hashlib
import requests

# === Configuración ===
ACCESS_ID = "ACCESS_ID"
ACCESS_KEY = "ACCESS_KEY"
DEVICE_ID = "DEVICE_ID"
API_ENDPOINT = "https://openapi.tuyaus.com"


def generate_sign(message: str, secret: str) -> str:
    """Genera una firma HMAC-SHA256 en mayúsculas"""
    return hmac.new(secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256).hexdigest().upper()


def get_token():
    """Solicita un token válido desde Tuya"""
    timestamp = str(int(time.time() * 1000))
    message = ACCESS_ID + timestamp
    sign = generate_sign(message, ACCESS_KEY)

    headers = {
        "client_id": ACCESS_ID,
        "sign": sign,
        "t": timestamp,
        "sign_method": "HMAC-SHA256"
    }

    url = f"{API_ENDPOINT}/v1.0/token?grant_type=1"
    response = requests.get(url, headers=headers, timeout=10)
    data = response.json()

    if data.get("success"):
        print("✅ Token obtenido.")
        return {
            "token": data["result"]["access_token"],
            "timestamp": timestamp
        }
    else:
        raise Exception(f"❌ Error al obtener token: {data}")


def get_device_status(token: str, timestamp: str):
    """Consulta el estado actual del dispositivo"""
    message = ACCESS_ID + token + timestamp
    sign = generate_sign(message, ACCESS_KEY)

    headers = {
        "client_id": ACCESS_ID,
        "access_token": token,
        "sign": sign,
        "t": timestamp,
        "sign_method": "HMAC-SHA256"
    }

    url = f"{API_ENDPOINT}/v1.0/devices/{DEVICE_ID}/status"
    response = requests.get(url, headers=headers, timeout=10)
    data = response.json()

    if data.get("success"):
        voltage, current, active_power = decode_phase_a(data["result"][1]["value"])
        data["result"].extend([{ "code": "voltage", "value": voltage}, {"code": "current", "value": current},  {"code": "active_power", "value": active_power}])
        return data["result"]
    else:
        raise Exception(f"❌ Error al consultar estado del dispositivo: {data}")

def decode_phase_a(value_base64: str):
    decoded = base64.b64decode(value_base64)

    voltage_raw = int.from_bytes(decoded[13:15], 'big')
    current_raw = int.from_bytes(decoded[11:13], 'big')  # 0x019F = 415
    active_power_raw = int.from_bytes(decoded[2:4], 'big')  # 0x0043 = 67

    voltage = round(voltage_raw * 0.1, 1)
    current = round(current_raw * 0.001, 3)
    active_power = round(active_power_raw, 1)

    return voltage, current, active_power


if __name__ == "__main__":
    try:
        print("🔐 Solicitando token...")
        auth = get_token()

        print(f"\n📡 Consultando estado del dispositivo '{DEVICE_ID}'...")
        status = get_device_status(auth["token"], auth["timestamp"])
        print(status)

        result = {
            item['code']: item['value']
            for item in status
            if item['code'] in ['voltage', 'current', 'active_power', 'reactive_power', 'total_power', 'total_forward_energy', 'backward_energy', 'total_energy']
        }
        print(json.dumps(result, sort_keys=True))  # 🔥 esto es lo importante
    except Exception as e:
        print(json.dumps({"error": str(e)}))
