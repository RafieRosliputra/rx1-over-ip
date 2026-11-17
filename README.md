# rx1-over-ip

Make a **DNP DS-RX1HS** dye-sub printer usable over the network with a cheap
Linux board (target: Orange Pi Zero 2; also fine on Raspberry Pi).

100% open source, no licences, no device limits. Two modes (one at a time):

| Mode | What it is | Best for |
|------|-----------|----------|
| `printmode cups` | **Print server**: CUPS + Gutenprint + HTTP API | Any device, QR booth / website, hot folder |
| `printmode usb`  | **USB extension**: USB/IP, the printer appears on your computer as if plugged in | Using the official DNP driver on your own computer |

```
cups:  Mac/Windows/phone --IPP--> Pi --USB--> RX1HS     Website --HTTP--> Pi
usb :  Mac/Windows/Linux <--USB/IP over network--> Pi --USB--> RX1HS
```

## Install (on the board)

1. Flash Armbian/Debian, connect WiFi (`sudo nmtui`).
2. Plug in the RX1HS and switch it on.
3. `git clone <this repo> && cd rx1-over-ip && sudo bash install.sh`

## Mode 1: print server (default)

Add `ipp://<pi-ip>:631/printers/DNP-RX1HS` in macOS / Windows / Android printer settings, or use the API:

```bash
curl -H "Authorization: Bearer $TOKEN" --data-binary @photo.jpg \
  "http://orangepi.local:8080/print?layout=4x6&copies=1"
```

| layout  | result                                               |
|---------|------------------------------------------------------|
| `4x6`   | photo fills one 4x6" print (auto-rotated, cropped)   |
| `strip` | two identical 2x6" strips on one 4x6" print (cut it) |

`GET /health` = printer status. macOS hot folder: `./mac/hotfolder.sh ~/Desktop/hotfolder orangepi.local 4x6`.
Config: `/etc/default/rx1print` (`RX1_TOKEN` recommended, `RX1_MEDIA`, ...).

## Mode 2: USB extension (USB/IP)

On the Pi: `sudo printmode usb` (auto-finds the RX1; or `printmode usb <busid>` from `usbip list -l`).

On your computer, attach it (port 3240):

- **Linux**: `sudo usbip attach -r <pi-ip> -b <busid>` (kernel `vhci-hcd`)
- **Windows**: a USB/IP client such as [usbip-win2](https://github.com/vadimgrn/usbip-win2) (not tested here)
- **macOS**: no built-in client. The experimental [sing-usbip](https://pkg.go.dev/github.com/sagernet/sing-usbip) project lists a macOS client; not tested here

Then install DNP's official driver on that computer and print normally.
Back to print server: `sudo printmode cups`.

Requirements: the Pi kernel needs `usbip-host` (`CONFIG_USBIP_HOST`). `install.sh` warns if it is missing; a few board kernels lack it.

## Notes

- Gutenprint colours differ slightly from DNP's official driver (mode 1).
- If the printer isn't auto-detected, check `lpinfo -v` and `lpinfo -m | grep -i rx1`, add it at `http://<pi>:631`.
- Prefer LAN over WiFi at events. USB/IP is sensitive to latency.
- Put the API behind a token before exposing it beyond your LAN.

## License

MIT
