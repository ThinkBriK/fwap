import sys
import tkinter as Tk
from tkinter import ttk

import pyVmomi

import FWAP
import OVF

# CONSTANTES

# Correspndance OS/IMAGE OVF
OS_OVF = {
    "RHEL 5.3": "ovf_53X_64_500u1.ova\ovf_53X_64_500u1.ovf",
    "RHEL 6.3": "ovf_rh63_64bits_500u1-b02.ova\OVF Agora RH6 b02.ovf",
    "Centos 6.5": "ovf_centos65_64bits_500u1-b02\ovf_centos65_64bits_500u1-b02.ovf",
}

DEFAULT_FWAP_FILE = 'http://a82amtl01.agora.msanet/repo/agora/scripts/referentiel.xml'
FWAP_FILES = ['http://a82amtl01.agora.msanet/repo/agora/scripts/referentiel.xml',
              'http://a82amtl02.agora.msanet/repo/agora/scripts/referentiel.xml']


########################################################################
class MyApp(object):
    """"""

    def __init__(self, parent, fwapfile=None):
        """Constructeur"""
        self.si = None
        self.vcenter = None
        self.eol = None
        self.fonction = None
        self.demandeur = None
        self.vmfolder = None
        self.esx = None
        self.datastore = None
        self.lan = None
        self.ram = None
        self.vcpus = None
        self.serverinfo = None
        self.mtl = None
        self.root = parent
        self.root.title("Déploiement TAT1")
        self.frame = ttk.Frame(self.root)
        self.frame.grid()
        if fwapfile:
            self.fwapfile = FWAP.FwapFile(fwapfile)
        else:
            self.fwapfile = FWAP.FwapFile(DEFAULT_FWAP_FILE)
        self.ovf_path = 'D:\VMs\OVF'
        self._create_widgets()

    def _create_widgets(self):
        frame = ttk.Frame(self.frame, name='main')
        frame.grid(row=0, column=0, padx=2, pady=3, rowspan=2)

        recap_frame = ttk.LabelFrame(self.frame, name='recap', text='Paramètres')
        recap_frame.grid(row=0, column=1, padx=2, pady=3)

        handler = lambda: self._onDeploy()
        btn = ttk.Button(self.frame, text="Lancer le déploiement", command=handler, state="disabled", name='deploy')
        btn.grid(row=1, column=1, sticky="S", padx=2, pady=3)

        RequestFrame(app=self, parent=frame)

    def updateParams(self, params_dict):
        """"""
        for key in params_dict.keys():
            setattr(self, key, params_dict[key])
        self.validate()

    def validate(self):
        required_args = ['servername', 'vcpus', 'ram', 'lan', 'os', 'datastore', 'esx', 'vmfolder', 'ep', 'rds',
                         'demandeur',
                         'fonction', 'eol']
        ready = True
        frame_params = self.frame.children['recap']

        for arg in required_args:
            arg_value = None
            if hasattr(self, arg):
                arg_value = getattr(self, arg)
            elif hasattr(self.serverinfo, arg):
                arg_value = str(getattr(self.serverinfo, arg))

            if isinstance(arg_value, pyVmomi.vim.Folder):
                # Cas de l'affichage du dossier
                arg_value = arg_value.__str__()

            # On vérifie que l'argument existe et ait une valeur
            if arg_value is not None and arg_value != '':
                param_text = arg + " : " + str(arg_value)
                # MAJ de la frame des paramètres
                if arg not in frame_params.children:
                    # Ajout d'un nouveau paramètre
                    new_param = ttk.Label(frame_params, text=param_text, name=arg)
                    new_param.grid(sticky='w')
                else:
                    # MAJ d'un paramètre
                    frame_params.children[arg]['text'] = param_text
            else:
                ready = False

        if ready:
            self.frame.children['deploy'].config(state='normal')
        else:
            self.frame.children['deploy'].config(state='disabled')

    def _onDeploy(self):
        deployment = OVF.vmDeploy(
            ovfpath=self.ovf_path + '\\' + OS_OVF.get(self.serverinfo.os),
            name=self.serverinfo.servername,
            vcpu=int(self.vcpus),
            ram=int(self.ram) * 1024 * 1024,
            lan=self.lan,
            datastore=self.datastore,
            esx=self.esx,
            vmfolder=self.vmfolder,
            ep=self.serverinfo.ep,
            rds=self.serverinfo.rds,
            demandeur=self.demandeur,
            fonction=self.fonction,
            eol=self.eol,
            vcenter=self.vcenter,
            disks=self.serverinfo.disks,
            mtl=self.serverinfo.mtl,
            deployer=self.user,
        )

        deployment.deploy(self.si)

    def __repr__(self):
        representation = ''
        for key in self.__dict__.keys():
            if key != 'password':
                representation += key + " : " + str(self.__dict__[key]) + "\n"
            else:
                representation += key + ": ********\n"
        return representation


