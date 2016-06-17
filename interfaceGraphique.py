import sys
import tkinter as Tk
from tkinter import ttk

import pyVmomi

import FWAP
import OVF

# CONSTANTES

# Correspondance OS/IMAGE OVF
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
        """Constructor"""
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
        # create the notebook
        nb = ttk.Notebook(self.frame, name='notebook')
        nb.enable_traversal()
        nb.grid(row=0, column=0, padx=2, pady=3, rowspan=2)

        recap_frame = ttk.LabelFrame(self.frame, name='recap', text='Paramètres')
        recap_frame.grid(row=0, column=1, padx=2, pady=3)

        handler = lambda: self._onDeploy()
        btn = ttk.Button(self.frame, text="Lancer le déploiement", command=handler, state="disabled", name='deploy')
        btn.grid(row=1, column=1, sticky="S", padx=2, pady=3)

        self.tabs = []

        self.tabs.append(RequestTab(app=self, notebook=nb))
        self.tabs.append(VcenterTab(app=self, notebook=nb))
        self.tabs.append(VirtualInfraTab(app=self, notebook=nb))

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
            param_text = ''
            if not hasattr(self, arg):
                if not hasattr(self, 'serverinfo'):
                    ready = False
                else:
                    if not hasattr(self.serverinfo, arg):
                        ready = False
                    else:
                        param_text = arg + " : " + str(getattr(self.serverinfo, arg))
            else:
                param_text = arg + " : " + str(getattr(self, arg))

            if not param_text == '':
                # MAJ de la frame des paramètres
                if arg not in frame_params.children:
                    # Ajout d'un nouveau paramètre
                    new_param = ttk.Label(frame_params, text=param_text, name=arg)
                    new_param.grid(sticky='w')
                else:
                    # MAJ d'un paramètre
                    frame_params.children[arg]['text'] = param_text

                    # frame_params.

        if ready:
            self.frame.children['deploy'].config(state='normal')

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
            mtl=self.serverinfo.mtl
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


class AppTab(ttk.Frame):
    def __init__(self, app, notebook, name):
        self.app = app
        super().__init__(notebook, name=name)

    def refresh(self):
        pass


class LoginMbox(ttk.Frame):
    def __init__(self, parent):
        ttk.Frame.__init__(parent)

    def _onSetViCredentials(self, vcenter, usr, passwd):
        try:
            si = OVF.connect_vcenter(vcenter=vcenter.get(), user=usr.get(), password=passwd.get())
        except:
            print(sys.exc_info()[0])
            return
        self.parent.app.updateParams(params_dict={'vcenter': vcenter.get(),
                                                  'password': passwd.get(),
                                                  'user': usr.get(),
                                                  'si': si})
        self.parent._populate_vi_tab()


