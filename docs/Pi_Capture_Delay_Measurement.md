# Raspberry Pi sensor-to-laptop delay measurement

This project can measure one-way capture delay from the Raspberry Pi camera sensor to the laptop backend. The Pi publisher places two representations of the capture time into every frame before H.264 encoding:

- a readable UTC timestamp for visual confirmation;
- a small CRC-protected black/white marker that the backend decodes without OCR.

The timestamp comes from Picamera2 `SensorTimestamp`, which represents the start of sensor frame capture. The backend records the time at which OpenCV returns the decoded frame and reports:

`Capture → host = laptop decode time − Pi sensor capture time`

The stream overlay also reports `Sensor → stream`, measured immediately before the backend JPEG is sent to the browser. This does not include the browser's MJPEG decode and paint time.

## 1. Synchronize both clocks

One-way timestamps require the Pi and laptop clocks to agree. First check the time service already supplied by Raspberry Pi OS:

The repeatable repository setup is:

```bash
# Run once on the Ubuntu backend host.
sudo ./scripts/setup_host_time_server.sh --subnet 192.168.1.0/24

# Run on every Pi whenever it is added to the camera LAN.
sudo ./scripts/setup_pi_clock_sync.sh --server 192.168.1.100

# A later read-only health check needs no sudo.
./scripts/setup_pi_clock_sync.sh --check-only
```

```bash
timedatectl status
systemctl status systemd-timesyncd --no-pager
```

If `System clock synchronized` is `yes`, no Chrony installation is required. `systemd-timesyncd` and Chrony are alternatives; installing Chrony normally removes `systemd-timesyncd`.

If synchronization is disabled, enable the existing service:

```bash
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
timedatectl status
```

Chrony is optional if more detailed diagnostics are required. Install it only after confirming that internet access and DNS work:

```bash
sudo apt update
sudo apt install -y chrony
sudo systemctl enable --now chrony
chronyc waitsync 30 0.01
```

### Isolated camera network: use Ubuntu as the time server

In the deployed topology, the Windows machine is used for development, while the Ubuntu laptop at `192.168.1.100` runs the backend and MediaMTX. Capture delay is calculated using the Ubuntu backend clock, so each Pi should synchronize directly with Ubuntu. The Windows clock is not involved in that calculation.

On Ubuntu, install and configure Chrony as the LAN time server:

```bash
sudo apt update
sudo apt install -y chrony
sudo nano /etc/chrony/chrony.conf
```

Add this line to `chrony.conf`:

```text
allow 192.168.1.0/24
```

Then restart and verify it:

```bash
sudo systemctl enable --now chrony
sudo systemctl restart chrony
chronyc tracking
sudo ss -ulpn | grep ':123'
```

If Ubuntu's firewall is active, permit NTP from the camera subnet:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 123 proto udp
```

On each Pi, keep `systemd-timesyncd`; Chrony does not need to be installed. Edit its configuration:

```bash
sudo nano /etc/systemd/timesyncd.conf
```

Set:

```ini
[Time]
NTP=192.168.1.100
FallbackNTP=
```

Apply and verify:

```bash
sudo timedatectl set-ntp true
sudo systemctl restart systemd-timesyncd
sleep 15
timedatectl status
timedatectl timesync-status
```

Do not start the timestamped camera measurement until `System clock synchronized` reports `yes` on Ubuntu and every Pi.

Keep the laptop synchronized through Windows **Settings → Time & language → Date & time → Set time automatically → Sync now**. A clock offset directly becomes measurement error; for example, a 20 ms offset produces a 20 ms latency error.

## 2. Install Pi dependencies

Connect to the required Pi from the laptop. For example, picam7:

```bash
ssh <pi-username>@192.168.1.203
```

On Raspberry Pi OS Bookworm:

```bash
sudo apt update
sudo apt install -y git python3-picamera2 python3-opencv ffmpeg netcat-openbsd
```

### Temporarily connect a Pi to internet Wi-Fi

The deployed camera LAN can remain isolated. Internet access is only needed while provisioning or updating packages. Before changing networking over SSH, identify which interface currently carries the camera-LAN address:

```bash
ip -br address
ip route
nmcli device status
nmcli connection show --active
```

If `192.168.1.x` is assigned to `eth0`, SSH is using Ethernet and it is safe to connect the unused `wlan0` interface to an internet Wi-Fi network. If it is assigned to `wlan0`, changing Wi-Fi will terminate SSH; use a directly attached keyboard/display, or ensure the administration laptop is also on the destination Wi-Fi and can discover the Pi's new DHCP address.

Use an internet Wi-Fi or phone hotspot whose subnet is not `192.168.1.0/24`. Two active networks using the same subnet create ambiguous routes to the backend at `192.168.1.100`.

Set the WLAN country once using `sudo raspi-config`, under **Localisation Options -> WLAN Country**, and select the actual country. Then enable and scan Wi-Fi:

```bash
nmcli radio wifi
sudo nmcli radio wifi on
nmcli device wifi rescan
nmcli device wifi list
```

Connect without placing the password in shell history:

```bash
sudo nmcli --ask device wifi connect "<internet-ssid>"
```

Enter the Wi-Fi password when prompted. Verify routing, DNS, and HTTPS:

```bash
nmcli connection show --active
ip route
ping -c 3 1.1.1.1
getent hosts deb.debian.org
curl -I https://deb.debian.org
```

When those checks succeed, install the required packages:

```bash
sudo apt update
sudo apt install -y git python3-picamera2 python3-opencv ffmpeg
```

Record the original camera-network connection name before switching networks. After installation, restore it with:

```bash
sudo nmcli connection up "<original-camera-network-connection>"
```

If SSH was using `wlan0`, this command will disconnect the temporary session. Reconnect using the Pi's camera-LAN address. Confirm that the central device is reachable again:

```bash
ping -c 3 192.168.1.100
```

To prevent the temporary internet network from being selected automatically during deployment, disable autoconnection after returning to the camera LAN:

```bash
sudo nmcli connection modify "<internet-ssid>" connection.autoconnect no
```

Confirm that the camera and the local RTSP server are available:

```bash
rpicam-hello --list-cameras
nc -vz 192.168.1.100 8554
```

The network check should report that port `8554` succeeded. The script publishes to an RTSP server; it does not itself implement an RTSP server. In this deployment MediaMTX is at `192.168.1.100:8554`, not on the Pis. Therefore, do not use `127.0.0.1`: on a Pi that address means the Pi itself.

## 3. Clone and run

Clone the repository and enter it:

```bash
git clone <your-github-repository-url> FOD_Detection
cd FOD_Detection
git pull
```

For a private repository, configure an SSH key or use GitHub's supported authentication rather than placing a token in shell history. On later deployments, only `cd FOD_Detection && git pull` is needed.

Stop the previous camera publisher for the same MediaMTX path before starting this one. Two publishers cannot own the same RTSP path simultaneously. Each Pi must publish to a unique path on the central server:

| Pi | Pi address | Application ID | Publish URL | Backend read URL |
|---|---|---|---|---|
| picam7 | `192.168.1.203` | `camera_1` | `rtsp://192.168.1.100:8554/cam3` | `rtsp://192.168.1.100:8554/cam3` |
| picam9 | `192.168.1.204` | `camera_2` | `rtsp://192.168.1.100:8554/cam4` | `rtsp://192.168.1.100:8554/cam4` |
| picam11 | `192.168.1.205` | `camera_3` | `rtsp://192.168.1.100:8554/cam5` | `rtsp://192.168.1.100:8554/cam5` |

