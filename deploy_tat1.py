#!/usr/bin/env python
"""
 Ecrit par Benoit BARTHELEMY
 benoit.barthelemy2@open-groupe.com

 Script permettant un déploiement TAT1 à partir d'un fichier FWAP.xml
"""
from argparse import ArgumentParser
from getpass import getpass

from FWAP import FwapFile
from OVF import vmDeploy

# Correspondance OS/IMAGE OVF
os = {
    "RHEL 5.3": "ovf_53X_64_500u1.ova\ovf_53X_64_500u1.ovf",
    "RHEL 6.3": "ovf_rh63_64bits_500u1-b02.ova\OVF Agora RH6 b02.ovf",
    "Centos 6.5": "ovf_centos65_64bits_500u1-b02\ovf_centos65_64bits_500u1-b02.ovf",
}


def get_args():
    """
    Get CLI arguments.
    """
    parser = ArgumentParser(description='Arguments du déploiement TAT1')

    fwap_loc_group = parser.add_mutually_exclusive_group(required=True)

    fwap_loc_group.add_argument('--mtl',
                                required=False,
                                action='store',
                                help='MTL à utiliser')
    parser.add_argument('--name',
                        required=True,
                        action='store',
                        help='VM name (as in FWAP.xml)')
    parser.add_argument('--ovfpath',
                        required=True,
                        action='store',
                        help='Directory containing OVF directories')

    parser.add_argument('--vcenter',
                        required=False,
                        action='store',
                        help='Name of the vCenter to use',
                        default='a82avce02.agora.msanet')

    parser.add_argument('--user',
                        required=True,
                        action='store',
                        help='Vcenter Account')

    parser.add_argument('--password',
                        required=False,
                        action='store',
                        help='Password of the vCenter Account (asked if absent)',
                        )
    parser.add_argument('--datastore',
                        required=True,
                        action='store',
                        help='Name of the Datastore containing the VM',
                        )

    parser.add_argument('--esx',
                        required=True,
                        action='store',
                        help='Name of the ESX host containing the VM',
                        )

    parser.add_argument('--vcpu',
                        required=False,
                        action='store',
                        help='Number of vCPUs for the new VM (default 1)',
                        default=1,
                        type=int,
                        )

    parser.add_argument('--ram',
                        required=False,
                        action='store',
                        help='Size of ram in Go',
                        default=1,
                        type=int,
                        )
    parser.add_argument('--lan',
                        required=False,
                        action='store',
                        help='Name of the LAN to connect the VM to',
                        default="LAN Data",
                        )
    parser.add_argument('--cluster',
                        required=False,
                        action='store',
                        help='Name of the Cluster containing the VM',
                        default="Cluster_Agora",
                        )

    parser.add_argument('--datacenter',
                        required=False,
                        action='store',
                        help='Name of the Datacenter containing the VM',
                        default="Zone LAN AGORA",
                        )

    parser.add_argument('--folder',
                        required=False,
                        action='store',
                        help='Name of the Folder containing the VM',
                        default="_Autres",
                        )

    fwap_loc_group.add_argument('--fwapfile',
                                required=False,
                                action='store',
                                help='FWAP.xml file',
                                )

    args = parser.parse_args()

    if not args.password:
        args.password = getpass(prompt='Enter password: ')

    return args


def main():
    args = get_args()

    # Parsing FWAP.XML
    # http://a82amtl02.agora.msanet/repo/agora/scripts/referentiel.xml
    if args.fwapfile:
        fwap_location = args.fwapfile
    else:
        fwap_location = "http://" + args.mtl + "/repo/agora/scripts/referentiel.xml"
    r = (FwapFile(fwap_location).parse(servername=args.name))[0]
    # r.print()
    # TODO Rajouter la MAJ des tools et la maj des propriétés des VMs!
    deployment = vmDeploy(ovf_path=args.ovfpath + '\\' + os.get(r.os),
                          vm_name=args.name,
                          nb_cpu=args.vcpu,
                          ram=args.ram,
                          lan=args.lan,
                          cluster_name=args.cluster,
                          datastore_name=args.datastore,
                          datacenter_name=args.datacenter,
                          esx_host=args.esx,
                          vm_folder=args.folder,
                          ep=r.ep,
                          rds=r.rds,
                          )
    si = deployment.connect_vcenter(vcenter=args.vcenter, user=args.user, password=args.password)
    deployment.deploy(si)
    for disk in r.disks:
        print(disk)
        # On déploie le disque de la taille des partitions + la taille des partitions sizées sur la RAM (+5% pour EXT3) + 64 M0 (pour LVM)
        kbsize = int(disk.partsize + disk.extra_mem_times_size * (args.ram + 1) * 1024 * 105 / 100 + 64)

        # On arrondi aux 100 Mo supérieur
        if (kbsize % 100) > 0:
            kbrounded = kbsize // 100 + 1
        else:
            kbrounded = kbsize / 100
        deployment.add_disk(disk_size=kbrounded * 100)
    return 0


# Chargement de la fonction Main
if __name__ == "__main__":
    exit(main())