class RequestTab(AppTab):
    def __init__(self, app, notebook):
        super().__init__(app=app, notebook=notebook, name='demande')

        label_ovf_path = ttk.Label(self, text="Répertoire racine des OVF")
        label_ovf_path.grid(row=0, column=0, sticky='E')
        self.ovf_path = ttk.Entry(self, width=60)
        self.ovf_path.insert(0, 'D:\VMs\OVF')
        self.ovf_path.grid(row=0, column=1, columnspan=3, sticky='NESW')

        label_fwap_path = ttk.Label(self, text="URL du FWAP")
        label_fwap_path.grid(row=1, column=0, sticky='E')

        self.fwap_path = ttk.Combobox(self, width=60, state='normal', values=FWAP_FILES)
        self.fwap_path.current(0)
        self.fwap_path.bind("<<ComboboxSelected>>", self._onUpdateFwapFile)
        self.fwap_path.grid(row=1, column=1, columnspan=3, sticky='W')

        label_servCombo = ttk.Label(self, text="Choisissez un serveur")
        label_servCombo.grid(row=2, column=0, sticky='E')

        self.servCombo = app.fwapfile.get_tk_combobox(parent=self, width=60, state='normal')
        self.servCombo.grid(row=2, column=1, columnspan=3, sticky='W')

        sep1 = ttk.Separator(self, orient='horizontal')
        sep1.grid(row=3, column=0, columnspan=5, sticky='NSEW', padx=2, pady=2)

        label_demandeur = ttk.Label(self, text="Demandeur")
        label_demandeur.grid(row=4, column=0, sticky='E')
        self.demandeur = ttk.Entry(self, width=60)
        self.demandeur.grid(row=4, column=1, columnspan=3, sticky='NSEW')

        label_fonction = ttk.Label(self, text="Fonction")
        label_fonction.grid(row=5, column=0, sticky='E')
        self.fonction = ttk.Entry(self, width=60)
        self.fonction.grid(row=5, column=1, columnspan=3, sticky='NSEW')

        label_eol = ttk.Label(self, text="Fin de vie")
        label_eol.grid(row=6, column=0, sticky='E')
        self.eol = ttk.Entry(self, width=30)
        self.eol.insert(0, 'Perenne')
        self.eol.grid(row=6, column=1, columnspan=3, sticky='NSEW')

        sep2 = ttk.Separator(self, orient='horizontal')
        sep2.grid(row=7, column=0, columnspan=5, sticky='NSEW', padx=2, pady=2)

        label_vcpu = ttk.Label(self, text="vCPUs")
        label_vcpu.grid(row=8, column=0, sticky='E')
        self.vcpus = Tk.Spinbox(self, from_=1, to=12, width=2)
        self.vcpus.value = 1
        self.vcpus.grid(row=8, column=1, sticky='NSEW')

        label_ram = ttk.Label(self, text="RAM (en GB)")
        label_ram.grid(row=8, column=2, sticky='E')
        self.ram = Tk.Spinbox(self, from_=1, to=64, width=2)
        self.ram.value = 1
        self.ram.grid(row=8, column=3, sticky='NSEW')

        sep3 = ttk.Separator(self, orient='horizontal')
        sep3.grid(row=9, column=0, columnspan=4, sticky='NSEW', padx=2, pady=2)

        boutonPopupVC = ttk.Button(self, text="Login vCenter", command="")
        boutonPopupVC.grid(row=10, column=0, columnspan=4, sticky='NSEW', pady=5)

        notebook.add(self, text='Demande', padding=2)

    def _onUpdateFwapFile(self, event):
        fwapfile = FWAP.FwapFile(self.fwap_path.get())
        self.app.updateParams(params_dict={'fwapfile': fwapfile})

        servlist = fwapfile.get_serverlist()
        if not servlist is None:
            self.servCombo.set_completion_list(servlist)

    def _onRequestValidate(self):
        self.app.updateParams(params_dict={'ovf_path': self.ovf_path,
                                           'demandeur': self.demandeur.get(),
                                           'fonction': self.fonction.get(),
                                           'eol': self.eol.get(),
                                           'vcpus': self.vcpus.get(),
                                           'ram': self.ram.get()
                                           })
        self.app.serverinfo = self.app.fwapfile.parse(servername=self.servCombo.get())[0]
        self.app.validate()

    def _onUpdateConfig(self, ovf_path, fwap_path):
        self.app.updateParams(params_dict={'ovf_path': ovf_path, 'fwapfile': FWAP.FwapFile(fwap_path)})

    def populateViTree(self):
        frame = self
        parent = self.app
        tree = ttk.Treeview(frame, selectmode='browse', columns=['RAM', 'CPU'])
        tree.column("#0", minwidth=30)
        tree.heading("#0", text="Sélectionner un Hôte")
        tree.column("RAM", minwidth=10)
        tree.heading("RAM", text="RAM Utilisée")
        tree.column("CPU", minwidth=10)
        tree.heading("CPU", text="CPU Utilisée")
        content = parent.si.RetrieveContent()
        # TODO Remplacer l'alimentation de l'arbre vmware par une fonction récursive

        # Datacenters
        for datacenter_element in content.rootFolder.childEntity:
            self._build_host_tree(tree=tree, parentid='', element=datacenter_element)
        tree.grid(row=0, rowspan=3, column=0, sticky='NESW')

        handler = lambda: self._onChooseDeployServer(tree=tree)
        btn = ttk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=0, sticky='S', pady=5)

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
        elif type(
                element) == pyVmomi.types.vim.HostSystem and element.runtime.connectionState == 'connected':
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

    def _onChooseDeployServer(self, tree):
        choix = tree.focus()
        app = self.app

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            app.esx = tree.item(choix)['text']
            app.validate()
            self.populateDetails()

    def populateDetails(self):
        frame = self
        app = self.app

        content = app.si.RetrieveContent()
        host = OVF.get_obj(content, pyVmomi.vim.HostSystem, app.esx)

        # On détermine le DC de l'hôte
        datacenter_element = host.parent
        while type(datacenter_element) != pyVmomi.types.vim.Datacenter:
            datacenter_element = datacenter_element.parent

        # Ajout d'un séparateur
        separator = ttk.Separator(frame, orient='vertical')
        separator.grid(row=0, column=1, rowspan=4, sticky='NSEW', padx=3)

        # Récupération des LAN accessibles depuis l'hôte
        lan_label = ttk.Label(frame, text="Choisissez le réseau")
        lan_label.grid(row=0, column=2, sticky="W", padx=3)
        lan_combo = ttk.Combobox(frame, values=[portgroup.spec.name for portgroup in host.config.network.portgroup],
                                 width=30, name='lanCombo')
        lan_combo.grid(row=0, column=3, sticky="NSEW", padx=3)

        # Récupération des Datastores accessibles depuis l'hôte
        datastore_label = ttk.Label(frame, text="Choisissez le datastore")
        datastore_label.grid(row=1, column=2, sticky="W", padx=3)
        display_choices = []
        datastores_tab = []

        for datastore in host.datastore:
            valeur = datastore.info.name + " (" + str(int(datastore.info.freeSpace / 1024 / 1024 / 1024)) + " Go libre)"
            display_choices.append(valeur)
            datastores_tab.append(datastore.info.name)
        datastore_combo = ttk.Combobox(frame, values=display_choices, width=30, name='datastoreCombo')
        datastore_combo.grid(row=1, column=3, sticky="NSEW", padx=3)

        # Choix du dossier de la VM
        folder_label = ttk.Label(frame, text="Choisissez le dossier")
        folder_label.grid(row=2, column=2, sticky="W", padx=3)
        tree = ttk.Treeview(frame, selectmode='browse', name='folderTree')
        tree.column('#0', minwidth=30)
        tree.heading('#0', text="Sélectionner un Dossier")
        if type(datacenter_element) == pyVmomi.types.vim.Datacenter:
            dc_id = tree.insert(parent='', index='end', text=datacenter_element.name, open=True)
            for vmFolder_element in datacenter_element.vmFolder.childEntity:
                self._build_folder_tree(tree, dc_id, vmFolder_element)
        tree.grid(row=2, column=3, sticky="NSEW", padx=3)

        # Bouton de validation
        handler = lambda: self._onViInfoChosen(datastore_list=datastores_tab)
        btn = ttk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=3, sticky='S', pady=5, padx=3)

    def _build_folder_tree(self, tree, parentid, element):
        if type(element) == pyVmomi.types.vim.Folder:
            folderid = tree.insert(parent=parentid, index='end', text=element.name, values=[element._moId])
            for child in element.childEntity:
                self._build_folder_tree(tree, folderid, child)

    def _onViInfoChosen(self, datastore_list):
        frame = self
        app = self.app
        params = {}
        # Récupération du LAN
        params['lan'] = frame.children['lanCombo']['values'][frame.children['lanCombo'].current()]
        # Récupération du Datastore
        params['datastore'] = datastore_list[frame.children['datastoreCombo'].current()]
        # Récupération du Folder
        tree = frame.children['folderTree']
        choix = tree.focus()
        params['vmfolder'] = pyVmomi.types.vim.Folder(tree.item(choix)['values'][0])
        app.updateParams(params)


