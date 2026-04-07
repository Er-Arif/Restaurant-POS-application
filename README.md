# White-Label Offline Desktop Restaurant POS

Windows-first offline restaurant POS built with Python, PySide6, SQLite, SQLAlchemy, bcrypt, cryptography, `win32print`, and PyInstaller.

## Features

- Offline license activation tied to the local machine fingerprint
- Admin and staff roles with bcrypt password hashing
- Touch-friendly dine-in POS with one active ticket per table
- White-label restaurant branding and receipt footer configuration
- SQLite storage, CSV export, manual backup/restore, and receipt printing
- Per-order archived receipt text files in the runtime receipts folder

## Project Structure

```text
.
├── main.py
├── init_db.py
├── license_generator.py
├── requirements.txt
├── tests/
└── pos_system/
    ├── config/
    ├── controllers/
    ├── database/
    ├── license/
    ├── models/
    ├── services/
    ├── ui/
    └── utils/
```

## Setup

1. Create and activate a Python 3 virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Generate your commercial signing keys before packaging:

```bash
python license_generator.py init-keys --private-key vendor_keys/private_key.pem --public-key pos_system/license/public_key.pem
```

4. Initialize the database:

```bash
python init_db.py
```

5. Run the application:

```bash
python main.py
```

## Offline License Workflow

1. Launch the app and copy the hardware fingerprint shown on the activation screen.
2. Generate a license key offline:

```bash
python license_generator.py generate --private-key vendor_keys/private_key.pem --hardware-id <FINGERPRINT> --license-type trial --expiry-date 2026-12-31
```

3. Paste the generated license key into the activation screen.
4. Complete the setup wizard to create the first admin account and restaurant branding.

## Runtime Files

When running from source, runtime files are saved under `.runtime/`:

- Database: `.runtime/data/pos.db`
- License file: `.runtime/license/license.dat`
- Receipt preview: `.runtime/last_receipt.txt`
- Archived receipts: `.runtime/receipts/`
- CSV exports: `.runtime/exports/`
- Backups: `.runtime/backups/`

## Build Executable

```bash
pyinstaller --onefile --windowed main.py
```

When bundled with `--onefile`, the executable still stores runtime data outside the app binary in `%ProgramData%\CodexRetail\WhiteLabelPOS\`.

## Testing

```bash
python -m unittest discover -s tests
```

## Commercial Hardening Notes

- Keep `vendor_keys/private_key.pem` outside the deployed app.
- Rotate the public key before packaging a real customer build.
- Test printing with the target Windows receipt printer and installed driver.
- Back up `%ProgramData%\CodexRetail\WhiteLabelPOS\` regularly.
