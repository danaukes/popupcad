# -*- coding: utf-8 -*-
"""
Written by Daniel M. Aukes.
Email: danaukes<at>seas.harvard.edu.
Please see LICENSE.txt for full license.
"""
import popupcad
from popupcad.filetypes.popupcad_file import popupCADFile
from dev_tools.acyclicdirectedgraph import AcyclicDirectedGraph
import PySide.QtGui as qg


class UpgradeError(Exception):
    pass


class NoOperation(Exception):

    def __init__(self):
        Exception.__init__(self, 'No Parent Operation')


class Design(popupCADFile):
    filetypes = {'cad': 'CAD Design'}
    defaultfiletype = 'cad'

    @classmethod
    def lastdir(cls):
        return popupcad.lastdesigndir

    @classmethod
    def setlastdir(cls, directory):
        popupcad.lastdesigndir = directory

    def __init__(self):
        super(Design, self).__init__()
        self.operations = []
        self._layerdef = popupcad.filetypes.layerdef.LayerDef()
        self.id = id(self)
        self.sketches = {}
        self.subdesigns = {}
#        self._main_operation = None

    def define_layers(self, layerdef):
        self._layerdef = layerdef

    def return_layer_definition(self):
        try:
            return self._layerdef
        except AttributeError:
            self._layerdef = self.__layerdef
            del self.__layerdef
            return self._layerdef

    def operation_index(self, operation_ref):
        try:
            indeces = dict([(op.id, ii)
                            for ii, op in enumerate(self.operations)])
            return indeces[operation_ref]
        except KeyError:
            raise(NoOperation)

    def op_from_ref(self, ref):
        return self.operations[self.operation_index(ref)]

    def replace_op_refs_force(self, oldref, newref):
        failed_ops = []
        for op in self.operations:
            try:
                op.replace_op_refs(oldref, newref)
            except AttributeError:
                failed_ops.append(op)
        return failed_ops

    def replace_sketch_refs_force(self, oldref, newref):
        failed_ops = []
        for op in self.operations:
            try:
                op.replace_sketch_refs(oldref, newref)
            except AttributeError:
                failed_ops.append(op)
        return failed_ops

    def replace_op_refs(self, oldref, newref):
        self.build_tree()

        oldop = self.op_from_ref(oldref[0])
        newop = self.op_from_ref(newref[0])

        if oldop in newop.decendents():
            error_string = str(oldop) + ' is a child of ' + str(newop)
            raise UpgradeError

        if newop in oldop.decendents():
            error_string = str(newop) + ' is a child of ' + str(oldop)
            raise UpgradeError

        ii = self.operations.index(newop)
        jjs = [self.operations.index(item) for item in oldop.decendents()]
        if not not jjs:
            jj = min(jjs)
            if ii > jj:
                error_string = str(
                    newop) + ' is below a child of ' + str(oldop) + '. Please move up.'
                raise UpgradeError

        for op in self.operations:
            failed_ops = self.replace_op_refs_force(oldref, newref)
        if not not failed_ops:
            error_string = 'Some operations cannot be updated'
            message_string = 'Please update manually.'
            s = 'This is due to the following operations:\n'
            for child in failed_ops[:-1]:
                s += '{0},\n'.format(str(child))
            s += '{0}'.format(str(failed_ops[-1]))
            raise UpgradeError

    def prioroperations(self, op):
        priorindex = self.operation_index(op.id)
        prioroperations = self.operations[:priorindex]
        return prioroperations

    def copy(self, identical=True):
        new = Design()
        new.operations = [operation.copy_wrapper()
                          for operation in self.operations]
        new.define_layers(self.return_layer_definition())
        if identical:
            new.id = self.id
        new.main_operation = self.main_operation
        new.sketches = {}
        for key, value in self.sketches.items():
            new.sketches[key] = value.copy(identical=True)
        new.subdesigns = {}
        for key, value in self.subdesigns.items():
            new.subdesigns[key] = value.copy(identical=True)
        self.copy_file_params(new, identical)
        return new

    def upgrade(self, identical=True):
        new = Design()
        samesame = False
        operations_old = self.operations
        while not samesame:
            operations_new = [item.upgrade_wrapper()
                              for item in operations_old]
            samesame = operations_old == operations_new
            operations_old = operations_new
        new.operations = operations_new
        new.define_layers(self.return_layer_definition())
        if identical:
            new.id = self.id
        new.main_operation = self.main_operation
        new.sketches = {}
        for key, value in self.sketches.items():
            new.sketches[key] = value.upgrade(identical=True)
        new.subdesigns = {}
        for key, value in self.subdesigns.items():
            new.subdesigns[key] = value.upgrade(identical=True)
        self.copy_file_params(new, identical)
        new.upgrade_operations2()
        return new

    def upgrade_operations2(self):
        from popupcad_deprecated.sketchoperation2 import SketchOperation2
        from popupcad.manufacturing.simplesketchoperation import SimpleSketchOp
        from popupcad.manufacturing.laminateoperation2 import LaminateOperation2
        newoperations = []
        ops_to_remove = []
        replacements = []
        for op0 in self.operations:
            if isinstance(
                    op0,
                    SketchOperation2) and op0.operation_link1 is not None:
                sketch_links = {'sketch': [op0.sketchid]}
                op1 = SimpleSketchOp(sketch_links, op0.layer_links)
                a = (op0.operation_link1, op0.outputref)
                b = (op1.id, 0)
                if op0.function in LaminateOperation2.unaryoperationtypes:
                    unary_links = [a, b]
                    binary_links = []
                else:
                    unary_links = [a]
                    binary_links = [b]
                operation_links = {
                    'unary': unary_links,
                    'binary': binary_links}
                op2 = LaminateOperation2(operation_links, op0.function)
                op2.id = op0.id
