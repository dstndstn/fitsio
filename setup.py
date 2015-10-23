import distutils
from distutils.core import setup, Extension, Command
from distutils.command.build_ext import build_ext

import os
import sys
import numpy
import glob
import shutil
import platform

class build_ext_subclass(build_ext):
    boolean_options = build_ext.boolean_options + ['use-system-fitsio']
    user_options = build_ext.user_options + \
            [('use-system-fitsio', None, 
              "Use the cfitsio installed in the system")]

    def initialize_options(self):
        self.use_system_fitsio = False
        self.cfitsio_build_dir = ""

        self.package_basedir = os.path.abspath(os.curdir)

        #cfitsio_version = '3280patch'
        self.cfitsio_version = '3370patch'
        self.cfitsio_dir = 'cfitsio%s' % self.cfitsio_version
        self.cfitsio_build_dir = os.path.join('build', self.cfitsio_dir)
        self.cfitsio_zlib_dir = os.path.join(self.cfitsio_build_dir,'zlib')
        build_ext.initialize_options(self)    
        self.link_objects = []
        self.extra_link_args = []

    def finalize_options(self):

        build_ext.finalize_options(self)    

        if self.use_system_fitsio:
            # Include bz2 by default?  Depends on how system cfitsio was built.
            # FIXME: use pkg-config to tell if bz2 shall be included ?
            self.extra_link_args.append('-lcfitsio')
        else:
            # We defer configuration of the bundled cfitsio to build_extensions
            # because we will know the compiler there.
            self.include_dirs.append(self.cfitsio_dir)


    def build_extensions(self):
        if not self.use_system_fitsio:

            # Use the compiler for building python to build cfitsio
            # for maximized compatibility.

            self.configure_cfitsio(CC=self.compiler.compiler, 
                              ARCHIVE=self.compiler.archiver, 
                               RANLIB=self.compiler.ranlib)

            # If configure detected bzlib.h, we have to link to libbz2

            if '-DHAVE_BZIP2=1' in open(os.path.join(self.cfitsio_build_dir, 'Makefile')).read():
                self.compiler.add_library('bz2')

            self.compile_cfitsio()

            # when using "extra_objects" in Extension, changes in the objects do *not*
            # cause a re-link!  The only way I know is to force a recompile by removing the
            # directory
            for sofile in glob.glob(os.path.join('build','lib*/fitsio/*_fitsio_wrap*.so*')):
                os.unlink(sofile)

            # link against the .a library in cfitsio; 
            # It should have been a 'static' library of relocatable objects (-fPIC), 
            # since we use the python compiler flags

            link_objects = glob.glob(os.path.join(self.cfitsio_build_dir,'*.a'))

            self.compiler.set_link_objects(link_objects)

        # call the original build_extensions

        build_ext.build_extensions(self)

    def configure_cfitsio(self, CC=None, ARCHIVE=None, RANLIB=None):

        # prepare source code and run configure
        def copy_update(dir1,dir2):
            f1 = os.listdir(dir1)
            for f in f1:
                path1 = os.path.join(dir1,f)
                path2 = os.path.join(dir2,f)

                if os.path.isdir(path1):
                    if not os.path.exists(path2):
                        os.makedirs(path2)
                    copy_update(path1,path2)
                else:
                    if not os.path.exists(path2):
                        shutil.copy(path1,path2)
                    else:
                        stat1 = os.stat(path1)
                        stat2 = os.stat(path2)
                        if (stat1.st_mtime > stat2.st_mtime):
                            shutil.copy(path1,path2)


        if not os.path.exists('build'):
            ret=os.makedirs('build')

        if not os.path.exists(self.cfitsio_build_dir):
            ret=os.makedirs(self.cfitsio_build_dir)

        copy_update(self.cfitsio_dir, self.cfitsio_build_dir)

        makefile = os.path.join(self.cfitsio_build_dir, 'Makefile')

        if os.path.exists(makefile):
            # Makefile already there
            return

        args = ''
        args += ' CC="%s"' % ' '.join(CC[:1])
        args += ' CFLAGS="%s"' % ' '.join(CC[1:])
    
        if ARCHIVE:
            args += ' ARCHIVE="%s"' % ' '.join(ARCHIVE)
        if RANLIB:
            args += ' RANLIB="%s"' % ' '.join(RANLIB)

        os.chdir(self.cfitsio_build_dir)
        ret=os.system('sh ./configure --with-bzip2 ' + args)
        if ret != 0:
            raise ValueError("could not configure cfitsio %s" % self.cfitsio_version)
        os.chdir(self.package_basedir)

    def compile_cfitsio(self):
        os.chdir(self.cfitsio_build_dir)
        ret=os.system('make')
        if ret != 0:
            raise ValueError("could not compile cfitsio %s" % self.cfitsio_version)
        os.chdir(self.package_basedir)


include_dirs=[numpy.get_include()]
    

sources = ["fitsio/fitsio_pywrap.c"]
data_files=[]

ext=Extension("fitsio._fitsio_wrap", 
              sources, include_dirs=include_dirs)

description = ("A full featured python library to read from and "
               "write to FITS files.")

long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read()

classifiers = ["Development Status :: 5 - Production/Stable"
               ,"License :: OSI Approved :: GNU General Public License (GPL)"
               ,"Topic :: Scientific/Engineering :: Astronomy"
               ,"Intended Audience :: Science/Research"
              ]

try:
    from distutils.command.build_py import build_py_2to3 as build_py
except ImportError:
    from distutils.command.build_py import build_py

setup(name="fitsio", 
      version="0.9.7",
      description=description,
      long_description=long_description,
      license = "GPL",
      classifiers=classifiers,
      url="https://github.com/esheldon/fitsio",
      author="Erin Scott Sheldon",
      author_email="erin.sheldon@gmail.com",
      install_requires=['numpy'],
      packages=['fitsio'],
      data_files=data_files,
      ext_modules=[ext],
      cmdclass = {
        "build_py":build_py,
        "build_ext": build_ext_subclass}
     )