class AppFrame(ttk.Frame):
    def __init__(self, app, parent, name):
        self.app = app
        super().__init__(parent, name=name)

    def refresh(self):
        pass


class LoginMbox(object):
    # TODO rattacher le popup au meme rootTK
    def __init__(self, caller_frame):
        self.root = Tk.Tk()
        self.root.title("Login vSphere")
        self.root.focus_set()
        self.frame = ttk.Frame(master=self.root, name='login')

        self.caller_frame = caller_frame
        label_vcenter = ttk.Label(self.frame, text="vCenter")
        label_vcenter.grid(row=0, column=0, sticky='W')
        vcombo = ttk.Combobox(self.frame, values=("a82avce02.agora.msanet", "a82avce96.agora.msanet"), width=30)
        vcombo.set("a82avce02.agora.msanet")
        vcombo.grid(row=0, column=1, sticky='NESW')
        vcombo.focus_set()

        label_usr = ttk.Label(self.frame, text="User vCenter")
        label_usr.grid(row=1, column=0, sticky='W')
        usr = ttk.Entry(self.frame, width=30)
        usr.grid(row=1, column=1, sticky='NESW')

        label_pwd = ttk.Label(self.frame, text="Password vCenter")
        label_pwd.grid(row=2, column=0, sticky='W')
        passwd = ttk.Entry(self.frame, show="*", width=30)
        passwd.grid(row=2, column=1, sticky='NESW')

        btn = ttk.Button(self.frame, text="OK", command=lambda: self._onSetViCredentials(vcombo, usr, passwd))
        btn.grid(row=3, column=1, sticky='S', pady=5)
        self.frame.grid()

    def _onSetViCredentials(self, vcenter, usr, passwd):
        try:
            si = OVF.connect_vcenter(vcenter=vcenter.get(), user=usr.get(), password=passwd.get())
        except:
            print(sys.exc_info()[0])
            return
        self.caller_frame.app.updateParams(params_dict={'vcenter': vcenter.get(),
                                                        'password': passwd.get(),
                                                        'user': usr.get(),
                                                        'si': si})
        self.caller_frame.vcLoginOK()
        self.root.destroy()


