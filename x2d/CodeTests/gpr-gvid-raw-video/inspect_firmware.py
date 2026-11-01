"""只读核对 X2D 4.2.0 视频 RAW 候选：不加载固件、不连接设备。"""

import argparse
import configparser
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

# Reuse the repository's standard-library-only ELF/APS2 reader.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pdaf-only-shadow"))
from native_afs_parameters import LockedElf

INPUTS = {
    "etc/imx461bqr_ec1706.conf": "e9eeb3630b1eef7a486957c0c2b7fc4e33f2288fd5955a09d2aa0866d9cfd700",
    "etc/imx461bqr_ec1706.sp": "a75a3195e21600c4e42d17c331f6add445dbbecb72dd2cd12aa1ad46d0034acb",
    "lib64/camera/plugins/hal/libdcam_cam_info_e2_ec1706_native.so": "c506acbe4ae2d65aef1bfd6752a26a95fd91a8456cc54da85e47c731540ee245",
    "lib64/librcam.so": "72ebc8deebce4a29047c475e77ab4edbf2860abb1f572fea45260fe17ad0bda5",
    "lib64/libdcam_frwk.so": "6d26f038175fc736dfc3e6b67c93f2d997895014be8e5c3040654cfb26bb501e",
}


class CameraElf(LockedElf):
    def pointer(self, address):
        matches = [r for r in self.relocations if r[0] == address]
        if len(matches) != 1:
            raise ValueError("expected one relocation for reviewed pointer")
        _, info, addend = matches[0]
        kind, symbol = info & 0xFFFFFFFF, info >> 32
        if kind == 1027 and symbol == 0:
            return addend
        if kind in (257, 1025):
            target = self.dynamic[symbol]
            if not target["section"]:
                raise ValueError("pointer needs external runtime resolution")
            return target["value"] + addend
        raise ValueError("unsupported reviewed pointer relocation")

    def text(self, address, limit=128):
        data = bytearray()
        for i in range(limit):
            value = self.read(address + i, 1)
            if value == b"\0":
                return data.decode("ascii")
            data.extend(value)
        raise ValueError("unterminated reviewed name")

    def check(self, words):
        for address, word in words.items():
            if struct.unpack("<I", self.read(address, 4))[0] != word:
                raise ValueError("reviewed consumer instruction differs")


def audit(system_root):
    root = Path(system_root).resolve(strict=True)
    data = {}
    for relative, expected in INPUTS.items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError("input escapes supplied system root")
        data[relative] = path.read_bytes()
        if hashlib.sha256(data[relative]).hexdigest() != expected:
            raise ValueError("requires exact X2D 4.2.0 input: " + relative)

    def elf(relative):
        cls = type(
            "PinnedCameraElf", (CameraElf,), {"EXPECTED_SHA256": INPUTS[relative]}
        )
        return cls(data[relative])

    hal = elf("lib64/camera/plugins/hal/libdcam_cam_info_e2_ec1706_native.so")
    driver = elf("lib64/librcam.so")
    framework = elf("lib64/libdcam_frwk.so")
    hal.check(
        {
            0x3C18: 0x52800B08,
            0x3C20: 0x91164129,
            0x3C2C: 0xF9400D08,
            0x3C30: 0xB9400508,
            0x3F6C: 0x912B4129,
            0x3F70: 0x52800B0A,
            0x3F7C: 0x9116416B,
        }
    )
    driver.check(
        {
            0xEBD44: 0x5280049C,
            0xEBDB4: 0x91014318,
            0xEBDC0: 0xF138431F,
            0xEBDE8: 0xF9400668,
            0xEBDFC: 0x79403EE9,
        }
    )
    framework.check(
        {
            0x9270C: 0x52800A02,
            0x9271C: 0x97FDF42B,
            0x222F4: 0xF9400000,
            0x22308: 0x97FFB4FC,
        }
    )
    config = configparser.ConfigParser(interpolation=None, strict=False)
    config.read_string(
        re.sub(r"\\\r?\n\s*", "", data["etc/imx461bqr_ec1706.conf"].decode())
    )
    profiles = json.loads(data["etc/imx461bqr_ec1706.sp"])["stream_profile"][
        "stream_groups"
    ]
    templates = {p["id"]: p for p in profiles}
    # Reviewed HAL consumers use 88-byte entries and mode-pointer offset 24.
    topology_modes = {}
    driver_names = driver.pointer(0x29EC38)
    for index in (11, 12, 13, 16, 19, 20):
        name = hal.text(hal.pointer(0x1FAD0 + index * 8))
        address = hal.pointer(0x32590 + index * 88 + 24)
        values = struct.unpack("<6I", hal.read(address, 24))
        mode, fps100, width, height, _, bits = values
        if not 0 <= mode < 45:
            raise ValueError("mode index outside audited driver table")
        driver_name = driver.text(driver_names + mode * 64, 64)
        topology_modes[name] = dict(
            hal_entry=index,
            sensor_mode=mode,
            nominal_fps=fps100 / 100,
            sensor_width=width,
            sensor_height=height,
            hal_bits=bits,
            driver_mode_name=driver_name,
        )
    candidates = []
    for profile in (
        "video_3840x2160_2997",
        "video_8192x3428_2400",
        "video_1920x1080_5994",
        "video_11656x8742_1000",
    ):
        section = config[profile + ":raw_dump"]
        width, height = (int(v.strip()) for v in section["res"].split(","))
        maps = config[profile + ":tplgy_map"]["tplgy_map[]"]
        topology = config[maps]["repeating_tplgy_id"]
        template = templates[config[profile + ":basic"]["template_id"]]
        stream = next(s for s in template["streams"] if s["id"] == "raw_dump")
        candidates.append(
            dict(
                profile=profile,
                width=width,
                height=height,
                format=section["format"],
                port=section["physical_port"],
                buffers=int(section["buffer_nr"]),
                behavior=stream["behavior"],
                flags=stream.get("flag", []),
                topology=topology,
                compiled_mode=topology_modes[topology],
            )
        )
    return dict(
        model="X2D 100C",
        firmware="4.2.0",
        verification="static_offline",
        camera_tested=False,
        input_sha256=INPUTS,
        checked_instructions=16,
        raw_candidates=candidates,
        full_resolution_14bit=topology_modes["TPLG_IMX461BQR_STILL_14BIT"],
        callback_evidence=dict(
            registration_symbol="cam_cap_eng_register_stream_observer",
            consumer_registration_symbol="cam_stream_consumer_register_observer",
            copied_observer_record_bytes=80,
        ),
        unresolved=[
            "Runtime mode activation and measured frame cadence",
            "RAW16_OPAQUE unpacking, count alignment, Bayer phase and optical-black layout",
            "DMA mapping/cache synchronization and exact callback ownership ABI",
            "Per-mode black/white/color/crop calibration",
            "Camera encoding time, memory pressure, storage and thermal stability",
        ],
        limits=[
            "Nominal modes do not prove working camera recording",
            "12K driver mode name says 11-bit while its HAL field says 12; do not silently reconcile",
            "No X2D II addresses or conclusions are transferred",
        ],
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--system-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.system_root.resolve()):
        parser.error("output must be outside read-only input tree")
    report = audit(args.system_root)
    with args.output.open("x") as output:
        json.dump(report, output, indent=2)
        output.write("\n")
    print(
        json.dumps(
            dict(
                model=report["model"],
                firmware=report["firmware"],
                candidates=len(report["raw_candidates"]),
                camera_tested=False,
            )
        )
    )


if __name__ == "__main__":
    main()
