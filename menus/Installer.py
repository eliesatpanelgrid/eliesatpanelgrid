#!/usr/bin/env python3 -u
# -*- coding: utf-8 -*-

import os
import subprocess
import shutil
import tarfile
import urllib.request
import time
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)

# --------------------------------------------------
# CONFIG
# --------------------------------------------------

PLUGIN_URL = "https://github.com/eliesatpanelgrid/eliesatpanelgrid/archive/main.tar.gz"
SCRIPTS_URL = "https://github.com/eliesatpanelgrid/scripts/archive/main.tar.gz"

PLUGIN_TMP = "/tmp/plugin.tar.gz"
SCRIPTS_TMP = "/tmp/scripts.tar.gz"

PLUGIN_DIR = "/usr/lib/enigma2/python/Plugins/Extensions/ElieSatPanelGrid"

FEED_FILE = "/etc/opkg/eliesat-feed.conf"
FEED_URL = "https://github.com/eliesat/feed/raw/main/"

OUTPUT_LOG = "/tmp/eliesatpanel_install.log"

# --------------------------------------------------
# UTIL
# --------------------------------------------------

def run(cmd, silent=True):
    return subprocess.call(
        cmd,
        shell=True,
        stdout=subprocess.DEVNULL if silent else None,
        stderr=subprocess.DEVNULL if silent else None
    )


def download(url, dest):
    urllib.request.urlretrieve(url, dest)


def extract(tar_path):
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall("/tmp")


def log(msg):
    with open(OUTPUT_LOG, "a") as f:
        f.write(msg + "\n")


# --------------------------------------------------
# STEP UI (CLEAN BLOCK)
# --------------------------------------------------

def step(title, func):
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
    print(f"▶ {title}", flush=True)

    try:
        func()
        print("✔ Installation completed successfully", flush=True)
        log(f"{title} -> SUCCESS")

    except Exception as e:
        print("✖ Something went wrong - failed to install", flush=True)
        log(f"{title} -> FAILED: {str(e)}")

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
    time.sleep(1)


# --------------------------------------------------
# TASKS
# --------------------------------------------------

def install_libraries():
    libs = ["wget", "curl", "python3-requests", "python3-six"]
    for lib in libs:
        run(f"opkg install {lib}", silent=True)
    return True


def install_feed():
    if os.path.exists(FEED_FILE):
        os.remove(FEED_FILE)

    with open(FEED_FILE, "w") as f:
        f.write(f"src/gz eliesat-feed {FEED_URL}\n")

    run("opkg update", silent=True)
    return True


def install_plugin():
    if os.path.exists(PLUGIN_DIR):
        shutil.rmtree(PLUGIN_DIR)

    download(PLUGIN_URL, PLUGIN_TMP)
    extract(PLUGIN_TMP)

    src = "/tmp/eliesatpanelgrid-main"
    if os.path.exists(src):
        shutil.move(src, PLUGIN_DIR)

    return True


def install_scripts():
    tmp = "/tmp/scripts-main"

    if os.path.exists(tmp):
        shutil.rmtree(tmp)

    download(SCRIPTS_URL, SCRIPTS_TMP)
    extract(SCRIPTS_TMP)

    if os.path.exists(tmp + "/usr"):
        run(f"cp -rf {tmp}/usr/* /usr/", silent=True)

    return True


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    if os.path.exists(OUTPUT_LOG):
        os.remove(OUTPUT_LOG)

    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)
    print("         ☆ ElieSatPanelGrid Installer ☆", flush=True)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    step("Downloading and installing missing libraries", install_libraries)
    step("Downloading and installing ElieSat feed", install_feed)
    step("Downloading and installing ElieSatPanelGrid", install_plugin)
    step("Downloading and installing scripts", install_scripts)

    time.sleep(3)

    print("     ☆ Restarting Enigma2, please wait... ☆", flush=True)
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━", flush=True)

    time.sleep(3)

    run("killall -9 enigma2", silent=True)

    log("✔ Enigma2 restart triggered")


# --------------------------------------------------
# RUN
# --------------------------------------------------

if __name__ == "__main__":
    main()