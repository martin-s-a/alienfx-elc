#!/usr/bin/env bash
# Install or update alienfx-elc system-wide. Run with sudo from the repo root.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "run with sudo" >&2
    exit 1
fi

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

rm -rf /usr/local/lib/alienfx-elc
install -d /usr/local/lib/alienfx-elc/alienfx_elc
install -m 0644 "$here"/alienfx_elc/*.py "$here"/alienfx_elc/default_config.toml /usr/local/lib/alienfx-elc/alienfx_elc/
install -m 0755 "$here/system/alienfx-elc" /usr/local/bin/alienfx-elc

install -d /etc/alienfx-elc
if [[ ! -e /etc/alienfx-elc/config.toml ]]; then
    install -m 0644 "$here/alienfx_elc/default_config.toml" /etc/alienfx-elc/config.toml
fi

install -m 0644 "$here/system/90-alienware-15r4-macro.hwdb" /etc/udev/hwdb.d/
systemd-hwdb update
udevadm trigger --subsystem-match=input --action=change

install -m 0755 "$here/system/alienfx-elc.sleep" /usr/lib/systemd/system-sleep/alienfx-elc
install -m 0644 "$here/system/alienfx-elc.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable alienfx-elc.service
systemctl restart alienfx-elc.service

echo "installed; config in /etc/alienfx-elc/config.toml"