#                newoperations.append(op0)
                newoperations.append(op1)
                newoperations.append(op2)
#                replacements.append(((op0.id,0),(op2.id,0)))
#                ops_to_remove.append(op0)
            else:
                newoperations.append(op0)

        self.operations = []
        self.operations.extend(newoperations)

#        for old,new in replacements:
#            self.replace_op_refs(old,new)
#            failed = self.replace_op_refs_force(old,new)
#            check_failures = set(failed)-set(ops_to_remove)
#            if not not check_failures:
#                raise(UpgradeError('Some operations could not be upgraded.  loss of data may have occurred',list(check_failures)))


#        for op in ops_to_remove:
#            self.operations.pop(self.operations.index(op))

    def addoperation(self, operation):
        if not not self.operations:
            if operation in self.operations:
                pass
            else:
                self.operations.append(operation)
        else:
            self.operations.append(operation)

    def findlocateline(self):
        for op in self.operations[::-1]:
            try:
                for geom in self.sketches[op.locationgeometry()].operationgeometry:
                    if not geom.is_construction():
                        return geom
            except AttributeError:
                pass

    def findlastdesignop(self):
        from popupcad.manufacturing import LocateOperation
        for op in self.operations[::-1]:
            if not isinstance(op, LocateOperation):
                return op

    def subdesigns_are_reprocessed(self, setvalue=None):
        if setvalue is None:
            try:
                return self.subdesigns_reprocessed
            except AttributeError:
                self.subdesigns_reprocessed = False
                return self.subdesigns_reprocessed
        else:
            self.subdesigns_reprocessed = setvalue

    def reprocessoperations(self, operations=None):
        if not self.subdesigns_are_reprocessed():
            for subdesign in self.subdesigns.values():
                subdesign.reprocessoperations()
            self.subdesigns_are_reprocessed(True)

        if operations is None:
            operations = self.operations

        for op in self.operations:
            op.generate(self)

    def build_tree(self):
        connections = []
        for child in self.operations:
            for parentref in child.parentrefs():
                parent = self.op_from_ref(parentref)
                connections.append((parent, child))
        tree = AcyclicDirectedGraph(self.operations[:], connections)
        return tree

    def cleanup_subdesigns(self):
        subdesignrefs = []
        for op in self.operations:
            subdesignrefs.extend(op.subdesignrefs())
        unused = set(self.subdesigns.keys()) - set(subdesignrefs)
        for key in unused:
            self.subdesigns.pop(key)

    def cleanup_sketches(self):
        sketchrefs = []
        for op in self.operations:
            sketchrefs.extend(op.sketchrefs())
        unused = set(self.sketches.keys()) - set(sketchrefs)
        for key in unused:
            self.sketches.pop(key)

    def save_joint_def(self):
        import yaml
        import os
        for op in self.operations:
            try:
                filename = os.path.normpath(
                    os.path.join(
                        self.filename() +
                        '.joints',
                    ))
                with open(filename, 'w') as f:
                    yaml.dump(
                        (op.bodies_generic,
                         op.connections,
                         op.fixed_bodies,
                         op.all_joint_props),
                        f)
            except AttributeError:
                pass

    def raster(
        self,
        filetype='PNG',
        destination=None,
        gv=None,
        size=(
            400,
            300)):
        if gv is None:
            from popupcad.widgets.render_widget import RenderWidget
            widget = RenderWidget(size)
            gv = widget.gv

        if destination is None:
            destination = self.dirname
        self.reprocessoperations()

        for ii, op in enumerate(self.operations):
            for jj, out in enumerate(op.output):
                filename = '{0:02.0f}_{1:02.0f}'.format(ii, jj)
                out.generic_laminate().raster(
                    filename,
                    filetype,
                    destination,
                    gv)

    def build_documentation(self):
        import os
        from popupcad.filetypes.design_documentation import DesignDocumentation
        base = os.path.splitext(self.get_basename())[0]
        subdir = os.path.normpath(os.path.join(self.dirname, base))
        if not os.path.exists(subdir):
            os.mkdir(subdir)
#        self.raster(destination=subdir)
        new = DesignDocumentation.build(self, subdir)
        file = os.path.normpath(os.path.join(subdir, base + '.md'))
        with open(file, 'w') as f:
            f.writelines(new.output())
        #            yaml.dump(new.dictify2(),f)
#        new.save_yaml(file)

    def set_main_operation(self, op):
        self._main_operation = op

    def get_main_operation(self):
        try:
            return self._main_operation
        except AttributeError:
            try:
                self._main_operation = self.operations[0].id, 0
            except IndexError:
                self._main_operation = None

            return self._main_operation
    main_operation = property(get_main_operation, set_main_operation)