class RequestFrame(AppFrame):
    def __init__(self, app, parent):
        super().__init__(app=app, parent=parent, name='demande')

        label_ovf_path = ttk.Label(self, text="Répertoire racine des OVF")
        label_ovf_path.grid(row=0, column=0, sticky='NESW')
        self.ovf_path_entry = ttk.Entry(self, width=60, validate='focusout', validatecommand=self._onRequestValidate)
        self.ovf_path_entry.insert(0, 'D:\VMs\OVF')
        self.ovf_path_entry.grid(row=0, column=1, columnspan=3, sticky='NESW')

        label_fwap_path = ttk.Label(self, text="URL du FWAP")
        label_fwap_path.grid(row=1, column=0, sticky='E')

        self.fwap_path_combo = ttk.Combobox(self, width=60, state='normal', values=FWAP_FILES)
        self.fwap_path_combo.current(0)
        self.fwap_path_combo.bind("<<ComboboxSelected>>", self._onUpdateFwapFile)
        self.fwap_path_combo.grid(row=1, column=1, columnspan=3, sticky='NESW')

        label_servCombo = ttk.Label(self, text="Choisissez un serveur")
        label_servCombo.grid(row=2, column=0, sticky='NESW')
        self.servCombo = app.fwapfile.get_tk_combobox(parent=self, width=60, state='normal')
        self.servCombo.grid(row=2, column=1, columnspan=3, sticky='NESW')
        self.servCombo.bind("<<ComboboxSelected>>", self._onRequestValidate)

        sep1 = ttk.Separator(self, orient='horizontal')
        sep1.grid(row=3, column=0, columnspan=5, sticky='NSEW', padx=2, pady=2)

        label_demandeur = ttk.Label(self, text="Demandeur")
        label_demandeur.grid(row=4, column=0, sticky='E')
        self.demandeur_entry = ttk.Entry(self, width=60, validate='all', validatecommand=self._onRequestValidate)
        self.demandeur_entry.grid(row=4, column=1, columnspan=3, sticky='NSEW')

        label_fonction = ttk.Label(self, text="Fonction")
        label_fonction.grid(row=5, column=0, sticky='E')
        self.fonction_entry = ttk.Entry(self, width=60, validate='all', validatecommand=self._onRequestValidate)
        self.fonction_entry.grid(row=5, column=1, columnspan=3, sticky='NSEW')

        label_eol = ttk.Label(self, text="Fin de vie")
        label_eol.grid(row=6, column=0, sticky='E')
        self.eol_entry = ttk.Entry(self, width=30, validate='focusout', validatecommand=self._onRequestValidate)
        self.eol_entry.insert(0, 'Perenne')
        self.eol_entry.grid(row=6, column=1, columnspan=3, sticky='NSEW')

        sep2 = ttk.Separator(self, orient='horizontal')
        sep2.grid(row=7, column=0, columnspan=5, sticky='NSEW', padx=2, pady=2)

        label_vcpu = ttk.Label(self, text="vCPUs")
        label_vcpu.grid(row=8, column=0, sticky='E')
        self.vcpus_spin = Tk.Spinbox(self, from_=1, to=12, width=2)
        self.vcpus_spin.value = 1
        self.vcpus_spin.grid(row=8, column=1, sticky='NSEW')

        label_ram = ttk.Label(self, text="RAM (en GB)")
        label_ram.grid(row=8, column=2, sticky='E')
        self.ram_spin = Tk.Spinbox(self, from_=1, to=64, width=2)
        self.ram_spin.value = 1
        self.ram_spin.grid(row=8, column=3, sticky='NSEW')

        sep3 = ttk.Separator(self, orient='horizontal')
        sep3.grid(row=9, column=0, columnspan=4, sticky='NSEW', padx=2, pady=2)

        self.boutonPopupVC = ttk.Button(self, text="Login vCenter", command=self._onVcPopup)
        self.boutonPopupVC.grid(row=10, column=0, columnspan=4, sticky='NSEW', pady=5)
        self.grid(row=0, column=0)

    def vcLoginOK(self):
        self.boutonPopupVC.config(text="Connecté en tant que " + self.app.user + "@" + self.app.vcenter,
                                  state=Tk.DISABLED)
        self._populateViTree()

    def _onVcPopup(self):
        self._onRequestValidate()
        LoginMbox(self)

    def _onUpdateFwapFile(self, event):
        fwapfile = FWAP.FwapFile(self.fwap_path_combo.get())
        self.app.updateParams(params_dict={'fwapfile': fwapfile})

        servlist = fwapfile.get_serverlist()
        if not servlist is None:
            self.servCombo.set_completion_list(servlist)

    def _onRequestValidate(self, *args):
        self.app.updateParams(params_dict={'ovf_path': self.ovf_path_entry.get(),
                                           'demandeur': self.demandeur_entry.get(),
                                           'fonction': self.fonction_entry.get(),
                                           'eol': self.eol_entry.get(),
                                           'vcpus': self.vcpus_spin.get(),
                                           'ram': self.ram_spin.get()
                                           })
        if self.servCombo.get() != "":
            self.app.serverinfo = self.app.fwapfile.parse(servername=self.servCombo.get())[0]
        self.app.validate()

    def _onUpdateConfig(self, ovf_path, fwap_path):
        self.app.updateParams(params_dict={'ovf_path': ovf_path, 'fwapfile': FWAP.FwapFile(fwap_path)})

    def _populateViTree(self):
        self.viframe = ttk.Frame(self)
        self.viframe.grid(row=11, columnspan=4)
        parent = self.app
        self.tree = ttk.Treeview(self.viframe, selectmode='browse', columns=['RAM', 'CPU'])
        self.tree.column("#0", minwidth=30)
        self.tree.heading("#0", text="Sélectionner un Hôte")
        self.tree.column("RAM", minwidth=10)
        self.tree.heading("RAM", text="RAM Utilisée")
        self.tree.column("CPU", minwidth=10)
        self.tree.heading("CPU", text="CPU Utilisée")
        content = parent.si.RetrieveContent()

        # Datacenters
        for datacenter_element in content.rootFolder.childEntity:
            self._build_host_tree(tree=self.tree, parentid='', element=datacenter_element)

        tree_sb = Tk.Scrollbar(self.viframe, orient="vertical")
        tree_sb.config(command=self.tree.yview)
        self.tree.config(yscrollcommand=tree_sb.set)
        tree_sb.grid(row=0, column=4, sticky="NSW")
        self.tree.grid(row=0, column=0, columnspan=4, sticky='NESW')
        self.tree.bind('<<TreeviewSelect>>', lambda e: self._onChooseDeployServer(e))

    def _build_host_tree(self, tree, parentid, element):
        childlist = []
        elementid = None
        if type(element) == pyVmomi.types.vim.Datacenter:
            elementid = tree.insert(parent=parentid, index='end', text=element.name, values=['', ''])
            childlist = element.hostFolder.childEntity
        elif type(element) == pyVmomi.types.vim.ClusterComputeResource:
            elementid = tree.insert(parent=parentid, index='end', text=element.name, values=['', ''])
            childlist = element.host
        elif type(element) == pyVmomi.types.vim.ComputeResource:
            # On ne fait pas apparaitre les resource Groups dans l'arbre
            elementid = parentid
            childlist = element.host
        elif type(element) == pyVmomi.types.vim.Folder:
            # On ne fait pas apparaitre des folder host des datacenters
            if element.name != 'host':
                elementid = tree.insert(parent=parentid, index='end', text=element.name, values=['', ''])
                childlist = element.childEntity
        elif type(element) == pyVmomi.types.vim.HostSystem and element.runtime.connectionState == 'connected':
            cpu_usage_mhz = element.summary.quickStats.overallCpuUsage
            total_mhz = element.summary.hardware.numCpuCores * element.summary.hardware.cpuMhz
            mem_usage_mo = element.summary.quickStats.overallMemoryUsage
            total_mem_mo = element.summary.hardware.memorySize / 1024 / 1024
            elementid = tree.insert(parent=parentid, index='end', text=element.name,
                                    values=["%4.2f Go (%3.2f %%)" % (mem_usage_mo / 1024,
                                                                     mem_usage_mo / total_mem_mo * 100),
                                            "%3.2f Ghz (%3.2f %%)" % (
                                                cpu_usage_mhz / 1024,
                                                cpu_usage_mhz / total_mhz * 100)])
        for child in childlist:
            self._build_host_tree(tree, elementid, child)

    def _onChooseDeployServer(self, event):
        tree = self.tree
        choix = tree.focus()
        app = self.app

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            app.esx = tree.item(choix)['text']
            app.validate()
            self.populateDetails()

    def populateDetails(self):
        frame = self.viframe
        app = self.app

        content = app.si.RetrieveContent()
        host = OVF.get_obj(content, pyVmomi.vim.HostSystem, app.esx)

        # On détermine le DC de l'hôte
        datacenter_element = host.parent
        while type(datacenter_element) != pyVmomi.types.vim.Datacenter:
            datacenter_element = datacenter_element.parent

        # Ajout d'un séparateur
        separator = ttk.Separator(frame, orient='horizontal')
        separator.grid(row=2, column=0, columnspan=4, sticky='NSEW', pady=6)

        # Récupération des LAN accessibles depuis l'hôte
        lan_label = ttk.Label(frame, text="Choisissez le réseau")
        lan_label.grid(row=3, column=0, sticky="W", padx=3)
        lan_combo = ttk.Combobox(frame, values=[portgroup.spec.name for portgroup in host.config.network.portgroup],
                                 width=30, name='lanCombo')
        lan_combo.grid(row=3, column=1, sticky="NSEW", padx=3)
        lan_combo.bind('<<ComboboxSelected>>', lambda e: self._onViInfoChosen(e))

        # Récupération des Datastores accessibles depuis l'hôte
        datastore_label = ttk.Label(frame, text="Choisissez le datastore")
        datastore_label.grid(row=4, column=3, sticky="S", padx=6)

        datastore_lb = Tk.Listbox(frame, width=30, name='datastoreLb')
        datastore_sb = Tk.Scrollbar(frame, orient="vertical")
        datastore_sb.config(command=datastore_lb.yview)
        datastore_lb.config(yscrollcommand=datastore_sb.set)
        datastore_sb.grid(row=5, column=4, sticky="NSW")
        datastore_lb.grid(row=5, column=3, sticky="NSEW")

        i = 1
        self.datastoretab = []
        for datastore in host.datastore:
            self.datastoretab.append(datastore.info.name)
            datastore_lb.insert(i,
                                datastore.info.name + " (" + str(
                                    int(datastore.info.freeSpace / 1024 / 1024 / 1024)) + " Go libre)")
            i += 1
        datastore_lb.bind('<<ListboxSelect>>', lambda e: self._onViInfoChosen(e))

        # Choix du dossier de la VM
        folder_label = ttk.Label(frame, text="Choisissez le dossier")
        folder_label.grid(row=4, column=0, columnspan=2, sticky="S", padx=6)
        tree = ttk.Treeview(frame, selectmode='browse', name='folderTree')
        tree_sb = Tk.Scrollbar(frame, orient="vertical")
        tree_sb.config(command=tree.yview)
        tree.config(yscrollcommand=tree_sb.set)
        tree.column('#0', minwidth=50)
        if type(datacenter_element) == pyVmomi.types.vim.Datacenter:
            dc_id = tree.insert(parent='', index='end', text=datacenter_element.name, open=True)
            for vmFolder_element in datacenter_element.vmFolder.childEntity:
                self._build_folder_tree(tree, dc_id, vmFolder_element)
        tree_sb.grid(row=5, column=2, sticky="NSW")
        tree.grid(row=5, column=0, columnspan=2, sticky="NSEW")
        tree.bind('<<TreeviewSelect>>', lambda e: self._onViInfoChosen(e))

    def _build_folder_tree(self, tree, parentid, element):
        if type(element) == pyVmomi.types.vim.Folder:
            folderid = tree.insert(parent=parentid, index='end', text=element.name, values=[element._moId])
            for child in element.childEntity:
                self._build_folder_tree(tree, folderid, child)

    def _onViInfoChosen(self, event):
        viframe = self.viframe
        app = self.app
        params = {}
        # Récupération du LAN
        cblanindex = viframe.children['lanCombo'].current()
        if cblanindex > 0:
            params['lan'] = viframe.children['lanCombo'].get()
        # Récupération du Datastore
        lbdsindex = viframe.children['datastoreLb'].curselection()
        if len(lbdsindex) > 0:
            params['datastore'] = self.datastoretab[lbdsindex[0]]
        # Récupération du Folder
        tree = viframe.children['folderTree']
        choix = tree.focus()
        if choix:
            params['vmfolder'] = pyVmomi.types.vim.Folder(tree.item(choix)['values'][0])
        app.updateParams(params)


if __name__ == "__main__":
    root = Tk.Tk()
    root.geometry()
    app = MyApp(root)
    root.mainloop()
