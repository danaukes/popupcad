# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""

import sys
import os
import PySide.QtCore as qc
import PySide.QtGui as qg

import popupcad
import imp
from popupcad.widgets.errorlog import ErrorLog
from popupcad.graphics2d.graphicsscene import GraphicsScene
from popupcad.graphics2d.graphicsview import GraphicsView
from popupcad.graphics3d.GLMeshItem import GLObjectViewer
from popupcad.supportfiles import Icon
import popupcad.filetypes as filetypes
import popupcad.materials as materials
from popupcad.widgets import materialselection
from popupcad.widgets.listeditor import ListSelector
import glob
from popupcad.widgets.widgetcommon import WidgetCommon
from popupcad.widgets.dragndroptree import DraggableTreeWidget,DirectedDraggableTreeWidget

class Editor(qg.QMainWindow,WidgetCommon):
    '''
    Editor Class

    The Editor is the main widget for popupCAD.
    '''
    gridchange = qc.Signal()
    operationedited = qc.Signal(object)
    operationadded = qc.Signal(object)

    def loggable(func):
        def log(self,*args,**kwargs):
            try:
                return func(self,*args,**kwargs)
            except Exception as ex:
                import traceback
                import sys
                tb = sys.exc_info()[2]
                exception_string = traceback.format_exception(type(ex), ex, tb)
                [self.error_log.appendText(item) for item in exception_string]
                raise
        return log
        
    def __init__(self, parent=None,**kwargs):
        """Initialize Editor

        :param parent: Parent Widget(if any)
        :type parent: QWidget
        :returns:  nothing
        :raises: nothing
        """
        super(Editor,self).__init__(parent)
        self.error_log = ErrorLog()
        self.safe_init(parent,**kwargs)

    @loggable
    def safe_init(self,parent=None,**kwargs):
        self.sceneview = GraphicsScene()
        self.view_2d = GraphicsView(self.sceneview)
        self.view_2d.scrollhand()
        self.setCentralWidget(self.view_2d)

        self.setTabPosition(qc.Qt.AllDockWidgetAreas, qg.QTabWidget.South)

#        self.operationeditor = DirectedDraggableTreeWidget()
        self.operationeditor = DraggableTreeWidget()
        self.operationeditor.enable()

        self.layerlistwidget = ListSelector()

        self.operationdock = qg.QDockWidget()
        self.operationdock.setWidget(self.operationeditor)
        self.operationdock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
        self.operationdock.setWindowTitle('Operations')
        self.addDockWidget(qc.Qt.LeftDockWidgetArea,self.operationdock)

        self.layerlistwidgetdock = qg.QDockWidget()
        self.layerlistwidgetdock.setWidget(self.layerlistwidget)
        self.layerlistwidgetdock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
        self.layerlistwidgetdock.setWindowTitle('Layers')
        self.addDockWidget(qc.Qt.LeftDockWidgetArea,self.layerlistwidgetdock)

        self.view_3d = GLObjectViewer(self)      
        self.view_3d_dock = qg.QDockWidget()
        self.view_3d_dock.setWidget(self.view_3d)
        self.view_3d_dock.setAllowedAreas(qc.Qt.AllDockWidgetAreas)
        self.view_3d_dock.setWindowTitle('3D Visualization')
        self.addDockWidget(qc.Qt.RightDockWidgetArea,self.view_3d_dock)

        self.importscripts()
        
        self.operationeditor.currentRowChanged.connect(self.showcurrentoutput) 
        self.layerlistwidget.itemSelectionChanged.connect(self.showcurrentoutput)
        self.setWindowTitle('Editor')
        self.operationeditor.signal_edit.connect(self.editoperation) 
        self.newfile()
        self.sceneview.highlightbody.connect(self.highlightbody)
        self.operationadded.connect(self.newoperationslot)
        self.operationedited.connect(self.editedoperationslot)

        self.createActions()
        self.backuptimer = qc.QTimer()
        self.backuptimer.setInterval(popupcad.backup_timeout)
        self.backuptimer.timeout.connect(self.autosave)
        self.backuptimer.start()
#        self.raiseBox()