class VcenterTab(AppTab):
    def __init__(self, app, notebook):
        super().__init__(app=app, notebook=notebook, name='vcenter')
        label_vcenter = ttk.Label(self, text="vCenter")
        label_vcenter.grid(row=0, column=0, sticky='W')
        vcenter = ttk.Combobox(self, values=("a82avce02.agora.msanet", "a82avce96.agora.msanet"), width=30)
        vcenter.set("a82avce02.agora.msanet")
        vcenter.grid(row=0, column=1, sticky='NESW')

        label_usr = ttk.Label(self, text="User vCenter")
        label_usr.grid(row=1, column=0, sticky='W')
        usr = ttk.Entry(self, width=30)
        usr.grid(row=1, column=1, sticky='NESW')

        label_pwd = ttk.Label(self, text="Password vCenter")
        label_pwd.grid(row=2, column=0, sticky='W')
        passwd = ttk.Entry(self, show="*", width=30)
        passwd.grid(row=2, column=1, sticky='NESW')

        handler = lambda: self._onSetViCredentials(vcenter, usr, passwd, notebook)
        btn = ttk.Button(self, text="OK", command=handler)
        btn.grid(row=3, column=1, sticky='S', pady=5)

        notebook.add(self, text='Connexion vCenter (déconnecté)', padding=2)

    def _onSetViCredentials(self, vcenter, usr, passwd, notebook):
        parent = self.app
        try:
            si = OVF.connect_vcenter(vcenter=vcenter.get(), user=usr.get(), password=passwd.get())
        except:
            print(sys.exc_info()[0])
            notebook.tab('current', text='Connexion vCenter (erreur)')
            notebook.tab(len(notebook.children) - 1, state="disabled")
            return
        parent.updateParams(
            params_dict={'vcenter': vcenter.get(), 'password': passwd.get(), 'user': usr.get(), 'si': si})
        notebook.tab('current', text='Connexion vCenter (OK)')
        # TODO Arriver à référencer l'onglet à réactiver autrement que par un index fixe !
        notebook.tab(len(notebook.children) - 1, state="normal")
        self._populate_vi_tab()

    def _populate_vi_tab(self):
        for tab in self.app.tabs:
            if isinstance(tab, VirtualInfraTab):
                tab.populateViTree()
                break

    def refresh(self):
        app = self.app
        tree = self.children['fwaptree']

        # On vide le TreeView
        if len(tree.get_children()) > 0:
            for child in tree.get_children():
                tree.delete(child)

        if hasattr(app, 'fwapfile'):
            tree = app.fwapfile.get_tk_tree(parent=self, label="Choisissez un serveur", type='serveur', name='fwaptree')
        else:
            tree = ttk.Treeview(master=self, name='fwaptree')

        tree.grid(row=0, column=0)

    def _onFwapSelect(self, tree):
        app = self.app
        choix = tree.focus()

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            name = tree.item(choix)['text']
            app.serverinfo = app.fwapfile.parse(servername=name)[0]
            app.validate()


