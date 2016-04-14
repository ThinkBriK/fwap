import sys
import tkinter as Tk
from tkinter import ttk

import pyVmomi

import FWAP
import OVF

# CONSTANTES

# Correspondance OS/IMAGE OVF
os_ovf = {
    "RHEL 5.3": "ovf_53X_64_500u1.ova\ovf_53X_64_500u1.ovf",
    "RHEL 6.3": "ovf_rh63_64bits_500u1-b02.ova\OVF Agora RH6 b02.ovf",
    "Centos 6.5": "ovf_centos65_64bits_500u1-b02\ovf_centos65_64bits_500u1-b02.ovf",
}


# selected_ovfpath = ovfpath + '\\' + os_ovf.get(os_voulu)

########################################################################
class MyApp(object):
    """"""

    def __init__(self, parent, fwapfile):
        """Constructor"""
        self.root = parent
        self.root.title("Déploiement TAT1")
        self.frame = Tk.Frame(self.root)
        self.frame.grid()
        self.fwapfile = FWAP.FwapFile(fwapfile)
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

        self._create_config_tab(nb)
        self._create_vcenter_tab(nb)
        self._create_fwap_tab(nb)
        self._create_request_tab(nb)
        self._create_empty_tab(nb, 'vi', 'Infrastructure VMware')

    def _create_config_tab(self, notebook):
        frame = ttk.Frame(notebook, name='config')
        handler = lambda: self._updateParams(
            params_dict={'ovf_path': ovf_path.get()})

        label_ovf_path = ttk.Label(frame, text="Chemin vers la racine des OVF ")
        label_ovf_path.grid(row=0, column=0, sticky='W')
        ovf_path = ttk.Entry(frame, width=30)
        ovf_path.insert(0, 'D:\VMs\OVF')
        ovf_path.grid(row=0, column=1, sticky='W')

        notebook.add(frame, text='Configuration', padding=2)

    def _create_fwap_tab(self, notebook):
        frame = ttk.Frame(notebook, name='fwap')
        tree = self.fwapfile.get_tk_tree(parent=frame, label="Choisissez un serveur", type='serveur')
        # tree.bind('<<TreeviewSelect>>', self.fwap_select)
        tree.grid(row=0, column=0)

        handler = lambda: self._onFwapSelect(tree)
        boutonOK = ttk.Button(frame, text="OK", command=handler)
        boutonOK.place(anchor='se', relx=.9, rely=.9)
        boutonOK.grid(row=0, column=1, sticky='se')

        # add to notebook (underline = index for short-cut character)
        notebook.add(frame, text='FWAP', padding=2)

    def _create_vcenter_tab(self, notebook):
        """"""
        frame = ttk.Frame(notebook, name='vcenter')
        label_vcenter = Tk.Label(frame, text="vCenter")
        label_vcenter.grid(row=0, column=0, sticky='W')
        vcenter = ttk.Combobox(frame, values=("a82avce02.agora.msanet", "a82avce96.agora.msanet"), width=25)
        vcenter.set("a82avce02.agora.msanet")
        vcenter.grid(row=0, column=1, sticky='W')

        label_usr = Tk.Label(frame, text="User vCenter")
        label_usr.grid(row=1, column=0, sticky='W')
        usr = Tk.Entry(frame, width=25)
        usr.grid(row=1, column=1, sticky='W')

        label_pwd = Tk.Label(frame, text="Password vCenter")
        label_pwd.grid(row=2, column=0, sticky='W')
        passwd = Tk.Entry(frame, show="*", width=25)
        passwd.grid(row=2, column=1, sticky='W')

        handler = lambda: self._onSetViCredentials(vcenter, usr, passwd, notebook)
        btn = Tk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=1, sticky='W')

        notebook.add(frame, text='Connexion vCenter (déconnecté)', padding=2)

    def _create_request_tab(self, notebook):
        # demandeur, fonction, eol

        frame = ttk.Frame(notebook, name='request')
        handler = lambda: self._updateParams(
            params_dict={'demandeur': demandeur.get(), 'fonction': fonction.get(), 'eol': eol.get(),
                         'vcpus': vcpus.get(), 'ram': ram.get()})

        label_demandeur = Tk.Label(frame, text="Demandeur")
        label_demandeur.grid(row=0, column=0, sticky='W')
        demandeur = Tk.Entry(frame, width=30)
        demandeur.grid(row=0, column=1, sticky='W')

        label_fonction = Tk.Label(frame, text="Fonction")
        label_fonction.grid(row=1, column=0, sticky='W')
        fonction = Tk.Entry(frame, width=30)
        fonction.grid(row=1, column=1, sticky='W')

        label_eol = Tk.Label(frame, text="Fin de vie")
        label_eol.grid(row=2, column=0, sticky='W')
        eol = Tk.Entry(frame, width=30)
        eol.insert(0, 'Perenne')
        eol.grid(row=2, column=1, sticky='W')

        sep = ttk.Separator(orient='horizontal')
        sep.grid(row=3, column=0, sticky='W')

        label_vcpu = Tk.Label(frame, text="Entrez le nombre de vCPUs")
        label_vcpu.grid(row=4, column=0, sticky='W')
        vcpus = Tk.Spinbox(frame, from_=1, to=12)
        vcpus.value = 1
        vcpus.grid(row=4, column=1, sticky='W')

        label_ram = Tk.Label(frame, text="RAM en GB")
        label_ram.grid(row=5, column=0, sticky='W')
        ram = Tk.Spinbox(frame, from_=1, to=64)
        ram.value = 1
        ram.grid(row=5, column=1, sticky='W')

        btn = Tk.Button(frame, text="OK", command=handler)
        btn.grid(row=6, column=1, sticky='W')

        notebook.add(frame, text='Demande', padding=2)

    def _create_empty_tab(self, notebook, name, text):
        frame = ttk.Frame(notebook, name=name)
        notebook.add(frame, text=text, padding=2, state='disabled')

    def _build_folder_tree(self, tree, parentid, element):
        if type(element) == pyVmomi.types.vim.Folder:
            folderid = tree.insert(parent=parentid, index='end', text=element.name)
            for child in element.childEntity:
                self._build_folder_tree(tree, folderid, child)

    def _populate_videtails_tab(self, notebook):

        # TODO vérifier que les éléments n'existent pas afin d'éviter de les dupliquer !
        frame = notebook.children['vi']

        content = self.si.RetrieveContent()
        host = OVF.get_obj(content, pyVmomi.vim.HostSystem, self.esx)

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
        tree.column("#0", minwidth=30)
        tree.heading("#0", text="Sélectionner un Dossier")
        for datacenter_element in content.rootFolder.childEntity:
            if type(datacenter_element) == pyVmomi.types.vim.Datacenter:
                dc_id = tree.insert(parent='', index='end', text=datacenter_element.name)
                for vmFolder_element in datacenter_element.vmFolder.childEntity:
                    self._build_folder_tree(tree, dc_id, vmFolder_element)
        tree.grid(row=2, column=3, sticky="NSEW", padx=3)

        # Bouton de validation
        handler = lambda: self._onViInfoChosen(notebook=notebook, datastore_list=datastores_tab)
        btn = Tk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=3, sticky='NESW', padx=3)

    def _populate_vi_tab(self, notebook):
        frame = notebook.children['vi']
        tree = ttk.Treeview(frame, selectmode='browse')
        tree.column("#0", minwidth=30)
        tree.heading("#0", text="Sélectionner un Hôte")
        content = self.si.RetrieveContent()
        # TODO Remplacer l'alimentation de l'arbre vmware par une fonction récursive
        # Datacenters
        for datacenter_element in content.rootFolder.childEntity:
            if type(datacenter_element) == pyVmomi.types.vim.Datacenter:
                dc_id = tree.insert(parent='', index='end', text=datacenter_element.name)
                # Clusters
                for host_element in datacenter_element.hostFolder.childEntity:
                    if type(host_element) == pyVmomi.types.vim.ComputeResource:
                        host_id = tree.insert(parent=dc_id, index='end', text=host_element.name)
                    elif type(host_element) == pyVmomi.types.vim.ClusterComputeResource:
                        cluster_id = tree.insert(parent=dc_id, index='end', text=host_element.name)
                        for cluster_member in host_element.host:
                            host_id = tree.insert(parent=cluster_id, index='end', text=cluster_member.name)
                    elif type(host_element) == pyVmomi.types.vim.Folder:
                        folder_id = tree.insert(parent=dc_id, index='end', text=host_element.name)
                        for folder_member in host_element.childEntity:
                            if type(folder_member) == pyVmomi.types.vim.ComputeResource:
                                host_id = tree.insert(parent=folder_id, index='end', text=folder_member.name)
                            elif type(folder_member) == pyVmomi.types.vim.ClusterComputeResource:
                                cluster_id = tree.insert(parent=folder_id, index='end', text=folder_member.name)
                                for cluster_member in folder_member.host:
                                    host_id = tree.insert(parent=cluster_id, index='end', text=cluster_member.name)
        tree.grid(row=0, rowspan=3, column=0, sticky='NESW')
        handler = lambda: self._onChooseDeployServer(tree=tree, notebook=notebook)
        btn = Tk.Button(frame, text="OK", command=handler)
        btn.grid(row=3, column=0, sticky='NESW')

    def _onChooseDeployServer(self, tree, notebook):
        choix = tree.focus()

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            self.esx = tree.item(choix)['text']
            self.validate()
            self._populate_videtails_tab(notebook)

    def _onDeploy(self):
        deployment = OVF.vmDeploy(
            ovfpath=self.ovf_path + '\\' + os_ovf.get(self.serverinfo.os),
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
        )
        res = deployment.deploy(self.si)

    def _onFwapSelect(self, tree):
        choix = tree.focus()

        # On vérifie qu'on soit bien sur un serveur (feuille)
        if len(tree.get_children(choix)) == 0:
            name = tree.item(choix)['text']
            self.serverinfo = self.fwapfile.parse(servername=name)[0]
            self.validate()

    def _onSetViCredentials(self, vcenter, usr, passwd, notebook):
        try:
            si = OVF.connect_vcenter(vcenter=vcenter.get(), user=usr.get(), password=passwd.get())
        except:
            print(sys.exc_info()[0])
            notebook.tab('current', text='Connexion vCenter (erreur)')
            notebook.tab(len(notebook.children) - 1, state="disabled")
            return
        self._updateParams(
            params_dict={'vcenter': vcenter.get(), 'password': passwd.get(), 'user': usr.get(), 'si': si})
        notebook.tab('current', text='Connexion vCenter (OK)')
        notebook.tab(len(notebook.children) - 1, state="normal")
        self._populate_vi_tab(notebook)

    def _onViInfoChosen(self, notebook, datastore_list):
        frame = notebook.children['vi']
        params = {}
        # Récupération du LAN
        params['lan'] = frame.children['lanCombo']['values'][frame.children['lanCombo'].current()]
        # Récupération du Datastore
        params['datastore'] = datastore_list[frame.children['datastoreCombo'].current()]
        # Récupération du Folder
        tree = frame.children['folderTree']
        choix = tree.focus()
        params['vmfolder'] = tree.item(choix)['text']
        self._updateParams(params)

    def _updateParams(self, params_dict):
        """"""
        for key in params_dict.keys():
            setattr(self, key, params_dict[key])
        self.validate()

    def __repr__(self):
        representation = ''
        for key in self.__dict__.keys():
            if key != 'password':
                representation += key + " : " + str(self.__dict__[key]) + "\n"
            else:
                representation += key + ": ********\n"
        return representation

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
                    frame_params.children[arg].text = param_text

        if ready:
            self.frame.children['deploy'].config(state='normal')


if __name__ == "__main__":
    root = Tk.Tk()
    root.geometry()
    app = MyApp(root, 'files/FWAP.xml')
    root.mainloop()

    # TODO Passer ovfpath en params