#        self.resize(1024,576)
#        dxy = qg.QApplication.desktop().screen().rect().center() - self.rect().center()
#        self.move(dxy)
    def autosave(self):
        import os
        import glob
        filenames = glob.glob(popupcad.backupdir+'\\*.cad')
        filenames.sort(reverse = True)
        for filename in filenames[popupcad.backup_limit:]:
            os.remove(filename)
        
        time = popupcad.basic_functions.return_formatted_time()
        filename = os.path.normpath(os.path.join(popupcad.backupdir,'autosave_'+time+'.cad'))
        self.design.save_yaml(filename)
        
    @loggable
    def importscripts(self):
        self.scriptclasses = []
        searchstring = os.path.normpath(os.path.join(popupcad.scriptdir,'*.py'))
        scripts = glob.glob(searchstring)
        for script in scripts:
            module = imp.load_source('module',script)
            self.scriptclasses.append(module.Script(self))
    
    @loggable
    def createActions(self):
        self.fileactions = []
        self.fileactions.append({'text':"&New",'kwargs':{'icon':Icon('new'),'shortcut':qg.QKeySequence.New,'statusTip':"Create a new file", 'triggered':self.newfile}})
        self.fileactions.append({'text':"&Open...",'kwargs':{'icon':Icon('open'),'shortcut':qg.QKeySequence.Open,'statusTip':"Open an existing file", 'triggered':self.open}})
        self.fileactions.append({'text':"&Save",'kwargs':{'icon':Icon('save'),'shortcut':qg.QKeySequence.Save,'statusTip':"Save the document to disk", 'triggered':self.save}})
        self.fileactions.append({'text':"Save &As...",'kwargs':{'icon':Icon('saveas'),'shortcut':qg.QKeySequence.SaveAs,'statusTip':"Save the document under a new name",'triggered':self.saveAs}})
        self.fileactions.append({'text':'&Export to SVG','kwargs':{'icon':Icon('export'),'triggered':self.exportLayerSVG}})
        self.fileactions.append({'text':"Regen ID",'kwargs':{'triggered':self.regen_id,}})      

        self.projectactions = []
        self.projectactions.append({'text':'&Rebuild','kwargs':{'icon':Icon('refresh'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_R,'triggered':self.reprocessoperations}})
        def dummy(action):
            action.setCheckable(True)
            action.setChecked(True)
            self.act_autoreprocesstoggle = action
        self.projectactions.append({'text':'Auto Reprocess','kwargs':{},'prepmethod':dummy})
        def dummy(action):
            action.setCheckable(True)
            action.setChecked(True)
            self.act_3don= action
        self.projectactions.append({'text':'3D Rendering','kwargs':{},'prepmethod':dummy})
        self.projectactions.append(None)
        self.projectactions.append({'text':'Layer Order...','kwargs':{'triggered':self.editlayers}})
        self.projectactions.append({'text':'Laminate Properties...','kwargs':{'triggered': self.editlaminate}})
        self.projectactions.append({'text':'Sketches...','kwargs':{'triggered':self.sketchlist}})
        self.projectactions.append({'text':'SubDesigns...','kwargs':{'triggered' :self.subdesigns}})

        self.viewactions = []
        self.viewactions.append({'text':'3D View','kwargs':{'icon':Icon('3dview'),'triggered':lambda:self.showhide(self.view_3d_dock)}})
        self.viewactions.append({'text':'Operations','kwargs':{'icon':Icon('operations'),'triggered':lambda:self.showhide(self.operationdock)}})
        self.viewactions.append({'text':'Layers','kwargs':{'icon':Icon('layers'),'triggered':lambda:self.showhide(self.layerlistwidgetdock)}})
        self.viewactions.append({'text':'Error Log','kwargs':{'triggered':lambda:self.showhide(self.error_log)}})
        self.viewactions.append(None)
        self.viewactions.append({'text':'Zoom Fit','kwargs':{'triggered':self.view_2d.zoomToFit,'shortcut': qc.Qt.CTRL+qc.Qt.Key_F}})
        self.viewactions.append({'text':'Screenshot','kwargs':{'triggered':self.sceneview.screenShot,'shortcut': qc.Qt.CTRL+qc.Qt.Key_R}})
        self.viewactions.append({'text':'3D Screenshot','kwargs':{'triggered':self.view_3d.screenshot}})

        self.operationactions = []        
        self.operationactions.append({'text':'&SketchOp','kwargs':{'icon':Icon('polygons'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_S,'triggered':lambda:self.newoperation(popupcad.manufacturing.SketchOperation2)}})
        self.operationactions.append({'text':'&Dilate/Erode','kwargs':{'icon':Icon('bufferop'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_B,'triggered':lambda:self.newoperation(popupcad.manufacturing.BufferOperation2)}})
        self.operationactions.append({'text':'&LayerOp','kwargs':{'icon':Icon('layerop'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_L,'triggered':lambda:self.newoperation(popupcad.manufacturing.LayerOp)}})
        self.operationactions.append({'text':'&LaminateOp','kwargs':{'icon':Icon('metaop'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_M,'triggered':lambda:self.newoperation(popupcad.manufacturing.LaminateOperation)}})
        self.operationactions.append({'text':'Shift/Flip','kwargs':{'triggered':lambda:self.newoperation(popupcad.manufacturing.ShiftFlip2)}})
        self.operationactions.append({'text':'L&ocateOp','kwargs':{'icon':Icon('locate'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_O,'triggered':lambda:self.newoperation(popupcad.manufacturing.LocateOperation)}})
        self.operationactions.append({'text':'&PlaceOp','kwargs':{'icon':Icon('placeop'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_P,'triggered':lambda:self.newoperation(popupcad.manufacturing.PlaceOperation7)}})

        supportactions= []
        supportactions.append({'text':'Sheet','kwargs':{'icon':Icon('outersheet'),'triggered':lambda:self.newoperation(popupcad.manufacturing.OuterSheet2)}})
        supportactions.append({'text':'&Web','kwargs':{'icon':Icon('outerweb'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_U,'triggered':lambda:self.newoperation(popupcad.manufacturing.AutoWeb3)}})
        supportactions.append({'text':'S&upport','kwargs':{'icon':Icon('autosupport'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_W,'triggered':lambda:self.newoperation(popupcad.manufacturing.SupportCandidate3)}})
        supportactions.append({'text':'Custom Support','kwargs':{'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_W,'triggered':lambda:self.newoperation(popupcad.manufacturing.CustomSupport3)}})

        self.manufacturingactions= []        
        self.manufacturingactions.append({'text':'Keep-outs','kwargs':{'icon':Icon('firstpass'),'triggered':lambda:self.newoperation(popupcad.manufacturing.KeepOut2)}})
        self.manufacturingactions.append({'text':'Supports','submenu':supportactions,'kwargs':{'icon':Icon('outerweb')}})
        self.manufacturingactions.append({'text':'Tool Clearance','kwargs':{'triggered':lambda:self.newoperation(popupcad.manufacturing.ToolClearance2)}})
        self.manufacturingactions.append({'text':'Cuts','kwargs':{'icon':Icon('firstpass'),'shortcut': qc.Qt.CTRL+qc.Qt.SHIFT+qc.Qt.Key_1,'triggered':lambda:self.newoperation(popupcad.manufacturing.CutOperation2)}})
        self.manufacturingactions.append({'text':'Removability','kwargs':{'triggered':lambda:self.newoperation(popupcad.manufacturing.Removability)}})
        self.manufacturingactions.append({'text':'Identify Bodies','kwargs':{'triggered':lambda:self.newoperation(popupcad.manufacturing.IdentifyBodies)}})
        self.manufacturingactions.append({'text':'Identify Rigid Bodies','kwargs':{'triggered':lambda:self.newoperation(popupcad.manufacturing.IdentifyRigidBodies)}})

        self.toolbar_operations = self.buildToolbar(self.operationactions,name='Operations',size=36,area=qc.Qt.ToolBarArea.TopToolBarArea)
        self.toolbar_manufacturing = self.buildToolbar(self.manufacturingactions,name='Manufacturing',size=36,area=qc.Qt.ToolBarArea.TopToolBarArea)

        self.menu_file = self.buildMenu(self.fileactions,name='File')
        self.menu_project= self.buildMenu(self.projectactions,name='Project')
        self.menu_operations = self.buildMenu(self.operationactions,name='Operations')
        self.menu_manufacturing = self.buildMenu(self.manufacturingactions,name='Manufacturing')
        self.menu_view = self.buildMenu(self.viewactions,name='View')

    @loggable
    def newoperation(self,operationclass):
        operationclass.new(self,self.design,self.operationeditor.currentRow(),self.operationadded)

    @loggable
    def editoperation(self,operation):
        operation.edit(self,self.design,self.operationedited)

    def regen_id(self):
        self.design.regen_id()

    @loggable
    def newoperationslot(self,operation):
        self.design.operations.append(operation)
        if self.act_autoreprocesstoggle.isChecked():
            self.reprocessoperations([operation])

    @loggable
    def editedoperationslot(self,operation):
        if self.act_autoreprocesstoggle.isChecked():
            self.reprocessoperations([operation])

    @loggable
    def reprocessoperations(self,operations=None):
        try:
            self.design.reprocessoperations(operations)
            self.operationeditor.refresh()
            self.showcurrentoutput()
            self.view_2d.zoomToFit()
        except:
            raise
        finally:
            self.operationeditor.refresh()
            self.showcurrentoutput()
        
    @loggable
    def newfile(self):
        from popupcad.materials import LayerDef,Carbon_0_90_0,Pyralux,Kapton
        design = filetypes.Design()
        design.define_layers(LayerDef(Carbon_0_90_0(),Pyralux(),Kapton(),Pyralux(),Carbon_0_90_0()))
        self.loadfile(design)

    @loggable
    def open(self):
        design = popupcad.filetypes.Design.open(self)
        if not design==None:
            self.loadfile(design)
            if self.act_autoreprocesstoggle.isChecked():
                self.reprocessoperations()

    @loggable
    def open_sketcher(self):
        from .sketcher import Sketcher
        from popupcad.filetypes.sketch import Sketch
        ii,jj = self.operationeditor.currentIndeces()
        layers = self.design.layerdef().layers
        sketcher = Sketcher(self,Sketch(),self.design,selectops = True)
        sketcher.show()
        
    @loggable
    def save(self):
        return self.design.save(self)

    @loggable
    def saveAs(self,parent = None):
        return self.design.saveAs(self)

    @loggable
    def loadfile(self,design):
        self.design = design
        self.operationeditor.blockSignals(True)
        self.layerlistwidget.blockSignals(True)
        self.sceneview.deleteall()      
        
        self.operationeditor.setnetworkgenerator(self.design.network)
        self.operationeditor.linklist(self.design.operations)
        
        self.updatelayerlist()
        self.layerlistwidget.selectAll()
        self.operationeditor.blockSignals(False)
        self.layerlistwidget.blockSignals(False)

    @loggable
    def editlayers(self):
        carbon = materials.Carbon_0_90_0
        pyralux = materials.Pyralux
        kapton = materials.Kapton
        initiallist = [carbon,pyralux,kapton]
        window = materialselection.MaterialSelection(self.design.layerdef().layers,initiallist,self)
        result = window.exec_()
        if result == window.Accepted:
            self.design.define_layers(window.layerdef)
        self.updatelayerlist()
        self.layerlistwidget.selectAll()

    @loggable
    def editlaminate(self):
        from popupcad.widgets.propertyeditor import PropertyEditor
        dialog = self.builddialog(PropertyEditor(self.design.layerdef().layers))
        dialog.exec_()
        self.design.layerdef().refreshzvalues()

    @loggable
    def sketchlist(self):
        from popupcad.filetypes.sketch import Sketch
        from popupcad.widgets import listmanager
        from .sketcher import Sketcher

        widget = listmanager.ListManager(self.design.sketches)
        def edit_method(sketch):
            sketch.edit(self,self.design,selectops = True)
        def new_method(refresh_method):
            def accept_method2(sketch,*args):
                self.design.sketches[sketch.id] = sketch
                refresh_method(sketch)
            sketcher = Sketcher(self,Sketch(),self.design,accept_method = accept_method2,selectops = True)
            sketcher.show()
        
        widget.set_layout(cleanup_method = self.design.cleanup_sketches,edit_method = edit_method,new_method = new_method,load_method = Sketch.open,saveas = True,copy = True,delete = True)
        dialog = self.builddialog(widget)        
        dialog.exec_()

    @loggable
    def subdesigns(self):
        from popupcad.filetypes.design import Design
        from popupcad.widgets import listmanager
        widget = listmanager.ListManager(self.design.subdesigns)
        widget.set_layout(cleanup_method = self.design.cleanup_subdesigns,load_method = Design.open,saveas = True,copy = True,delete = True)
        dialog = self.builddialog(widget)        
        dialog.exec_()

    @loggable
    def updatelayerlist(self):
        self.layerlistwidget.linklist(self.design.layerdef().layers)

    @loggable
    def showcurrentoutput(self,*args,**kwargs):
        ii,jj = self.operationeditor.currentIndeces()
        operationoutput = self.design.operations[ii].output[jj]
        selectedlayers=[item for item in self.design.layerdef().layers if item in self.layerlistwidget.selectedData()]
        self.show2dgeometry3(operationoutput,selectedlayers)
        self.show3dgeometry3(operationoutput,selectedlayers)

    @loggable
    def show2dgeometry3(self,operationoutput,selectedlayers,):
        display_geometry_2d = operationoutput.display_geometry_2d()
        self.sceneview.deleteall()
        for layer in selectedlayers[::1]:
            for geom in display_geometry_2d[layer]:
                self.sceneview.addItem(geom)
                geom.setselectable(True)

    @loggable
    def show3dgeometry3(self,operationoutput,selectedlayers):
        if self.act_3don.isChecked():
            tris = operationoutput.tris()
            lines = operationoutput.lines()
            self.view_3d.view.update_object(self.design.layerdef().zvalue,tris,lines,selectedlayers)
        else:
            tris = dict([(layer,[]) for layer in self.design.layerdef().layers])
            lines = dict([(layer,[]) for layer in self.design.layerdef().layers])
            self.view_3d.view.update_object(self.design.layerdef().zvalue,tris,lines,selectedlayers)

    @loggable
    def exportLayerSVG(self):
        import os
        ii,jj = self.operationeditor.currentIndeces()
        generic_geometry_2d = self.design.operations[ii].output[jj].generic_geometry_2d()
        for layernum,layer in enumerate(self.design.layerdef().layers[::1]):
            basename = self.design.get_basename() + '_'+str(self.design.operations[ii])+'_layer{0:02d}.svg'.format(layernum+1)
            filename = os.path.normpath(os.path.join(popupcad.exportdir,basename))
            scene = GraphicsScene()
            geoms = [item.outputstatic(color = (1,1,1,1)) for item in generic_geometry_2d[layer]]
            [scene.addItem(geom) for geom in geoms]
            scene.renderprocess(filename)

    @loggable
    def highlightbody(self,ref):
        import popupcad.algorithms.bodydetection as bodydetection
        ii,jj = self.operationeditor.currentIndeces()
        generic_geometry_2d = self.design.operations[ii].output[jj].generic_geometry_2d()
        bodies = bodydetection.findallconnectedneighborgeoms(self.design,ref,generic_geometry_2d)
        print bodies

    def closeEvent(self, event):
        if self.checkSafe():
            self.error_log.close()
            event.accept()
        else:
            event.ignore()

    def checkSafe(self):
        temp = qg.QMessageBox.warning(self, "Modified Document",
                'This file has been modified.\nDo you want to save your''changes?',
                qg.QMessageBox.Save | qg.QMessageBox.Discard |
                qg.QMessageBox.Cancel)
        if temp== qg.QMessageBox.Save:
            return self.save()
        elif temp== qg.QMessageBox.Cancel:
            return False
        return True            
            
if __name__ == "__main__":
    app = qg.QApplication(sys.argv)
    app.setWindowIcon(Icon('popupcad'))
    mw = Editor()
    mw.show()
    mw.raise_() 
    sys.exit(app.exec_())
