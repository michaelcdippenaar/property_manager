# Klikk tenant (Flutter)

Tenant mobile app for the Tremly / Klikk property manager stack.

## Run (simulator — default API URLs)

From this directory:

```bash
flutter pub get
flutter devices
flutter run
```

- **iOS Simulator** uses `http://127.0.0.1:8000/api/v1` (Django on your Mac).
- **Android Emulator** uses `http://10.0.2.2:8000/api/v1`.

Start the API first:

```bash
cd ../backend && source .venv/bin/activate && python manage.py runserver
```

## Run on a **physical phone** (“could not reach the server”)

On a real device, `localhost` / `127.0.0.1` / `10.0.2.2` point at the **phone**, not your Mac.

1. Put the **phone and Mac on the same Wi‑Fi** (no client isolation).
2. Find your **Mac’s LAN IP** (e.g. System Settings → Network, or `ipconfig getifaddr en0`).
3. **Bind Django** so the phone can reach it:
   ```bash
   cd ../backend && source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000
   ```
4. **ALLOWED_HOSTS** must include that IP. In `.env` (see [`../backend/.env.example`](../backend/.env.example)):
   ```env
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.x.x
   ```
   Replace `192.168.x.x` with your Mac’s IP.
5. **Run Flutter** with an explicit API base (replace the IP):
   ```bash
   flutter run --dart-define=API_BASE_URL=http://192.168.x.x:8000/api/v1
   ```
6. If it still fails: allow **TCP 8000** through the Mac firewall.

**iOS:** The app enables **local-network HTTP** via `NSAllowsLocalNetworking` in `ios/Runner/Info.plist` for dev.

## Configuration

| `API_BASE_URL` | When |
|----------------|------|
| *(unset)* | Simulator / emulator defaults ([`lib/config/api_config.dart`](lib/config/api_config.dart)) |
| `http://<mac-ip>:8000/api/v1` | Physical iPhone or Android device |
