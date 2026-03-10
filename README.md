# digitalSTROM Smart for Home Assistant

[![HACS Badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/wooniot/ha-digitalstrom-smart)](https://github.com/wooniot/ha-digitalstrom-smart/releases)

A zone-based, event-driven Home Assistant integration for **digitalSTROM** home automation systems. Built by [Woon IoT BV](https://wooniot.nl) - digitalSTROM installation specialists.

## Why this integration?

Unlike traditional per-device polling integrations, digitalSTROM Smart uses the **scene-based architecture** that digitalSTROM was designed for:

| | Traditional approach | digitalSTROM Smart |
|--|---------------------|-------------------|
| **Control method** | Individual device commands | Zone scenes (one command, all devices respond) |
| **State updates** | Polling every 10-30s per device | Real-time event subscription |
| **Bus load** | ~50+ requests/min (10 zones) | ~0.4 requests/min + 1 event connection |
| **Risk** | Can corrupt apartments.xml | Safe - uses only standard API calls |

## Features

- **Zone-based lights** with brightness control
- **Zone-based covers** (blinds/shades) with position control
- **Scene activation** (the recommended way to control digitalSTROM)
- **Temperature sensors** per zone
- **Energy monitoring** (apartment-level power consumption)
- **Pause/Resume** switch for safe dS Configurator use
- **Event-driven** - instant state updates when someone uses a wall switch
- **Local and Cloud** connection support

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Search for "digitalSTROM Smart"
3. Click Install
4. Restart Home Assistant

### Manual

1. Download the latest release from [GitHub](https://github.com/wooniot/ha-digitalstrom-smart/releases)
2. Copy `custom_components/digitalstrom_smart/` to your HA config directory
3. Restart Home Assistant

## Configuration

1. Go to **Settings > Devices & Services > Add Integration**
2. Search for "digitalSTROM Smart"
3. Choose **Local** (IP address) or **Cloud** (*.digitalstrom.net)
4. For local: enter dSS IP and port, then press the **meter button** on your dSS to approve
5. For cloud: enter your digitalstrom.net URL and credentials

## Entities created

For each zone with devices:
- `light.<zone>_light` - Zone light control (on/off/brightness)
- `cover.<zone>_cover` - Zone cover control (open/close/position) - only if shade devices present
- `scene.<zone>_scene_1` through `scene_4` - Activate dS presets
- `sensor.<zone>_temperature` - Zone temperature (if available)

Apartment-level:
- `sensor.dss_power_consumption` - Total power (Watts)
- `switch.dss_pause_communication` - Pause for dS Configurator

## Services

- `digitalstrom_smart.call_scene` - Activate a scene (zone_id, group, scene_number)
- `digitalstrom_smart.pause` - Pause all dSS communication
- `digitalstrom_smart.resume` - Resume communication

## Using the Pause switch

When you need to use the **dS Configurator** to modify your installation:
1. Turn ON the Pause switch - all dSS communication stops
2. Use dS Configurator freely
3. Turn OFF the Pause switch - the integration reconnects and resyncs

## Compatibility

- **dSS firmware**: 1.19.x and newer
- **Home Assistant**: 2024.1.0 and newer
- **Connection**: Local (HTTPS, port 8080) or Cloud (*.digitalstrom.net)

## About

Developed by **[Woon IoT BV](https://wooniot.nl)** - professional digitalSTROM installers and smart home specialists based in the Netherlands.

- Website: [wooniot.nl](https://wooniot.nl)
- Issues: [GitHub Issues](https://github.com/wooniot/ha-digitalstrom-smart/issues)
- License: MIT
