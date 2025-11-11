
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import os, subprocess


def create_mo_files():
    podir = "po"
    mo = []
    for po in os.listdir(podir):
        if po.endswith(".po"):
            os.makedirs(
                "{}/{}/LC_MESSAGES".format(podir, po.split(".po")[0]), exist_ok=True
            )
            mo_file = "{}/{}/LC_MESSAGES/{}".format(
                podir, po.split(".po")[0], "pardus-idevice-mounter.mo"
            )
            msgfmt_cmd = "msgfmt {} -o {}".format(podir + "/" + po, mo_file)
            subprocess.call(msgfmt_cmd, shell=True)
            mo.append(
                (
                    "/usr/share/locale/" + po.split(".po")[0] + "/LC_MESSAGES",
                    ["po/" + po.split(".po")[0] + "/LC_MESSAGES/pardus-idevice-mounter.mo"],
                )
            )
    return mo


changelog = "debian/changelog"
if os.path.exists(changelog):
    head = open(changelog).readline()
    try:
        version = head.split("(")[1].split(")")[0]
    except:
        print("debian/changelog format is wrong for get version")
        version = "0.0.0"
    f = open("src/__version__", "w")
    f.write(version)
    f.close()

data_files = [
    ("/usr/bin", ["pardus-idevice-mounter"]),
    ("/usr/share/applications", ["data/tr.org.pardus.idevice-mounter.desktop"]),
    ("/usr/share/pardus/pardus-idevice-mounter/ui", ["ui/main_window.glade"]),
    (
        "/usr/share/pardus/pardus-idevice-mounter/src",
        [
            "src/main.py",
            "src/main_window.py",
            "src/device_manager.py",
            "src/mount_manager.py",
            "src/logger_config.py",
            "src/__version__",
        ],
    ),
    ("/usr/share/pardus/pardus-idevice-mounter/data",
        ["data/pardus-idevice-mounter.svg"]
    ),
    ("/usr/share/icons/hicolor/scalable/apps/",
        ["data/pardus-idevice-mounter.svg"
        ]
    )
] + create_mo_files()


setup(
    name="pardus-idevice-mounter",
    version=version,
    packages=find_packages(),
    scripts=["pardus-idevice-mounter"],
    install_requires=["PyGObject"],
    data_files=data_files,
    author="Emel Öztürk",
    author_email="emel.ozturk@pardus.org.tr",
    description="Device mounter application for iOS devices",
    license="GPLv3",
    keywords="pardus-idevice-mounter, idevice-mounter",
    url="https://github.com/pardus/pardus-idevice-mounter",
)
