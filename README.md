# rx1-wireless-print

Make a **DNP DS-RX1HS** dye-sub printer print over the network using a cheap
Linux board (tested target: Orange Pi Zero 2, also fine on Raspberry Pi).

100% open source stack: **CUPS + Gutenprint** + a tiny HTTP API (`rx1print`).

```
Mac / Windows / phone ──IPP──┐
Website / photobooth ──HTTP──┤──> Orange Pi ──USB──> DNP RX1HS
Mac hot folder ──────HTTP────┘     (CUPS + rx1print)
```

## Install (on the board)

1. Flash Armbian/Debian, connect WiFi (`sudo nmtui`).
2. Plug in the RX1HS and switch it on.
3. `git clone <this repo> && cd rx1-wireless-print && sudo bash install.sh`

## Use

**As a network printer (IPP)** – add `ipp://<pi-ip>:631/printers/DNP-RX1HS`
in macOS / Windows / Android printer settings.

**From code (HTTP API)** – send the raw image bytes:

```bash
curl -H "Authorization: Bearer $TOKEN" --data-binary @photo.jpg \
  "http://orangepi.local:8080/print?layout=4x6&copies=1"
```

| layout  | result                                               |
|---------|------------------------------------------------------|
| `4x6`   | photo fills one 4x6" print (auto-rotated, cropped)   |
| `strip` | two identical 2x6" strips on one 4x6" print (cut it) |

`GET /health` returns the CUPS printer status.

**macOS hot folder** – `./mac/hotfolder.sh ~/Desktop/hotfolder orangepi.local 4x6`

## Config

`/etc/default/rx1print` – printer name, port, `RX1_TOKEN` (recommended),
`RX1_MEDIA`, max copies. Restart with `sudo systemctl restart rx1print`.

## Notes

- Gutenprint colours differ slightly from DNP's official driver.
- If the printer/driver isn't auto-detected, run `lpinfo -v` and `lpinfo -m | grep -i rx1`
  and add it at `http://<pi>:631`.
- Use LAN instead of WiFi for events if you can.
- Put the API behind a token before exposing it beyond your LAN.

## License

MIT
