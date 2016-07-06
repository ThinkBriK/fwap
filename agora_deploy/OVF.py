#!/usr/bin/env python
"""
Script pour déployer une VM TAT1 dont on a récupéré les informations
 Ecrit par Benoit BARTHELEMY
 benoit.barthelemy2@open-groupe.com
"""
import atexit
import datetime
import re
import ssl
from argparse import ArgumentParser
from getpass import getpass
from os import path
from sys import exit
from threading import Thread
from time import sleep

import requests
from pyVim import connect
from pyVmomi import vim
from pyVmomi import vmodl
from tools import tasks

from agora_deploy import FWAP


def get_args():
    """
    Récuépration des informations de la ligne de commande
    """
    parser = ArgumentParser(description='Arguments for talking to vCenter')

    parser.add_argument('--eol',
                        required=False,
                        action='store',
                        default='Perenne',
                        help='End of life of the VM (default=Perenne)')

    parser.add_argument('--demandeur',
                        required=True,
                        action='store',
                        help='Name of the requester')

    parser.add_argument('--fonction',
                        required=True,
                        action='store',
                        help='Function of the VM')

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
    Lecture du descripteur OVF
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
    Récupération des objets vsphere par nom
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
    récupération d'un objet dans une liste par nom
    """
    for o in obj_list:
        if o.name == obj_name:
            return o
    print("Unable to find object by the name of %s in list:\n%s" %
          (obj_name, map(lambda o: o.name, obj_list)))
    exit(1)


def get_objects(si, datacenter=None, datastore=None, cluster=None):
    """
    Retourne un dictionnaire contenant les informations nécessaires à un déploiement d'OVF.
    """

    # Get datacenter object.
    datacenter_list = []

    for toplevel_entity in si.content.rootFolder.childEntity:
        if type(toplevel_entity) == vim.Datacenter:
            datacenter_list.append(toplevel_entity)

    if datacenter:
        datacenter_obj = get_obj_in_list(datacenter, datacenter_list)
    else:
        datacenter_obj = datacenter_list[0]

    # Get datastore object.
    datastore_list = []
    for datacenter_entity in datacenter_list:
        for datastore_entity in datacenter_entity.datastoreFolder.childEntity:
            if type(datastore_entity) == vim.Datastore:
                datastore_list.append(datastore_entity)

    if datastore:
        datastore_obj = get_obj_in_list(datastore, datastore_list)
    elif len(datastore_list) > 0:
        datastore_obj = datastore_list[0]
    else:
        print("No datastores found in DC (%s)." % datacenter_obj.name)
        datastore_obj = None

    # Get cluster object.
    cluster_list = []
    for datacenter_entity in datacenter_list:
        for cluster_entity in datacenter_entity.hostFolder.childEntity:
            if type(cluster_entity) == vim.ClusterComputeResource:
                cluster_list.append(cluster_entity)

    if cluster:
        cluster_obj = get_obj_in_list(cluster, cluster_list)
    elif len(cluster_list) > 0:
        cluster_obj = cluster_list[0]
    else:
        print("No clusters found in DC (%s)." % datacenter_obj.name)
        cluster_obj = None

    # Generate resource pool.
    resource_pool_obj = cluster_obj.resourcePool

    return {"datacenter": datacenter_obj,
            "datastore": datastore_obj,
            "resource pool": resource_pool_obj}


def keep_lease_alive(lease):
    """
    Garde le lease du VMDK ouvert le temps du transfert.
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


def connect_vcenter(vcenter, user, password, port=443):
    """ Renvoie un objet service_instance représentant une connexion vcenter """
    # Suppression de la vérification SSL
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
    # Déconnexion auto à la fermeture
    atexit.register(connect.Disconnect, service_instance)
    return service_instance


def uploadOVF(url=None, fileFullPath=None):
    """ Permet l'upload de l'OVF sur l'ESX voulu """
    headers = {'Content-Type': 'application/x-vnd.vmware-streamVmdk'}
    # Upload en Streaming vu la taille des images de VMs
    with open(fileFullPath, 'rb') as f:
        r = requests.post(url=url, headers=headers, data=f, verify=False)

    # Gestion des erreurs
    r.raise_for_status()


