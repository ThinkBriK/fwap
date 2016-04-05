#!/usr/bin/env python
"""
 Written by Tony Allen
 Github: https://github.com/stormbeard
 Blog: https://stormbeard.net/
 This code has been released under the terms of the Apache 2 licenses
 http://www.apache.org/licenses/LICENSE-2.0.html

 Script to deploy VM via a single .ovf and a single .vmdk file.
"""
import ssl
from argparse import ArgumentParser
from getpass import getpass
from os import system, path
from sys import exit
from threading import Thread
from time import sleep

from pyVim import connect
from pyVmomi import vim


def get_args():
    """
    Get CLI arguments.
    """
    parser = ArgumentParser(description='Arguments for talking to vCenter')

    parser.add_argument('-s', '--vcenter',
                        required=True,
                        action='store',
                        help='vCenter to connect to.')

    parser.add_argument('-o', '--port',
                        type=int,
                        default=443,
                        action='store',
                        help='Port to connect on.')

    parser.add_argument('-u', '--user',
                        required=True,
                        action='store',
                        help='Username to use.')

    parser.add_argument('-p', '--password',
                        required=False,
                        action='store',
                        help='Password to use.')

    parser.add_argument('--datacenter_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the Datacenter you\
                          wish to use. If omitted, the first\
                          datacenter will be used.')

    parser.add_argument('--datastore_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Datastore you wish the VM to be deployed to. \
                          If left blank, VM will be put on the first \
                          datastore found.')

    parser.add_argument('--cluster_name',
                        required=False,
                        action='store',
                        default=None,
                        help='Name of the cluster you wish the VM to\
                          end up on. If left blank the first cluster found\
                          will be used')

    parser.add_argument('-v', '--vmdk_path',
                        required=True,
                        action='store',
                        default=None,
                        help='Path of the VMDK file to deploy.')

    parser.add_argument('-f', '--ovf_path',
                        dest='ovf_path',
                        required=True,
                        action='store',
                        default=None,
                        help='Path of the OVF file to deploy.')

    parser.add_argument('-n', '--name',
                        required=True,
                        action='store',
                        default=None,
                        help='Name of the new VM.')

    parser.add_argument('-e', '--esxi',
                        required=True,
                        action='store',
                        help='ESXi to deploy to.')

    args = parser.parse_args()

    if not args.password:
        args.password = getpass(prompt='Enter password: ')

    return args


def get_ovf_descriptor(ovf_path):
    """
    Read in the OVF descriptor.
    """
    if path.exists(ovf_path):
        with open(ovf_path, 'r') as f:
            try:
                ovfd = f.read()
                f.close()
                return ovfd
            except:
                print("Could not read file: %s" % ovf_path)
                exit(1)


def get_obj(content, vimtype, name):
    """
    Get the vsphere object associated with a given text name
    """
    obj = None
    container = content.viewManager.CreateContainerView(content.rootFolder, vimtype, True)
    for c in container.view:
        if c.name == name:
            obj = c
            break
    return obj


def get_obj_in_list(obj_name, obj_list):
    """
    Gets an object out of a list (obj_list) whos name matches obj_name.
    """
    for o in obj_list:
        if o.name == obj_name:
            return o
    print("Unable to find object by the name of %s in list:\n%s" %
          (o.name, map(lambda o: o.name, obj_list)))
    exit(1)


def get_objects(si, args):
    """
    Return a dict containing the necessary objects for deployment.
    """
    # Get datacenter object.
    datacenter_list = si.content.rootFolder.childEntity
    if args['datacenter_name']:
        datacenter_obj = get_obj_in_list(args['datacenter_name'], datacenter_list)
    else:
        datacenter_obj = datacenter_list[0]

    # Get datastore object.
    datastore_list = datacenter_obj.datastoreFolder.childEntity
    if args['datastore_name']:
        datastore_obj = get_obj_in_list(args['datastore_name'], datastore_list)
    elif len(datastore_list) > 0:
        datastore_obj = datastore_list[0]
    else:
        print("No datastores found in DC (%s)." % datacenter_obj.name)

    # Get cluster object.
    cluster_list = datacenter_obj.hostFolder.childEntity
    if args['cluster_name']:
        cluster_obj = get_obj_in_list(args['cluster_name'], cluster_list)
    elif len(cluster_list) > 0:
        cluster_obj = cluster_list[0]
    else:
        print("No clusters found in DC (%s)." % datacenter_obj.name)

    # Generate resource pool.
    resource_pool_obj = cluster_obj.resourcePool

    return {"datacenter": datacenter_obj,
            "datastore": datastore_obj,
            "resource pool": resource_pool_obj}


