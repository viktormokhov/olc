#!/usr/bin/env python3
"""Repack Olcbox APK: patched libgojni + Android R+ rules (resources.arsc STORED)."""
import os
import zipfile

BASE = "/tmp/apk-patch/base.apk"
AAR = "/tmp/apk-patch/aar"
OUT = "/tmp/apk-patch/unsigned2.apk"
LIBS = {
    "armeabi-v7a": "jni/armeabi-v7a/libgojni.so",
    "arm64-v8a": "jni/arm64-v8a/libgojni.so",
    "x86_64": "jni/x86_64/libgojni.so",
}

def skip_sig(name: str) -> bool:
    return name.startswith("META-INF/") and (
        name.endswith(".RSA") or name.endswith(".SF") or name == "META-INF/MANIFEST.MF"
    )

replace = {f"lib/{abi}/libgojni.so" for abi in LIBS}

def must_store(name: str) -> bool:
    return name == "resources.arsc"

with zipfile.ZipFile(BASE, "r") as zin, zipfile.ZipFile(OUT, "w") as zout:
    for info in zin.infolist():
        if skip_sig(info.filename) or info.filename in replace:
            continue
        data = zin.read(info.filename)
        ni = zipfile.ZipInfo(filename=info.filename, date_time=info.date_time)
        if must_store(info.filename):
            ni.compress_type = zipfile.ZIP_STORED
            zout.writestr(ni, data, compress_type=zipfile.ZIP_STORED)
        else:
            ni.compress_type = info.compress_type
            ni.external_attr = info.external_attr
            zout.writestr(ni, data)
    for abi, rel in LIBS.items():
        fn = f"lib/{abi}/libgojni.so"
        data = open(os.path.join(AAR, rel), "rb").read()
        ni = zipfile.ZipInfo(fn)
        zout.writestr(ni, data, compress_type=zipfile.ZIP_DEFLATED)
        print("patched", fn, len(data))
print("wrote", OUT, os.path.getsize(OUT))