def run_command_in_guest(vm, command, arguments, guestUser, guestPassword, si):
    """ Permet de lancer une commande via les vmWare agora_tools dans l'OS d'une VM"""
    exitCode = None
    try:
        cmdspec = vim.vm.guest.ProcessManager.ProgramSpec(arguments=arguments, programPath=command)

        # Credentials used to login to the guest system
        creds = vim.vm.guest.NamePasswordAuthentication(username=guestUser, password=guestPassword)

        # pid de la commande

        pid = si.content.guestOperationsManager.processManager.StartProgramInGuest(vm=vm, auth=creds, spec=cmdspec)

        # Code Retour
        while exitCode is None:
            exitCode = \
                si.content.guestOperationsManager.processManager.ListProcessesInGuest(vm=vm, auth=creds, pids=pid)[
                    0].exitCode
            sleep(1)
    except vim.fault.GuestComponentsOutOfDate as e:
        print(e.msg)

    return exitCode


def list_process_pids_in_guest(vm, proc_name, guestUser, guestPassword, si):
    """ Permet de lister tous les processus de l'OS d'une VM correspondant à un nom de process """
    pids = []
    try:
        # Credentials used to login to the guest system
        creds = vim.vm.guest.NamePasswordAuthentication(username=guestUser, password=guestPassword)
        processes = si.content.guestOperationsManager.processManager.ListProcessesInGuest(vm=vm, auth=creds)
        for proc in processes:
            if re.search(proc_name, proc.name):
                pids.append(proc.pid)
    except vim.fault.GuestComponentsOutOfDate as e:
        print(e.msg)

    return pids


def kill_process_in_guest(vm, pid, guestUser, guestPassword, si):
    """
    Permet de tuer un processus dans l'OS d'une VM
    :param vm: nom de la VM
    :param pid: PID du process à tuer
    :param guestUser: Nom du compte dans l'OS de la VM (doit avoir les droits nécessaires)
    :param guestPassword: Mot de passe du compte dans l'OS de la VM
    :param si:
    :return:
    """
    try:
        creds = vim.vm.guest.NamePasswordAuthentication(username=guestUser, password=guestPassword)
        si.content.guestOperationsManager.processManager.TerminateProcessInGuest(vm=vm, auth=creds, pid=pid)
    except vim.fault.GuestComponentsOutOfDate as e:
        print(e.msg)


