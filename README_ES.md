# ⚡ Integración de medidores TOMZN DDS238-1-W1 en Home Assistant con AppDaemon

Este proyecto muestra cómo integrar medidores inteligentes TOMZN DDS238-1-W1 conectados a la API de Tuya con Home Assistant mediante AppDaemon, permitiendo una representación clara de sensores eléctricos como voltaje, corriente, potencia activa, energía consumida y energía exportada.

---

## 📐 Requisitos

* Home Assistant OS
* AppDaemon instalado (como complemento oficial)
* Una cuenta y proyecto en [Tuya IoT Platform](https://iot.tuya.com)
* Acceso al `Access ID`, `Access Key` y `Device ID` de tu medidor
* Un medidor TOMZN DDS238-1-W1 correctamente vinculado a Tuya Smart o Smart Life

---

## 🧠 ¿Qué hace este proyecto?

1. Consulta periódica a la API de Tuya cada 60 segundos para obtener el estado del medidor.
2. Decodifica los datos `phase_a` en Base64 para extraer:

   * Voltaje (V)
   * Corriente (A)
   * Potencia activa (W)
3. Publica los sensores como entidades en Home Assistant:

   * Sensor de voltaje, corriente, potencia activa
   * Energía total consumida, energía exportada, etc.
4. Integra los sensores al panel de energía de Home Assistant con los atributos requeridos (`state_class`, `device_class`, `unit_of_measurement`).

---

## 📁 Archivos clave

### apps.yaml

```yaml
tuya_medidor_l1:
  module: medidor_centro_carga
  class: TuyaMedidor
  access_id: !secret tuya_access_id
  access_key: !secret tuya_access_key
  device_id: eb244fcdfc27bae2181xyj
  nombre: centro_carga_l1

tuya_medidor_l2:
  module: medidor_centro_carga
  class: TuyaMedidor
  access_id: !secret tuya_access_id
  access_key: !secret tuya_access_key
  device_id: eb0b07db3da85b990bvxqh
  nombre: centro_carga_l2
```

### medidor\_centro\_carga.py

Archivo principal que hace el request a Tuya, decodifica `phase_a` y publica sensores personalizados.

---

## 📦 Decodificación del datapoint `phase_a`

El campo `phase_a` es una cadena en Base64 que representa una secuencia de bytes codificados por el medidor TOMZN DDS238-1-W1. Esta contiene información cruda de voltaje, corriente y potencia activa.

### Ejemplo de valor:

```
"phase_a": "AAAB0AAAADsDgAAPpgUN"
```

Al hacer `base64.b64decode(...)`, se obtiene un arreglo de 15 bytes:

```python
b'\x00\x00\x01\xdd\x00\x00\x00;\x03\x82\x00\x0F\xa6\x05\r'
```

### 📊 Decodificación por bytes

| Bytes (offset) | Función             | Descripción técnica                       | Conversión                               |
| -------------- | ------------------- | ----------------------------------------- | ---------------------------------------- |
| `2:4`          | Potencia activa (W) | Potencia activa en vatios (sin escalar)   | `int.from_bytes(b[2:4], 'big')`          |
| `11:13`        | Corriente (A)       | Corriente RMS en Amperes (escalado ÷1000) | `int.from_bytes(b[11:13], 'big') / 1000` |
| `13:15`        | Voltaje (V)         | Voltaje RMS en Voltios (escalado ×0.1)    | `int.from_bytes(b[13:15], 'big') * 0.1`  |

### 📌 Código de ejemplo:

```python
decoded = base64.b64decode(value_base64)

active_power = int.from_bytes(decoded[2:4], 'big')
current = int.from_bytes(decoded[11:13], 'big') / 1000
voltage = int.from_bytes(decoded[13:15], 'big') * 0.1
```

---

## ✅ Ventajas de este enfoque

* Compatible con medidores Tuya sin usar integraciones nativas inestables
* Totalmente personalizable desde AppDaemon
* Sensores separados para voltaje, corriente, potencia y energía
* Compatible con el panel de energía de Home Assistant

---

## 📌 Créditos

Desarrollado y probado por [Ana Sofia Moreno](https://chat.openai.com) usando Home Assistant OS + AppDaemon + Medidor TOMZN DDS238-1-W1. Comparte y mejora esta solución si te fue útil.