def keep_lease_alive(lease):
    """
    Keeps the lease alive while POSTing the VMDK.
    """
    while (True):
        sleep(5)
        try:
            # Choosing arbitrary percentage to keep the lease alive.
            lease.HttpNfcLeaseProgress(50)
            if (lease.state == vim.HttpNfcLease.State.done):
                return
                # If the lease is released, we get an exception.
                # Returning to kill the thread.
        except:
            return


class vmDeploy(object):
    def __init__(self, ovf_path, vm_name, nb_cpu, ram_ko, lan, datacenter_name, datastore_name,
                 cluster_name, esx_host, vm_folder):
        self.vm_name = vm_name
        self.ovf_descriptor = get_ovf_descriptor(ovf_path)
        self.nb_cpu = nb_cpu
        self.ram_ko = ram_ko
        self.wanted_lan_name = lan
        self.ovf_lan = lan
        self.ovf_manager = None
        self.datacenter_name = datacenter_name
        self.datastore_name = datastore_name
        self.cluster_name = cluster_name
        self.esx_host = esx_host
        self.vm_folder = vm_folder

    def connect_vcenter(self, vcenter, user, password, port=443):
        self.vcenter = vcenter
        # Disabling SSL certificate verification
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
        context.verify_mode = ssl.CERT_NONE
        try:
            service_instance = connect.SmartConnect(host=vcenter,
                                                    user=user,
                                                    pwd=password,
                                                    port=port,
                                                    sslContext=context,
                                                    )
        except:
            print("Unable to connect to %s" % vcenter)
            exit(1)
        return service_instance

    def deploy(self, si):
        self.ovf_manager = si.content.ovfManager
        ovf_object = self.ovf_manager.ParseDescriptor(self.ovf_descriptor, vim.OvfManager.ParseDescriptorParams())
        self.ovf_lan_name = ovf_object.network[0].name
        wanted_lan = get_obj(si.content, vim.Network, self.wanted_lan_name)
        spec_params = vim.OvfManager.CreateImportSpecParams(entityName=self.vm_name)
        # On prépare la configuration de l'import à partir des arguments
        objs = get_objects(si, self.__dict__)
        # On crée l'objet représentant l'import : import_spec
        import_spec = self.ovf_manager.CreateImportSpec(self.ovf_descriptor,
                                                        objs["resource pool"],
                                                        objs["datastore"],
                                                        spec_params)
        # On lance l'import OVF dans le resource Pool choisi en paramètre
        chosen_host = get_obj(si.content, vim.HostSystem, self.esx_host)
        chosen_folder = get_obj(si.content, vim.Folder, self.vm_folder)
        lease = objs["resource pool"].ImportVApp(import_spec.importSpec, folder=chosen_folder, host=chosen_host)

        msg = {str}
        keepalive_thread = Thread(target=keep_lease_alive, args=(lease,))
        keepalive_thread.start()

        while True:
            # On attend que le système soit prêt à recevoir
            if lease.state == vim.HttpNfcLease.State.ready:
                # Spawn a dawmon thread to keep the lease active while POSTing
                # VMDK.
                keepalive_thread = Thread(target=keep_lease_alive, args=(lease,))
                keepalive_thread.start()

                # POST the VMDK to the host via curl on the retrieved url. Requests library would work
                # too.
                for disk in import_spec.fileItem:
                    for devurl in lease.info.deviceUrl:
                        # TODO : Vérifier que ce ne soit pas devurl.importKey
                        if devurl.key == disk.deviceId:
                            url = devurl.url.replace('*', self.vcenter)
                            break
                    curl_cmd = (
                        "curl -Ss -X POST --insecure -T %s -H 'Content-Type:application/x-vnd.vmware-streamVmdk' %s" %
                        (disk.path, url))
                    system(curl_cmd)
                lease.HttpNfcLeaseComplete()
                keepalive_thread.join()
                return 0
            elif lease.state == vim.HttpNfcLease.State.error:
                print("Lease error: " + lease.state.error)
                exit(1)
        connect.Disconnect(si)


def main():
    # args = get_args()
    # TODO a remplacer par args une fois le programme fonctionnel

    deployment = vmDeploy(ovf_path='D:\VMs\OVF\ovf_53X_64_500u1.ova\ovf_53X_64_500u1.ovf',
                          vm_name='a82aflr02',
                          nb_cpu=1,
                          ram_ko=524248,
                          lan='Lan Data',
                          cluster_name='Cluster_Agora',
                          datastore_name='CEDRE_029',
                          datacenter_name='Zone LAN AGORA',
                          esx_host='a82hhot20.agora.msanet',
                          vm_folder='_Autres')
    si = deployment.connect_vcenter(vcenter='a82avce02.agora.msanet', user='c82nbar', password='W--Vrtw2016-1')
    deployment.deploy(si)


if __name__ == "__main__":
    exit(main())