class vmDeploy(object):
    """ Déploiement d'une VM Tat1 depuis un OVF """
    def __init__(self, ovfpath, name, vcpu, ram, lan, datastore, esx, vmfolder, ep, rds, demandeur, fonction, eol,
                 vcenter, disks, deployer, mtl=None,
                 **kwargs):
        """ Constructeur """
        self.vm_name = name
        self.ovf_path = ovfpath
        self.ovf_descriptor = get_ovf_descriptor(ovfpath)
        self.nb_cpu = vcpu
        self.ram = ram
        self.wanted_lan_name = lan
        self.ovf_lan = lan
        self.ovf_manager = None
        self.datastore_name = datastore
        self.esx_host = esx
        self.vm_folder = vmfolder
        self.ep = ep.upper()
        self.rds = rds.upper()
        self.disks = disks
        self.deployed_disks = 0
        self.demandeur = demandeur
        self.fonction = fonction
        self.eol = eol
        self.vcenter = vcenter
        self.mtl = mtl
        self.deployer = deployer

    def _add_disks(self, si):
        """
        Ajout des disques à la VM définie par l'objet
        :param si: service_instance représentant la connexion vcenter
        """
        for disk in self.disks:
            # print(disk)
            # On déploie le disque de la taille des partitions + la taille des partitions sizées sur la RAM (+5% pour EXT3) + 64 M0 (pour LVM)
            mosize = int(
                disk.partsize + (disk.extra_mem_times_size * (self.ram / 1024 / 1024 + 1) * 1024 * 105 / 100) + 64)

            # On arrondi aux 100 Mo supérieur
            if (mosize % 100) > 0:
                morounded = mosize // 100 + 1
            else:
                morounded = mosize / 100

            self.add_disk(disk_size=morounded * 100, si=si)

    def _connect_switch(self, si):
        """
        Connexion aux switchs
        :param si: service_instance représentant la connexion vcenter
        """
        new_vm_spec = vim.vm.ConfigSpec()
        # Changement de vSwitch
        vm = self.vm
        # Ne fonctionne wue pour la première interface
        device_change = []
        for device in vm.config.hardware.device:
            if isinstance(device, vim.vm.device.VirtualEthernetCard):
                nicspec = vim.vm.device.VirtualDeviceSpec()
                nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
                nicspec.device = device
                nicspec.device.wakeOnLanEnabled = True
                nicspec.device.backing = vim.vm.device.VirtualEthernetCard.NetworkBackingInfo()
                nicspec.device.backing.network = get_obj(si.RetrieveContent(), [vim.Network],
                                                         self.wanted_lan_name)
                nicspec.device.backing.deviceName = self.wanted_lan_name
                nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
                nicspec.device.connectable.startConnected = True
                nicspec.device.connectable.allowGuestControl = True
                device_change.append(nicspec)
                break
        new_vm_spec.deviceChange = device_change
        task = vm.ReconfigVM_Task(new_vm_spec)
        task.SetTaskDescription(vmodl.LocalizableMessage(key="pyAgora_connect", message="Connecting LAN"))
        tasks.wait_for_tasks(si, [task])

    def _correct_cdrom(self, si):
        """
        Connexion du cdrom au cdrom du client (pour éviter les problèmes avec des OVF mal faits)
        :param si: service_instance représentant la connexion vcenter
        """
        # Rajoute la sélection systématique du CDROM du client (si l'hôte a un CD dans le lecteur tout foire)
        virtual_cdrom_device = None
        for dev in self.vm.config.hardware.device:
            if isinstance(dev, vim.vm.device.VirtualCdrom):
                virtual_cdrom_device = dev

        if not virtual_cdrom_device:
            raise RuntimeError('Virtual CDROM could not '
                               'be found.')
        virtual_cd_spec = vim.vm.device.VirtualDeviceSpec()
        virtual_cd_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.edit
        virtual_cd_spec.device = vim.vm.device.VirtualCdrom()
        virtual_cd_spec.device.controllerKey = virtual_cdrom_device.controllerKey
        virtual_cd_spec.device.key = virtual_cdrom_device.key
        virtual_cd_spec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        virtual_cd_spec.device.backing = vim.vm.device.VirtualCdrom.RemotePassthroughBackingInfo()

        # Allowing guest control
        virtual_cd_spec.device.connectable.allowGuestControl = True

        dev_changes = []
        dev_changes.append(virtual_cd_spec)
        spec = vim.vm.ConfigSpec()
        spec.deviceChange = dev_changes
        task = self.vm.ReconfigVM_Task(spec=spec)
        task.SetTaskDescription(
            vmodl.LocalizableMessage(key="pyAgora_cdrom_update", message="Connecting to client CDROM"))
        tasks.wait_for_tasks(si, [task])

    def resize(self, si, nb_cpu, ram):
        """
        Permet de resizer les ressources compute d'une VM
        :param si: service_instance représentant la connexion vcenter
        :param nb_cpu: nombre de cpus
        :param ram: taille de la ram en octets
        """
        new_vm_spec = vim.vm.ConfigSpec()
        new_vm_spec.numCPUs = nb_cpu
        new_vm_spec.memoryMB = ram // 1024
        task = self.vm.ReconfigVM_Task(new_vm_spec)
        task.SetTaskDescription(vmodl.LocalizableMessage(key="pyAgora_resize", message="Resizing VM Compute resources"))
        tasks.wait_for_tasks(si, [task])

    def _ovf_deploy(self, si):
        """
        Déploiement "Basique" de l'OVF, sans métadonnées et autres spécificités Agora
        :param si:service_instance représentant la connexion vcenter
        """
        self.ovf_manager = si.content.ovfManager
        ovf_object = self.ovf_manager.ParseDescriptor(self.ovf_descriptor, vim.OvfManager.ParseDescriptorParams())
        self.ovf_lan_name = ovf_object.network[0].name
        wanted_lan = get_obj(si.content, vim.Network, self.wanted_lan_name)
        spec_params = vim.OvfManager.CreateImportSpecParams(entityName=self.vm_name)

        # On lance l'import OVF dans le resource Pool choisi en paramètre
        chosen_host = get_obj(si.content, vim.HostSystem, self.esx_host)
        if type(self.vm_folder) == vim.Folder:
            chosen_folder = self.vm_folder
        else:
            chosen_folder = get_obj(si.content, vim.Folder, self.vm_folder)

        # On prépare la configuration de l'import à partir des arguments
        objs = {}
        objs['datastore'] = get_obj(content=si.content, vimtype=vim.Datastore, name=self.datastore_name)
        if type(chosen_host.parent) == vim.ClusterComputeResource:
            objs['cluster'] = chosen_host.parent
            objs['resource pool'] = chosen_host.parent.resourcePool
        else:
            objs['cluster'] = None
            objs['resource pool'] = None

        # On crée l'objet représentant l'import : import_spec
        import_spec = self.ovf_manager.CreateImportSpec(self.ovf_descriptor,
                                                        objs["resource pool"],
                                                        objs["datastore"],
                                                        spec_params)

        # TODO : Rajouter de l'error handling sur la création du Lease (nom de machine existante etc ...)

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

                for disk in import_spec.fileItem:
                    for devurl in lease.info.deviceUrl:
                        if devurl.importKey == disk.deviceId:
                            url = devurl.url.replace('*', self.vcenter)
                            break
                    fullpath = path.dirname(self.ovf_path) + '\\' + disk.path
                    print("Uploading %s to %s." % (fullpath, url))
                    # TODO faire l'upload dans un thread et MAJ l'avancement de l'upload dans vSphere
                    uploadOVF(url=url, fileFullPath=fullpath)
                    print("Upload of %s : Done." % fullpath)
                lease.HttpNfcLeaseComplete()
                self.vm = lease.info.entity
                keepalive_thread.join()
                break
            elif lease.state == vim.HttpNfcLease.State.error:
                print("Lease error: " + lease.state.error)
                exit(1)

    def _update_metadata(self):
        """
        Mise à jour des attributs de la VM qui vient d'être déployée
        """
        # TODO Créer une méthode publique pour mettre à jour un ou plusieurs attributs
        # MAJ Attributs vSphere
        self.vm.setCustomValue(key="Admin Systeme", value="POP")
        self.vm.setCustomValue(key="Date creation", value=str(datetime.date.today()))
        self.vm.setCustomValue(key="Date fin de vie", value=self.eol)
        self.vm.setCustomValue(key="Demandeur", value=self.demandeur)
        self.vm.setCustomValue(key="Environnement", value=self.ep)
        self.vm.setCustomValue(key="Fonction", value=self.fonction)
        self.vm.setCustomValue(key="LAN", value=self.wanted_lan_name)

    def _update_annotation(self, si):
        """
        Mise à jour des annotations de la VM qui vient d'être déployée (Fait en dernier pour signifier la fin du déploiement)
        :param si: service_instance représentant la connexion vcenter
        :return:
        """
        spec = vim.vm.ConfigSpec()
        text = "Déployé par : " + self.deployer
        spec.annotation = self.vm.config.annotation + "\n" + len(text) * '-' + "\n" + text + "\n" + len(text) * '-'
        task = self.vm.ReconfigVM_Task(spec)
        tasks.wait_for_tasks(si, [task])

    def _update_ovf_properties(self, si):
        """
        Mise à jour des propriétés OVF utilisées par les scripts TAT1
        :param si: service_instance représentant la connexion vcenter
        """
        new_vm_spec = vim.vm.ConfigSpec()
        # MAJ variables OVF
        new_vAppConfig = vim.vApp.VmConfigSpec()
        new_vAppConfig.property = []
        for ovf_property in self.vm.config.vAppConfig.property:
            updated_spec = vim.vApp.PropertySpec()
            updated_spec.info = ovf_property
            updated_spec.operation = vim.option.ArrayUpdateSpec.Operation.edit
            if ovf_property.id == 'EP':
                updated_spec.info.value = self.ep
            elif ovf_property.id == 'hostname':
                updated_spec.info.value = self.vm_name
            elif ovf_property.id == 'RDS':
                updated_spec.info.value = self.rds
            elif ovf_property.id == 'url_referentiel':
                if self.mtl:
                    updated_spec.info.value = 'http://' + self.mtl + '/repo/agora/scripts'
                else:
                    if self.ep == 'D' or self.ep == 'E':
                        updated_spec.info.value = 'http://a82amtl01.agora.msanet/repo/agora/scripts'
                    else:
                        updated_spec.info.value = 'http://a82amtl02.agora.msanet/repo/agora/scripts'
            elif ovf_property.id == 'MTL_HOST_REPO':
                if self.mtl:
                    updated_spec.info.value = self.mtl
                else:
                    if self.ep == 'D' or self.ep == 'E':
                        updated_spec.info.value = 'a82amtl01.agora.msanet'
                    else:
                        updated_spec.info.value = 'a82amtl02.agora.msanet'
            else:
                continue
            new_vAppConfig.property.append(updated_spec)
        new_vm_spec.vAppConfig = new_vAppConfig
        new_vm_spec.vAppConfigRemoved = False

        task = self.vm.ReconfigVM_Task(new_vm_spec)
        task.SetTaskDescription(vmodl.LocalizableMessage(key="pyAgora_writeovf", message="Writing OVF values"))
        tasks.wait_for_tasks(si, [task])

    def _update_root_pw_on_first_boot(self, newRootPassword, si):
        """
        Changement du mot de passe root lors d'un déploiement TAT1
        :param newRootPassword: nouveau mot de passe root
        :param si: service_instance représentant la connexion vcenter
        """
        # Changement du MDP root
        # On attend que le fichier /Agora/build/config/AttenteRootpw soit créé
        while True:
            try:
                if 0 == run_command_in_guest(vm=self.vm, command='/usr/bin/test',
                                             arguments="-f /Agora/build/config/AttenteRootpw",
                                             guestUser='root', guestPassword='', si=si):
                    break
            # On catche l'exception pour éviter de planter en raison des agora_tools pas lancés
            except (vim.fault.GuestOperationsUnavailable):
                pass
            sleep(3)
        # On sette le MDP root
        run_command_in_guest(vm=self.vm, command='/bin/echo',
                             arguments=newRootPassword + '>/Agora/build/config/rootpw', guestUser='root',
                             guestPassword='', si=si)
        # On kille les dialog
        pids = list_process_pids_in_guest(vm=self.vm, proc_name='dialog', guestUser='root', guestPassword='', si=si)
        while True:
            if len(pids) == 0:
                break
            for pid in pids:
                kill_process_in_guest(vm=self.vm, pid=pid, guestUser='root', guestPassword='', si=si)
            sleep(1)
            pids = list_process_pids_in_guest(vm=self.vm, proc_name='dialog', guestUser='root', guestPassword='', si=si)

    def add_disk(self, disk_size, si, disk_type=''):
        """
        Permet d'ajouter un disque à une VM
        :param disk_size: Taille du disque en Mo
        :param si: service_instance représentant la connexion vcenter
        :param disk_type: Si "thin" création en thin provisionning
        Ajout d'un disque à la VM
        """
        spec = vim.vm.ConfigSpec()
        vm = self.vm
        # get all disks on a VM, set unit_number to the next available
        for dev in vm.config.hardware.device:
            if hasattr(dev.backing, 'fileName'):
                unit_number = int(dev.unitNumber) + 1 + self.deployed_disks
                # unit_number 7 reserved for scsi controller
                if unit_number == 7:
                    unit_number += 1
                if unit_number >= 16:
                    print("Trop de disques !!!!")
                    exit(1)
            if isinstance(dev, vim.vm.device.VirtualSCSIController):
                controller = dev
        # add disk here
        dev_changes = []
        new_disk_kb = int(disk_size) * 1024
        disk_spec = vim.vm.device.VirtualDeviceSpec()
        disk_spec.fileOperation = "create"
        disk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        disk_spec.device = vim.vm.device.VirtualDisk()
        disk_spec.device.backing = \
            vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
        if disk_type == 'thin':
            disk_spec.device.backing.thinProvisioned = True
        disk_spec.device.backing.diskMode = 'persistent'
        disk_spec.device.unitNumber = unit_number
        disk_spec.device.capacityInKB = new_disk_kb
        disk_spec.device.controllerKey = controller.key
        dev_changes.append(disk_spec)
        spec.deviceChange = dev_changes
        task = vm.ReconfigVM_Task(spec=spec)
        task.SetTaskDescription(vmodl.LocalizableMessage(key="pyAgora_disk", message="Adding disks"))
        tasks.wait_for_tasks(si, [task])
        self.deployed_disks += 1

    def boot(self, si):
        """
        Boot de la VM
        :param si: service_instance représentant la connexion vcenter
        """
        task = self.vm.PowerOn()
        tasks.wait_for_tasks(si, [task])

    def deploy(self, si, guestRootPassword='aaaaa'):
        """
        Déploiement d'une VM Tat1 étape par étape
        :param si: service_instance représentant la connexion vcenter
        :param guestRootPassword: mot de passe root de la VM
        """
        self.guestRootPassword = guestRootPassword
        self._ovf_deploy(si=si)
        self.resize(nb_cpu=self.nb_cpu, ram=self.ram // 1024, si=si)
        self._update_metadata()
        self._update_ovf_properties(si=si)
        self._connect_switch(si=si)
        self._add_disks(si=si)
        self._correct_cdrom(si=si)
        self.take_snapshot(service_instance=si, snapshot_name="Avant premier boot",
                           description="Snapshot automatique avant premier boot")
        self.boot(si=si)
        self._update_root_pw_on_first_boot(newRootPassword=self.guestRootPassword, si=si)
        self.upgrade_tools(si=si)
        self.rebootAfterReconfig(si=si)
        self._update_annotation(si=si)

    def take_snapshot(self, service_instance, snapshot_name="Snapshot", description=None, dumpMemory=False,
                      quiesce=False):
        """
        Prise d'un snapshot de la VM
        :param service_instance: service_instance représentant la connexion vcenter
        :param snapshot_name: Nom du snapshot
        :param description: Description du snapshot
        :param dumpMemory: Ajout de l'état de la mémoire dans le snapshot ? (défaut : non)
        :param quiesce: Demander un état figé du système de fichier (quiescence) ? (défaut : non)
        """
        vm = self.vm
        task = vm.CreateSnapshot(snapshot_name, description, dumpMemory, quiesce)
        tasks.wait_for_tasks(service_instance, [task])

    def upgrade_tools(self, si):
        """
        Mise à jour des VMware Tools
        :param si: service_instance représentant la connexion vcenter
        """
        # MAJ des agora_tools
        task = self.vm.UpgradeTools()
        tasks.wait_for_tasks(si, [task])

    def rebootAfterReconfig(self, si):
        """
        Reboot à la fin du reconfig (détecté par la présence du fichier /Agora/build/config/code_retour_install)
        :param si: service_instance représentant la connexion vcenter
        """
        # On attend la fin du reconfig
        while True:
            try:
                if 0 == run_command_in_guest(vm=self.vm, command='/usr/bin/test',
                                             arguments="-f /Agora/build/config/code_retour_install",
                                             guestUser='root', guestPassword=self.guestRootPassword, si=si):
                    break
            # On catche l'exception pour éviter de planter en raison des agora_tools pas lancés
            except (vim.fault.GuestOperationsUnavailable):
                pass
            sleep(3)
        # On reboote
        self.vm.RebootGuest()


def main():
    # args = get_args()
    # TODO a remplacer par args une fois le programme fonctionnel
    disks = []
    disks.append(FWAP.ServerDisk(name='/dev/sde', vg="vg_test", lvs="lv_test", partsize=1024,
                                 extra_mem_times_size=0))

    deployment = vmDeploy(ovfpath='D:\VMs\OVF\ovf_53X_64_500u1.ova\ovf_53X_64_500u1.ovf',
                          name='a82aflr03',
                          vcpu=1,
                          ram=1 * 1024 * 1024,
                          lan='LAN Data',
                          cluster='Cluster_Agora',
                          datastore='CEDRE_005',
                          datacenter='Zone LAN AGORA',
                          esx='a82hhot20.agora.msanet',
                          vmfolder='_Autres',
                          ep='I',
                          rds='RXPM',
                          demandeur='Benoit BARTHELEMY',
                          fonction="tests déploiement",
                          eol="Temporaire",
                          vcenter="a82avce02.agora.msanet",
                          disks=disks)
    si = connect_vcenter(vcenter='a82avce02.agora.msanet', user='c82nbar', password='W--Vrtw2016-1')
    res = deployment.deploy(si)

    return res


if __name__ == "__main__":
    exit(main())