class VirtualInfraTab(AppTab):
    def __init__(self, app, notebook):
        super().__init__(app=app, notebook=notebook, name='vi')
        notebook.add(self, text='Infrastructure VMware', padding=2, state='disabled')

    def populateViTree(self):
        frame = self
        parent = self.app
        tree = ttk.Treeview(frame, selectmode='browse', columns=['RAM', 'CPU'])
        tree.column("#0", minwidth=30)
        tree.heading("#0", text="Sélectionner un Hôte")
        tree.column("RAM", minwidth=10)
        tree.heading("RAM", text="RAM Utilisée")
        tree.column("CPU", minwidth=10)
        tree.heading("CPU", text="CPU Utilisée")
        content = parent.si.RetrieveContent()
        # TODO Remplacer l'alimentation de l'arbre vmware par une fonction récursive

        # Datacenters
        for datacenter_element in content.rootFolder.childEntity:
            self._build_host_tree(tree=tree, parentid='', element=datacenter_element)
        tree.grid(row=0, rowspan=3, column=0, sticky='NESW')

        handler = lambda: self._onChooseDeployServer(tree=tree)
        btn = ttk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=0, sticky='S', pady=5)

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
        elif type(
                element) == pyVmomi.types.vim.HostSystem and element.runtime.connectionState == 'connected':
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

    def _onChooseDeployServer(self, tree):
        choix = tree.focus()
        app = self.app

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            app.esx = tree.item(choix)['text']
            app.validate()
            self.populateDetails()

    def populateDetails(self):
        frame = self
        app = self.app

        content = app.si.RetrieveContent()
        host = OVF.get_obj(content, pyVmomi.vim.HostSystem, app.esx)

        # On détermine le DC de l'hôte
        datacenter_element = host.parent
        while type(datacenter_element) != pyVmomi.types.vim.Datacenter:
            datacenter_element = datacenter_element.parent

        # Ajout d'un séparateur
        separator = ttk.Separator(frame, orient='vertical')
        separator.grid(row=0, column=1, rowspan=4, sticky='NSEW', padx=3)

        # Récupération des LAN accessibles depuis l'hôte
        lan_label = ttk.Label(frame, text="Choisissez le réseau")
        lan_label.grid(row=0, column=2, sticky="W", padx=3)
        lan_combo = ttk.Combobox(frame, values=[portgroup.spec.name for portgroup in host.config.network.portgroup],
                                 width=30, name='lanCombo')
        lan_combo.grid(row=0, column=3, sticky="NSEW", padx=3)

        # Récupération des Datastores accessibles depuis l'hôte
        datastore_label = ttk.Label(frame, text="Choisissez le datastore")
        datastore_label.grid(row=1, column=2, sticky="W", padx=3)
        display_choices = []
        datastores_tab = []

        for datastore in host.datastore:
            valeur = datastore.info.name + " (" + str(int(datastore.info.freeSpace / 1024 / 1024 / 1024)) + " Go libre)"
            display_choices.append(valeur)
            datastores_tab.append(datastore.info.name)
        datastore_combo = ttk.Combobox(frame, values=display_choices, width=30, name='datastoreCombo')
        datastore_combo.grid(row=1, column=3, sticky="NSEW", padx=3)

        # Choix du dossier de la VM
        folder_label = ttk.Label(frame, text="Choisissez le dossier")
        folder_label.grid(row=2, column=2, sticky="W", padx=3)
        tree = ttk.Treeview(frame, selectmode='browse', name='folderTree')
        tree.column('#0', minwidth=30)
        tree.heading('#0', text="Sélectionner un Dossier")
        if type(datacenter_element) == pyVmomi.types.vim.Datacenter:
            dc_id = tree.insert(parent='', index='end', text=datacenter_element.name, open=True)
            for vmFolder_element in datacenter_element.vmFolder.childEntity:
                self._build_folder_tree(tree, dc_id, vmFolder_element)
        tree.grid(row=2, column=3, sticky="NSEW", padx=3)

        # Bouton de validation
        handler = lambda: self._onViInfoChosen(datastore_list=datastores_tab)
        btn = ttk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=3, sticky='S', pady=5, padx=3)

    def _build_folder_tree(self, tree, parentid, element):
        if type(element) == pyVmomi.types.vim.Folder:
            folderid = tree.insert(parent=parentid, index='end', text=element.name, values=[element._moId])
            for child in element.childEntity:
                self._build_folder_tree(tree, folderid, child)

    def _onViInfoChosen(self, datastore_list):
        frame = self
        app = self.app
        params = {}
        # Récupération du LAN
        params['lan'] = frame.children['lanCombo']['values'][frame.children['lanCombo'].current()]
        # Récupération du Datastore
        params['datastore'] = datastore_list[frame.children['datastoreCombo'].current()]
        # Récupération du Folder
        tree = frame.children['folderTree']
        choix = tree.focus()
        params['vmfolder'] = pyVmomi.types.vim.Folder(tree.item(choix)['values'][0])
        app.updateParams(params)


if __name__ == "__main__":
    root = Tk.Tk()
    root.geometry()
    app = MyApp(root)
    root.mainloop()
