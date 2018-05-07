#-------------------------------------------------------------------------------
# known bug: 1, Source0/1/2/3 ...  patch0/1/2/3...
# known bug: new package
#-------------------------------------------------------------------------------
from enum import Enum
import re

class Statement(Enum):
    stat_unknown = 0
    stat_blank  =1      # blank / '#'
    stat_common =2      # description / build action....
    stat_attr   =3      # '<attr> : <value>', <attr>: Name, Version, Release, URL....
    stat_desc   =4      # '%description'
    stat_package  =5    # '%package'
    stat_prep     =6    # '%prep'
    stat_build    =7    # '%build'
    stat_install  =8    # '%install'
    stat_file     =9    # '%file'


class Status(Enum):
    desc_unknown = 0
    desc_package = 1    # in stat_package
    desc_desc =2        # in stat_desc
    desc_prep  =3       # in stat_prep
    desc_build   =4     # in stat_build
    desc_install =5     # in stat_install
    desc_file    =6     # in stat_file


__kw_list={
    'description':  (Statement.stat_desc,       Status.desc_desc),
    'package' :     (Statement.stat_package,    Status.desc_package),
    'prep' :        (Statement.stat_prep,       Status.desc_prep),
    'build' :       (Statement.stat_build,      Status.desc_build),
    'install':      (Statement.stat_install,    Status.desc_install),
    'file' :        (Statement.stat_file,       Status.desc_file),
    }

__attr_list_multi=('requires' ,'buildrequires', 'source')
__attr_list_single=('name', 'version', 'release', 'url', 'summary','group', 'license', 'provides')
__attr_list= __attr_list_single + __attr_list_multi


class package:
    def __init__(self, name):  # in: fd
        self.name = name
        self.version = self.release = self.url = self.summary = self.group= self.provides=''
        self.license = ''
        self.source=[] # Source0/1/2/...
        self.requires=[] #
        self.buildrequires=[]
        self.prep_handle = []
        self.build_handle = []
        self.install_handle = []


class specfile:
    def __init__(self, specfn):  #absolute file name
        self.packages=[]


def _is_blank(line):
    if len(line) == 0:
        return True
    if len(line.strip()) == 0:
        return True
    m=re.match('\s*#', line)
    if m is not None:
        return True
    return False

def _is_kw(line):
    for word in __kw_list.keys():
        m=re.match('\s*'+'%'+word, line, re.IGNORECASE)
        if m is not None:
            return __kw_list[word]
    return (Statement.stat_unknown, Status.desc_unknown)


def _set_package_attr(pkg_obj, str_attr, str_value):
#    print("attr = %s, value= %s"%(str_attr, str_value))
    cmd=''
    if str_attr in __attr_list_single :
        if eval('pkg_obj.'+str_attr) != '' :
#            print( eval('pkg_obj.'+str_attr))
            return False
        else:
            cmd='pkg_obj.'+str_attr+'='+ '\'' + str_value +'\''       #'pkg_obj.xxx=yyy'
#            print('cmd is [%s]'%(cmd))
            exec(cmd)
            return True
    if str_attr in __attr_list_multi :
        cmd='pkg_obj.'+str_attr+'.append('+'\''+str_value+'\''+')'   #'pkg_obj.xxx.append(yyy)'
#        print(cmd)
        exec(cmd)
        return True
    print("[DBG] _set_package_attr what is it")
    return False





def _is_attr_setting(line, pkg_obj):
#    p='.*\w+.*:'
#    m=re.match(p,line,re.IGNORECASE)
#    if m is None:
#        print("+++[DBG 0]: "+line)
#        return False
#    str_attr = m.group()[0:-1].strip().lower()
    tmp= line.split(':',1)
    if len(tmp) < 2:                        # Only 1 <==> no ':' ==> invalid
        return False
    str_attr = tmp[0].strip().lower()
    if not str_attr.isalnum() :             # 'aa bb : vv' => invalid
        print("+++[DBG 1] _is_attr_setting: "+line)
        print("str_attr = %s"%(str_attr))
        return False
    if str_attr not in  __attr_list :       #  'xxx: yyy'  => xxx is invalid
        print("+++[DBG 2] _is_attr_setting: "+line)
        return False

#    if len(tmp) > 2 :                       # 'xxx: yyy : zzz'  ==> Maybe is invalid
#        print("+++[DBG 3]: "+line)          # 'url: http://.....'  ==> is valid
#        return False
    str_value = tmp[1].strip().lower()      #
    if str_value == '' :                  # 'xxx:  ' ==> Must be invalid
        print("+++[DBG 4]: _is_attr_setting "+line)
        return False
    return _set_package_attr(pkg_obj, str_attr, str_value)



def stat_maybe_change_state(line, curr_stat):
    if len(line) == 0 :
        return ( False, curr_stat)
    if line.strip()[0] != '%' :
        return ( False,curr_stat)
    (statement, status) = _is_kw(line)
    if statement != Statement.stat_unknown :
        print('[DBG state chagne] %s -> %s'%(curr_stat, status))
        return (True, status )
    else :
        print("[DBG stat_maybe_change_state] %s"%(line))
        return ( False,curr_stat)



def handle_desc_package(line, pkgobj):
    if _is_attr_setting(line, pkgobj) :   # 'xxx:yyy'
        return Status.desc_package
    else:
        print("[DBG handle_desc_package] %s"%(line))
        return Status.desc_package



def handle_desc_desc(line, pkgobj):
    return Status.desc_desc


def handle_desc_prep(line, pkgobj):
    pkgobj.prep_handle.append(line)
    return Status.desc_prep

def handle_desc_build(line, pkgobj):
    pkgobj.build_handle.append(line)
    return Status.desc_build

def handle_desc_install(line, pkgobj):
    pkgobj.build_handle.append(line)
    return Status.desc_build

def handle_desc_file(line,pkgobj):
    pass

def _get_package_name(line):
    return line.strip().split(' ',1)[1]

#parse every line in spec file
def spec_parsefile(f):
    cur_state = Status.desc_package
    main_pkg = cur_pkg = package('')
    spec = specfile('test')
    spec.packages.append(main_pkg)
    for line in f:
        if _is_blank(line):
            continue
        (changed, new_state) = stat_maybe_change_state(line,cur_state)     # '%xxxx'
        if changed :
            if new_state == Status.desc_package :    # new package desc
                new_pkg_name = _get_package_name(line)
                sub_package=package(main_pkg.name+'-'+new_pkg_name)
                cur_pkg=sub_package
                spec.packages.append(sub_package)
            cur_state = new_state
            continue                  # Fixme: need handler deeply
        if cur_state == Status.desc_package :
            cur_state = handle_desc_package(line, cur_pkg)
            continue
        elif cur_state == Status.desc_desc :
            cur_state = handle_desc_desc(line, cur_pkg)
            continue
        elif cur_state == Status.desc_prep :
            cur_state = handle_desc_prep(line, main_pkg)
            continue
        elif cur_state == Status.desc_build :
            cur_state = handle_desc_build(line, main_pkg)
            continue
        elif cur_state == Status.desc_install:
            cur_state = handle_desc_install(line, main_pkg)
            continue
        elif cur_state == Status.desc_file :
            cur_state = handle_desc_file(line, cur_pkg)
            continue
        else:
            print('[DEBUG] : Unknow state')
            continue
    return spec

def main():
    fn = r'sample\\libXfont.spec'
    f=open(fn)
    spec=spec_parsefile(f)
    f.close()

if __name__ == '__main__':
    main()

