#!/usr/bin/env python
"""
Written by Dann Bohn
Github: https://github.com/whereismyjetpack
Email: dannbohn@gmail.com

Script to add a Hard disk to an existing VM
This is for demonstration purposes only.
I did not do a whole lot of sanity checking, etc.

Known issues:
This will not add more than 15 disks to a VM
To do that the VM needs an additional scsi controller
and I have not yet worked through that
"""
import atexit
import ssl
import time

from pyVim.connect import SmartConnect, Disconnect
from pyVmomi import vim


def get_obj(content, vimtype, name):
    obj = None
    container = content.viewManager.CreateContainerView(
        content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def enlarge_disk(vm, new_disk_size, id_scsi: int):
    for dev in vm.config.hardware.device:
        if hasattr(dev.backing, 'fileName') and id_scsi == dev.unitNumber:
            print("%s : Device /dev/sd%s (%g Go)" % (
                dev.deviceInfo.label, chr(ord('a') + dev.unitNumber), int(dev.capacityInKB) / 1024 / 1024))
            capacity_in_kb = dev.capacityInKB
            new_disk_kb = new_disk_size * 1024 * 1024
            if new_disk_kb > capacity_in_kb:
                dev_changes = []
                disk_spec = vim.vm.device.VirtualDeviceSpec()
                disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                disk_spec.device = vim.vm.device.VirtualDisk()
                disk_spec.device.key = dev.key
                disk_spec.device.backing = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                disk_spec.device.backing.fileName = dev.backing.fileName
                disk_spec.device.backing.diskMode = dev.backing.diskMode
                disk_spec.device.controllerKey = dev.controllerKey
                disk_spec.device.unitNumber = dev.unitNumber
                disk_spec.device.capacityInKB = new_disk_kb
                dev_changes.append(disk_spec)
                spec = vim.vm.ConfigSpec()
                spec.deviceChange = dev_changes
                task = vm.ReconfigVM_Task(spec=spec)
                while True:
                    if task.info.state == "success" or task.info.state == "error":
                        print("Task ended : %s !" % (task.info.state))
                        return
                    print("Resize to %s Go running ..." % (new_disk_size))
                    time.sleep(5)


def main():
    # Disabling SSL certificate verification
    context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    context.verify_mode = ssl.CERT_NONE
    # connect to vCenter
    si = SmartConnect(
        host='a82avce02.agora.msanet',
        user='c82nbar',
        pwd='W--Vrtw2016-1',
        port=443,
        sslContext=context,
    )
    # disconnect this thing
    atexit.register(Disconnect, si)

    vm = None
    content = si.RetrieveContent()
    vm = get_obj(content, [vim.VirtualMachine], "a82aflr01")

    if vm:
        enlarge_disk(vm, 10, 1)
    else:
        print("VM not found")


# Chargement de l'objet Main
if __name__ == "__main__":
    main()
