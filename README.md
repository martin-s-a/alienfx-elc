# alienfx-elc

Lighting presets for the Alienware 15 R4, switched from its macro keys.

The laptop's lights (keyboard, macro keys, touchpad, logos, side strips) hang
off an AW-ELC controller (USB `187c:0550`, platform `0x0104`). This talks to it
directly over hidraw, with no OpenRGB and no dependencies beyond Python 3.11+.

## Install

```bash
sudo ./install.sh
```

It installs:

- `/usr/local/bin/alienfx-elc` and its package in `/usr/local/lib/alienfx-elc`
- `/etc/alienfx-elc/config.toml`, the presets (kept on reinstall)
- `alienfx-elc.service`, which reads the keyboard and switches presets
- a hwdb rule that gives the unnumbered macro key a keycode (`macro_preset_cycle`)
- a systemd-sleep hook that puts the current look back after resume

The service runs as root because it reads the keyboard. Adding your user to
the `input` group instead would let every program you run read your keystrokes.

## Keys

| key | default preset |
|---|---|
| unnumbered key above macro 1 | `default`: everything off |
| macro 1 | `night`: dim white keyboard |
| macro 2 | `brightness`: each press steps the keyboard 25 → 50 → 75 → 100 % |
| macro 3 | `auto`: keyboard lights while typing, off after 10 s idle |
| macro 4, 5 | free |

Edit `/etc/alienfx-elc/config.toml`, then `sudo systemctl reload alienfx-elc`.

## Power-on lighting

The controller plays its own animation from power-on until the service starts.
To start dark from the firmware on:

```bash
alienfx-elc save-default
```

This writes the `startup` preset into the controller's flash, as OpenRGB's
"save to device" does. Saving another preset replaces it.

## The power button

The firmware drives the power button with its own power-state animation. A
preset that also paints it makes the two alternate, so the button blinks.
Presets leave it alone unless they name `power_button`.

## Zone map (platform 0x0104)

| id | zone |
|---|---|
| 0x00 | alien head on the lid |
| 0x01 | ALIENWARE wordmark |
| 0x02 | touchpad |
| 0x03 | power button |
| 0x04–0x07 | keyboard, right to left |
| 0x08 / 0x09 | base strip, left / right |
| 0x0a / 0x0b | lid strip, left / right |
| 0x0c | macro keys |
| 0x0d | reported by the controller, no visible light |

## Tests

```bash
python3 -m unittest discover -s tests
```
