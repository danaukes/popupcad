# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
import PySide.QtGui as qg
import popupcad

class FileMissing(Exception):
    def __init__(self,filename):
        super(FileMissing,self).__init__('Child File Missing:{filename}'.format(filename=filename) )

def buildfilters(filetypes,defaultfiletype):
    filters = {}
    for filetype,name in filetypes.items():
        filters[filetype] = '{0}(*.{1})'.format(name,filetype)
    filterstring = ''.join([item+';;' for item in filters.values()])
    selectedfilter=filters[defaultfiletype]
    return filters,filterstring,selectedfilter


class GenericFile(object):
    filetypes = {'file':'Generic File'}
    defaultfiletype = 'file'
    _lastdir = '.'
    def get_basename(self):
        try:
            return self._basename
        except AttributeError:
            self._basename = self.genbasename()
            return self._basename

    def copy(self,identical = True):
        new = type(self)()
        self.copy_file_params(new,identical)
        return new

    def upgrade(self):
        return self.copy()

    @classmethod
    def lastdir(cls):
        return cls._lastdir

    @classmethod
    def setlastdir(cls,directory):
        cls._lastdir = directory

    @classmethod
    def get_parent_program_name(self):
        return None
        
    @classmethod
    def get_parent_program_version(self):
        return None

    def copy_file_params(self,new,identical):
        try:
            new.dirname = self.dirname
        except AttributeError:
            pass

        try:
            if identical:
                new.set_basename(self.get_basename())
            else:
                new.set_basename(new.genbasename())
        except AttributeError:
            pass
        
        try:
            new.parent_program_name = self.parent_program_name
        except AttributeError:
            pass
        try:
            new.parent_program_version = self.parent_program_version
        except AttributeError:
            pass

        return new

    def genbasename(self):
        basename = str(self.id)+'.'+self.defaultfiletype
        return basename

    def set_basename(self,basename):
        self._basename = basename

    def _buildfilters(*args):
        return buildfilters(*args)
    filters,filterstring,selectedfilter = buildfilters(filetypes,defaultfiletype)
    
    @classmethod
    def buildfilters(cls,*args):
        return buildfilters(*args)
        
    def updatefilename(self,filename,selectedfilter):
        import os
        try:
            del self.filename
        except AttributeError:
            pass
        self.dirname,self._basename = os.path.split(filename)
        self.selectedfilter = selectedfilter
        self.setlastdir(self.dirname)
        
    @classmethod
    def load_yaml(cls,filename):
        import yaml
        with open(filename,'r') as f:
            obj1 = yaml.load(f)
            return obj1.upgrade()

    @classmethod
    def load_safe(cls,filepathin,suggestions = None,openmethod = None,**openmethodkwargs):
        import os
        pathin,filenamein = os.path.split(filepathin)

        if suggestions == None:
            suggestions = []

        suggestions.append(pathin)        
        suggestions.append('.')
        suggestions.append(cls.lastdir())
        suggestions.append(popupcad.designdir)
        
        for path in suggestions:
            try:
                filepath = os.path.normpath(os.path.join(path,filenamein))
                if openmethod==None:
                    design = cls.load_yaml(filepath)
                else:
                    design = openmethod(filepath,**openmethodkwargs)
                return filepath, design
            except IOError:
                pass
                
        msgbox = qg.QMessageBox()
        msgbox.setText('Cannot Find File')
        msgbox.setInformativeText('Select a new File?')
        msgbox.setDetailedText(filenamein)
        msgbox.setIcon(msgbox.Icon.Warning)
        msgbox.setStandardButtons(msgbox.StandardButton.Cancel | msgbox.StandardButton.Open)
        msgbox.setDefaultButton(msgbox.StandardButton.Open)
        ret = msgbox.exec_()

        if ret == msgbox.Cancel:
            raise(FileMissing(filenamein))
        if ret == msgbox.Open:
            return cls.open_filename()

    @classmethod
    def open_filename(cls,parent = None,openmethod = None,**openmethodkwargs):
        filename, selectedfilter = qg.QFileDialog.getOpenFileName(parent,'Open',cls.lastdir(),filter = cls.filterstring,selectedFilter = cls.selectedfilter)
        if filename:
            if openmethod == None:
                design = cls.load_yaml(filename)
            else:
                design = openmethod(filename,**openmethodkwargs)
            design.updatefilename(filename,selectedfilter)
            return filename, design
        else:
            return None,None
            
    @classmethod
    def open(cls,*args,**kwargs):
        filename,design = cls.open_filename(*args,**kwargs)
        return design
            
    def save(self,parent = None,savemethod = None,**savemethodkwargs):
        try:
            
            self.parent_program_name = self.get_parent_program_name()
            self.parent_program_version = self.get_parent_program_version()
            if savemethod == None:
                return self.save_yaml(self.filename())
            else:
                return savemethod(self.filename(),**savemethodkwargs)
        except AttributeError:
            return self.saveAs(parent)

    def regen_id(self):
        import random
        self.id = int(random.randint(0,9999999999))
                    
    def saveAs(self,parent = None,savemethod = None,**savemethodkwargs):
        import os
        try:
            tempfilename = os.path.normpath(os.path.join(self.dirname,self.get_basename())) 
        except AttributeError:
            try:
                basename = self.get_basename()
            except AttributeError:
                basename = self.genbasename()
                
            tempfilename = os.path.normpath(os.path.join(self.lastdir(),basename))                
            
        filename, selectedfilter = qg.QFileDialog.getSaveFileName(parent, "Save As", tempfilename,filter = self.filterstring,selectedFilter = self.selectedfilter)
        if not filename:
            return False
        else:
            self.updatefilename(filename,selectedfilter)

            self.parent_program_name = self.get_parent_program_name()
            self.parent_program_version = self.get_parent_program_version()

            if savemethod == None:
                return self.save_yaml(self.filename())
            else:
                return savemethod(self.filename(),**savemethodkwargs)

    def filename(self):
        import os
        return os.path.normpath(os.path.join(self.dirname,self.get_basename()))              
            
    def save_yaml(self,filename,identical = True):
        import yaml
        new = self.upgrade(identical)
        with open(filename,'w') as f:        
            yaml.dump(new,f)
        return True
        
    def __str__(self):
        return self.get_basename()

    def __repr__(self):
        return str(self)

class popupCADFile(GenericFile):
    @classmethod
    def get_parent_program_name(self):
        return popupcad.program_name
    @classmethod
    def get_parent_program_version(self):
        return popupcad.version
    