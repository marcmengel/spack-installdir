
import os
import sys
import json

import ruamel.yaml
import spack.main
import spack.spec
import spack.store
import spack.hooks
import spack.hooks.module_file_generation


def get_tuple():
    host_platform = spack.platforms.host()
    host_os = host_platform.operating_system('default_os')
    host_target = host_platform.target('default_target')
    generic_target = host_platform.target('fe').microarchitecture.generic.name
    return (str(host_platform), str(host_os), str(generic_target))


def run_command(s):
    print("--> running: %s" % s)
    os.system(s)


def get_compiler():
    f = os.popen("spack compiler list", "r")
    for line in f:
        comp = line
    f.close()
    return comp.strip()


def make_repo_if_needed( name ):
    f = os.popen("spack repo list","r")
    for line in f:
        if line.find(name+" ") == 0:
             f.close()
             rd = line[line.rfind(" "):].strip()
             return rd
    f.close()
    rd="%s/var/spack/repos/%s" % (os.environ["SPACK_ROOT"], name)
    run_command("spack repo create %s %s" % (rd, name))
    run_command("spack repo add --scope=site %s" % rd)
    return rd


def make_recipe( namespace, name, version, tarfile,  pathvar='IGNORE'):

    rd = make_repo_if_needed(namespace)

    # rewrite recipe if present with new tarfile...

    print( "pfile: %s/packages/%s/package.py" % (rd, name))
    if os.path.exists( "%s/packages/%s/package.py" % (rd, name)):
        print("saving recipe")
        os.rename( 
             "%s/packages/%s/package.py" % (rd, name),
             "%s/packages/%s/package.py.save" % (rd, name),
        )

    f = os.popen("unset VISUAL; EDITOR=/bin/ed spack create -N %s --template generic --name %s > /dev/null 2>&1" % (namespace, name), "w")
    dict = {
       'name': name, 
       'NAME': name.upper().replace('-','_'), 
       'version': version,
       'tarfile': tarfile,
       'PATHVAR' : pathvar
    }
    f.write("""
g/FIXME:/d
/^class/a
    '''declare-simple %(name)s locally declared bundle of files you do not really build'''
.
/homepage *=/s;=.*;= 'https://nowhere.org/nosuch/';
/url *=/s;=.*;= 'file://%(tarfile)s'
/url *=/+2,\$d
a

    version('%(version)s')

    def url_for_version(self,version):
        url = 'file:///tmp/%(name)s.v{0}.tgz'
        return url.format(version)

    def install(self, spec, prefix):
        install_tree(self.stage.source_path, prefix)

    def setup_run_environment(self, run_env):
        run_env.set('%(NAME)s_DIR', self.prefix)
        run_env.prepend_path('%(PATHVAR)s', self.prefix)
.
.+1,$d
wq
""" % dict)
    f.close()

def make_tarfile(directory, name,version):
    if directory:
       directory = f"cd {directory} &&"
    else:
       directory = ""
    tfn = "/tmp/%s.v%s.tgz" % (name, version)
    os.system(f"{directory} tar czvf %s ." % tfn)
    return tfn

    
def restore_recipe( namespace, name ):

    rd = make_repo_if_needed(namespace)

    # restore recipe if present with new tarfile...

    print( "pfile: %s/packages/%s/package.py" % (rd, name))
    if os.path.exists( "%s/packages/%s/package.py.save" % (rd, name)):
        print("restoring recipe")
        os.rename( 
             "%s/packages/%s/package.py.save" % (rd, name),
             "%s/packages/%s/package.py" % (rd, name),
        )

def install_directory(args):
    name, version = args.spec.replace("=","").split("@")
    tfn = make_tarfile(args.directory,name,version)
    make_recipe(args.namespace, name, version, tfn,  'PATH')
    os.system("spack install --no-checksum %s@%s" % (name, version))
    restore_recipe(args.namespace, name)
