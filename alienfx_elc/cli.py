import argparse
import sys

from . import config as config_mod
from . import daemon, layout
from .elc import Elc, ElcError, HidrawTransport


def main(argv=None):
    parser = argparse.ArgumentParser(prog="alienfx-elc", description="Alienware 15 R4 lighting presets")
    parser.add_argument("--config", help="config file (default /etc/alienfx-elc/config.toml)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("info", help="show the controller's platform and firmware")
    apply_p = sub.add_parser("apply", help="show a preset once (its first look)")
    apply_p.add_argument("preset")
    sub.add_parser("save-default", help="store the startup preset in the controller's flash")
    sub.add_parser("daemon", help="run the key-driven service")
    args = parser.parse_args(argv)

    try:
        if args.command == "daemon":
            daemon.run(args.config)
            return 0
        cfg = config_mod.load(args.config)
        elc = Elc(HidrawTransport())
        if args.command == "info":
            info = elc.info()
            known = " (Alienware 15 R4)" if info["platform"] == layout.PLATFORM else " (unknown layout)"
            print(f"platform 0x{info['platform']:04x}{known}, {info['zones']} zones, firmware {info['firmware']}")
        elif args.command == "apply":
            if args.preset not in cfg.presets:
                parser.error(f"unknown preset {args.preset!r}; defined: {', '.join(cfg.presets)}")
            elc.play(cfg.presets[args.preset].frames[0])
        elif args.command == "save-default":
            elc.save_default(cfg.presets[cfg.startup].frames[0])
            print(f"saved preset {cfg.startup!r} as the controller's power-on lighting")
    except (ElcError, OSError, ValueError) as error:
        print(f"alienfx-elc: {error}", file=sys.stderr)
        return 1
    return 0
