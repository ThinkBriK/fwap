from distutils.core import setup

setup(
    name='agora_deploy',
    packages=['agora_deploy', 'agora_tools'],
    version='0.8.2-beta',
    description='Déploiement de VMs Tat1',
    author='Benoit BARTHELEMY',
    author_email='benoit.barthelemy2@open-groupe.com',
    classifiers=[
        'Programming Language :: Python :: 3',
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'Topic :: Office/Business',
    ],
    requires=['lxml', 'pyVmomi', 'pyVim'],
    url='http://agora.msa.fr',
)
