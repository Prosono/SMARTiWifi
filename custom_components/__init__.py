"""The Pulse Audio integration."""
import asyncio
import os
import subprocess
import socket
import sys
import time

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import CONF_NAME

from .const import DOMAIN, CONF_SSID, CONF_STATE
from .const import DOMAIN, CONF_PASS
from .const import DOMAIN, CONF_CHAN
from .const import DOMAIN, CONF_SINK

PLATFORMS = ["media_player"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Pulse Audio component."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Pulse Audio from a config entry."""
    name = entry.data[CONF_NAME]
    ssid = entry.data[CONF_SSID]
    password = entry.data[CONF_PASS]
    channel = entry.data[CONF_CHAN]
    state = entry.data[CONF_STATE]

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        CONF_NAME: name,
       # CONF_SINK: sink,
        CONF_SSID: ssid,
        CONF_PASS: password,
        CONF_CHAN: channel,
        CONF_STATE: state
    }
    if not os.path.exists('/f'):
        os.makedirs('/f')
    if not os.path.exists('/f/root'):
        os.system('mount /dev/mmcblk1p7 /f')
   
    if state == "off":
        port = 8899
        host = 'localhost'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        data = "ifconfig wlan0 down"
        byteswritten = 0
        while byteswritten < len(data):
            startpos = byteswritten
            endpos = min(byteswritten + 1024, len(data))
            byteswritten += s.send(data[startpos:endpos].encode('utf-8'))
            sys.stdout.write("Wrote %d bytes\r" % byteswritten)
            sys.stdout.flush()
        s.shutdown(1)
        time.sleep(1)
        return True
    else:
        port = 8899
        host = 'localhost'
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        data = "ifconfig wlan0 up"
        byteswritten = 0
        while byteswritten < len(data):
            startpos = byteswritten
            endpos = min(byteswritten + 1024, len(data))
            byteswritten += s.send(data[startpos:endpos].encode('utf-8'))
            sys.stdout.write("Wrote %d bytes\r" % byteswritten)
            sys.stdout.flush()
        s.shutdown(1)
        time.sleep(1)
    print("ip:", name, "SSID:", ssid, "password:", password, "channel:", channel)
    #wifi set
    sed_ssid_str = 'sed -i "s/^ssid=.*$/ssid=' + ssid + '/g" /f/etc/hostapd.conf'
    os.system(sed_ssid_str)
    sed_pass_str = 'sed -i "s/^.*passphrase.*$/wpa_passphrase=' + password + '/g" /f/etc/hostapd.conf'
    os.system(sed_pass_str)
    sed_channel_str = 'sed -i "s/^.*channel.*$/channel=' + str(channel) + '/g" /f/etc/hostapd.conf'
    os.system(sed_channel_str)
    if int(channel) > 35:
        os.system('sed -i "s/^.*hw_mode.*$/hw_mode=a/g" /f/etc/hostapd.conf')
    else:
        os.system('sed -i "s/^.*hw_mode.*$/hw_mode=g/g" /f/etc/hostapd.conf')
    output = subprocess.check_output('cat /f/usr/share/hassio/homeassistant/.storage/core.config_entries | grep -A 5 "dusunwifi" | grep ssid | wc -l', shell=True)
    output = output.strip().decode()
    if output == '1':
        os.system('/f/usr/bin/up_wifi_ssid.sh')
    #dhcp set
    sed_dhcp_str = 'sed -i "s/^.*dhcp-option.*$/dhcp-option=3,' + name + '/g" /f/etc/dnsmasq.conf'
    os.system(sed_dhcp_str)
    dhcp_s = name[:name.rfind(".")] + ".100"
    dhcp_e = name[:name.rfind(".")] + ".200"
    sed_pool_str = 'sed -i "s/^.*dhcp-range.*$/dhcp-range=' + dhcp_s + ',' + dhcp_e + ',6h/g" /f/etc/dnsmasq.conf'
    os.system(sed_pool_str)

    #ip set
    sed_ip_str = 'sed -i "s/^.*address.*$/address:' + name + '/g" /f/etc/network/interfaces'
    #os.system('sed -i "s/^.*address.*$/address:$ip/g" /etc/network/interfaces')
    os.system(sed_ip_str)
    #os.system('/usr/bin/ds_conf_ap.sh')
    os.system('touch /f/root/.homeassistant/custom_components/dusunwifi/start')
    
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    if not os.path.exists('/f'):
        os.makedirs('/f')
    if not os.path.exists('/f/root'):
        os.system('mount /dev/mmcblk1p7 /f')

    filename = "/f/root/.homeassistant/custom_components/dusunwifi/wifi"
    os.system('rm -rf ' + filename)
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