Run on picam7:

```bash
python3 scripts/pi_timestamped_rtsp.py \
  --camera-id camera_1 \
  --publish-url rtsp://192.168.1.100:8554/cam3 \
  --width 1280 --height 720 --fps 30 \
  --bitrate 4000000 --gop 15
```

Run on picam9:

```bash
python3 scripts/pi_timestamped_rtsp.py \
  --camera-id camera_2 \
  --publish-url rtsp://192.168.1.100:8554/cam4 \
  --width 1280 --height 720 --fps 30 \
  --bitrate 4000000 --gop 15
```

Run on picam11:

```bash
python3 scripts/pi_timestamped_rtsp.py \
  --camera-id camera_3 \
  --publish-url rtsp://192.168.1.100:8554/cam5 \
  --width 1280 --height 720 --fps 30 \
  --bitrate 4000000 --gop 15
```

The marker requires a width of at least 488 pixels. Press Ctrl+C to stop cleanly.

The publisher uses YUV420 and changes only the luma cells occupied by the
machine-readable marker. This avoids the RGB conversion path that previously
produced corrupt/choppy H.264 on some Raspberry Pi 5 Picamera2/PyAV package
combinations. It also publishes over RTSP/TCP with a 1200-byte RTP packet size.
Live validation on picam9 at 1280x720 and picam11 at 640x360 sustained about 30
timestamp updates per second without decoder errors.

The validated smooth live publisher is:

```bash
./scripts/pi_rpicam_rtsp.sh 192.168.1.100 cam4 1280 720 30 15
```

It publishes over RTSP/TCP with a 1200-byte RTP packet size and retries after a
relay restart. On the MediaMTX host, use a sufficiently large bounded outgoing
packet queue for 720p streams:

```yaml
writeQueueSize: 512
```

A queue of 32 packets caused slow-reader frame drops and visible H.264 corruption
at 1280x720. This hardware-camera publisher does not embed a source timestamp,
so use it only as a fallback when capture-to-host measurement is not required.

Configure the laptop project to read the same three paths:

```dotenv
CAMERA_1_SOURCE=rtsp://192.168.1.100:8554/cam3
CAMERA_2_SOURCE=rtsp://192.168.1.100:8554/cam4
CAMERA_3_SOURCE=rtsp://192.168.1.100:8554/cam5
```

If MediaMTX authentication is enabled, the Pi needs publisher credentials and the backend needs reader credentials. Put the appropriate credentials into the respective URLs; do not commit real passwords to Git.

## 4. View the measurement

Restart the laptop backend and frontend normally. The Performance panel will show:

- **Capture → host**: latest sensor-start-to-laptop-decode delay;
- **Avg capture → host**: rolling average over the latest 120 timestamped frames;
- **Camera 1/2/3 sensor → host**: latest delay from each Pi independently;
- **Model inference**: latest model execution time for that camera;
- **Total**: camera-to-host delay plus model inference time for that camera;
- **Latest frame age**: time since the backend received its newest frame;
- the video overlay **Sensor → stream**: sensor capture to backend MJPEG send time.

The status endpoint and Performance panel refresh once per second. The Pi marker
itself advances on every captured frame.

If the two capture-to-host values say **Unavailable**, check these in order:

1. the readable `PI CAP ... UTC` text appears in the video;
2. the correct `--camera-id` was used for that feed;
3. the video has not been cropped or resized before reaching the backend;
4. the Pi is running this publisher rather than the old publisher;
5. H.264 bitrate is not so low that it destroys the marker.

## Interpretation

This metric includes sensor exposure/readout, Pi processing, H.264 encoding, RTSP transport, laptop receive buffering, and H.264 decoding. It excludes inference and browser paint time. Compare the rolling average and a percentile distribution during a longer test; a single frame can be affected by keyframes, Wi-Fi retransmissions, and OS scheduling.
