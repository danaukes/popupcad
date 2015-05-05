# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
   
import numpy
    
from dev_tools.constraints import SymbolicVertex

class BaseVertex(object):
    editable = ['pos','static','construction']
    deletable = []
    
    roundvalue = 5
    def __init__(self,position = None):

        self.id = id(self)
        self._pos = None
        self.setstatic(False)
        self.set_construction(True)
        self.setmoveable(True)

        if position !=None:
            self.setpos(position)
    def set_construction(self,test):
        self.construction = test
    def is_construction(self):
        try:
            return self.construction
        except AttributeError:
            self.construction = True
            return self.construction

    def setstatic(self,test):
        self.static = test

    def is_static(self):
        return self.static

    def setmoveable(self,test):
        self.moveable = test

    def is_moveable(self):
        try:
            return self.moveable
        except AttributeError:
            self.moveable = True
            return self.moveable

    def constraints_ref(self):
        try:
            return self._constraints_ref
        except AttributeError:
            self._constraints_ref = SymbolicVertex(self.id)
            return self._constraints_ref

    def isValid(self):
        return True

    def is_equal(self,other,tolerance):
        import popupcad.algorithms.points as points
        if type(self)==type(other):
            return points.twopointsthesame(self.getpos(),other.getpos(),tolerance)
        return False

    def __str__(self):
        return 'vertex'+str(self.id)
        
    def vertices(self):
        return [self]

    def __hash__(self):
        return self.id

    def __eq__(self,other):
        if type(self)==type(other):
            return self.id == other.id
        return False
        
    def p(self):
        return self.constraints_ref().p()

    def setpos(self,pos):
        pos = numpy.array(pos)
        pos.round(self.roundvalue)
        self._pos = tuple(pos.tolist())

    def getpos(self):
        try:
            if self._pos==None:
                self._pos = self.__pos
                del self.__pos
                return self._pos
            else:
                return self._pos
        except AttributeError:
            try:
                self._pos = self.__pos
                del self.__pos
            except AttributeError:
                self._pos = self._Vertex__pos
                del self._Vertex__pos
            return self._pos

    def getpos3D(self):
        return (self._pos[0],self._pos[1],0)

    def setsymbol(self,variable,value):
        p = self.constraints_ref().p()
        if p[0] == variable:
            self.setpos((value,self.getpos()[1]))            
        if p[1] == variable:
            self.setpos((self.getpos()[0],value))
            
    def properties(self):
        from dev_tools.propertyeditor import PropertyEditor
        return PropertyEditor(self)
        
    def copy(self,identical = True):
        new = type(self)()
        return self.copy_values(new,identical)

    def upgrade(self,*args,**kwargs):
        return self.copy(*args,**kwargs)
        
    def copy_values(self,new,identical=False):
        new.setpos(self.getpos())
        new.static = self.static
        new.setmoveable(self.is_moveable())
        new.set_construction(self.is_construction())
        
        if identical:
            new.id = self.id
        return new            

    def shape_is_equal(self,other):
        from popupcad.filetypes.genericshapebase import GenericShapeBase
        tolerance = GenericShapeBase.tolerance
        import popupcad.algorithms.points as points
        if type(self)==type(other):
            return points.twopointsthesame(self.getpos(),other.getpos(),tolerance)
        return False
        
    def shift(self,dxdy):
        pos = numpy.array(self.getpos())
        dxdy = numpy.array(dxdy)
        newpos = pos+dxdy
        self.setpos(newpos)

    def constrained_shift(self,dxdy,constraintsystem):
        constraintsystem.constrained_shift([(self,dxdy)])

    @classmethod
    def delistify(cls,id,x,y,static,is_moveable,is_construction):
        new = cls()
        new.id = id
        new.setpos((x,y))
        new.static = static
        new.setmoveable(is_moveable)
        new.set_construction(is_construction)
        return new

    def listify(self):
        x,y = self.getpos()
        output = [self.id,x,y,self.static,self.is_moveable(),self.is_construction()]
        return output

    def vertex_representer(dumper,v):
        output = dumper.represent_sequence(v.yaml_node_name,v.listify())
        return output
    
    @classmethod
    def vertex_constructor(cls,loader, node):
        list1 = loader.construct_sequence(node)
        new = cls.delistify(*list1)
        return new

class ShapeVertex(BaseVertex):
    yaml_node_name = u'!shape_vertex'
    def gen_interactive(self):
        from popupcad.graphics2d.interactivevertex import InteractiveShapeVertex
        iv = InteractiveShapeVertex(self)
        iv.updateshape()
        return iv

class DrawnPoint(ShapeVertex):
    yaml_node_name = u'!drawn_point'
    def exteriorpoints(self):
        return [self.getpos()]
    def interiorpoints(self):
        return []
    def gen_interactive(self):
        from popupcad.graphics2d.interactivevertex import DrawingPoint
        iv = DrawingPoint(self)
        iv.updateshape()
        return iv
    def points(self):
        return [self.getpos()]
    def segments(self):
        return []
    def segmentpoints(self):
        return []
    def outputinteractive(self):
        from popupcad.graphics2d.interactivevertex import DrawingPoint
        iv = DrawingPoint(self)
        iv.updateshape()
        return iv

    def outputstatic(self,*args,**kwargs):
        from popupcad.graphics2d.interactivevertex import StaticDrawingPoint
        iv = StaticDrawingPoint(self)
        iv.updateshape()
        return iv

    def outputshapely(self):
        from popupcad.geometry.customshapely import ShapelyPoint
#        from shapely.geometry import Point
        p = ShapelyPoint(*self.getpos())
        return p

class ReferenceVertex(BaseVertex):
    yaml_node_name = u'!reference_vertex'
    def __init__(self,*args,**kwargs):
        super(ReferenceVertex,self).__init__(*args,**kwargs)
        self.setstatic(True)
    def gen_interactive(self):
        from popupcad.graphics2d.interactivevertex import ReferenceInteractiveVertex
        iv = ReferenceInteractiveVertex(self)
        iv.updateshape()
        return iv
