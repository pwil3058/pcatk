### Copyright: Peter Williams (2012) - All rights reserved
###
### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU General Public License as published by
### the Free Software Foundation; version 2 of the License only.
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU General Public License for more details.
###
### You should have received a copy of the GNU General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""
Provide generic enhancements to Tree and List View widgets primarily to create
them from templates and allow easier access to named contents.
"""

import collections

import gtk
import gobject

class NamedTreeModel(gtk.TreeModel):
    # TODO: trim and improve NamedTreeModel
    Row = None # this is a namedtuple type
    types = None # this is an instance of Row defining column types

    @classmethod
    def col_index(cls, label):
        return cls.Row._fields.index(label)
    # END_DEF: col_index()

    @classmethod
    def col_indices(cls, labels):
        return [cls.Row._fields.index(label) for label in labels]
    # END_DEF: col_indices()

    @staticmethod
    def get_selected_rows(selection):
        """
        Return the list of Row() tuples associated with a list of paths.
        selection: a gtk.TreeSelection specifying the model and the
        rows to be retrieved
        """
        model, paths = selection.get_selected_rows()
        return [model.Row(*model[p]) for p in paths]
    # END_DEF: get_rows_for_paths()

    def get_row(self, model_iter):
        return self.Row(*self[model_iter])
    # END_DEF: get_row()

    def get_named(self, model_iter, *labels):
        return self.get(model_iter, *self.col_indices(labels))
    # END_DEF: get_values_named()

    def get_value_named(self, model_iter, label):
        return self.get_value(model_iter, self.col_index(label))
    # END_DEF: get_value_named()

    def set_value_named(self, model_iter, label, value):
        self.set_value(model_iter, self.col_index(label), value)
    # END_DEF: set_value_named()

    def set_named(self, model_iter, *label_values):
        col_values = []
        for index in len(label_values):
            if (index % 2) == 0:
                col_values.append(self.col_index(label_values[index]))
            else:
                col_values.append(label_values[index])
        self.set(model_iter, *col_values)
    # END_DEF: set_named()

    def named(self):
        """
        Iterate over rows as instances of type Row()
        """
        model_iter = self.get_iter_first()
        while model_iter is not None:
            yield self.get_row(model_iter)
            model_iter = self.iter_next(model_iter)
        return
    # END_DEF: named

    def find_named(self, select_func):
        model_iter = self.get_iter_first()
        while model_iter:
            if select_func(self.get_row(model_iter)):
                return model_iter
            else:
                model_iter = self.iter_next(model_iter)
        return None
    # END_DEF: get_row_with_key_value()
# END_CLASS: NamedTreeModel

class NamedListStore(gtk.ListStore, NamedTreeModel):
    def __init__(self):
        gtk.ListStore.__init__(*[self] + list(self.types))
    # END_DEF: __init__()
    def append_contents(self, rows):
        for row in rows:
            self.append(row)
    def set_contents(self, rows):
        self.clear()
        for row in rows:
            self.append(row)
# END_CLASS: NamedListStore

class NamedTreeStore(gtk.TreeStore, NamedTreeModel):
    def __init__(self):
        gtk.TreeStore.__init__(*[self] + list(self.types))
    # END_DEF: __init__()
# END_CLASS: NamedTreeStore

class CellRendererSpin(gtk.CellRendererSpin):
    """
    A modified version that propagates the SpinButton's "value-changed"
    signal.  Makes the behaviour more like a SpinButton.
    """

    def __init__(self, *args, **kwargs):
        """
        Add an "editing-started" callback to setup connection to SpinButton
        """
        gtk.CellRendererSpin.__init__(self, *args, **kwargs)
        self.connect('editing-started', CellRendererSpin._editing_started_cb)
    # END_DEF: __init__()

    @staticmethod
    def _editing_started_cb(cell, spinbutton, path):
        """
        Connect to the spinbutton's "value-changed" signal
        """
        spinbutton.connect('value-changed', CellRendererSpin._spinbutton_value_changed_cb, cell, path)
    # END_DEF: _editing_started_cb

    @staticmethod
    def _spinbutton_value_changed_cb(spinbutton, cell, path):
        """
        Propagate "value-changed" signal to get things moving
        """
        cell.emit('value-changed', path, spinbutton)
    # END_DEF: _spinbutton_value_changed_cb
gobject.signal_new('value-changed', CellRendererSpin, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,))
# END_CLASS: CellRendererSpin

class ViewSpec(object):
    __slots__ = ('properties', 'selection_mode', 'columns')

    def __init__(self, properties=None, selection_mode=None, columns=None):
        self.properties = properties if properties is not None else dict()
        self.selection_mode = selection_mode
        self.columns = columns if columns is not None else list()
    # END_DEF: __init__()
# END_CLASS: ViewSpec

class ColumnSpec(object):
    __slots__ = ('title', 'properties', 'cells', 'sort_key_function')

    def __init__(self, title, properties=None, cells=None, sort_key_function=None):
        self.title = title
        self.properties = properties if properties is not None else dict()
        self.cells = cells if cells is not None else list()
        self.sort_key_function = lambda x: sort_key_function(x[1])
    # END_DEF: __init__()
# END_CLASS: ColumnSpec

class CellRendererSpec(object):
    __slots__ = ('cell_renderer', 'properties', 'expand', 'start')

    def __init__(self, cell_renderer, expand=None, start=False):
        self.cell_renderer = cell_renderer
        self.expand = expand
        self.start = start
    # END_DEF: __init__()
# END_CLASS: CellRendererSpec

class CellDataFunctionSpec(object):
    __slots__ = ('function', 'user_data')

    def __init__(self, function, user_data=None):
        self.function = function
        self.user_data = user_data
    # END_DEF: __init__()
# END_CLASS: CellDataFunctionSpec

class CellSpec(object):
    __slots__ = ('cell_renderer_spec', 'properties', 'cell_data_function_spec', 'attributes')

    def __init__(self, cell_renderer_spec, properties=None, cell_data_function_spec=None, attributes=None):
        self.cell_renderer_spec = cell_renderer_spec
        self.properties = properties if properties is not None else dict()
        self.cell_data_function_spec = cell_data_function_spec
        self.attributes = attributes if attributes is not None else dict()
    # END_DEF: __init__()
# END_CLASS: CellSpec

class View(gtk.TreeView):
    # TODO: bust View() up into a number of "mix ins" for more flexibility
    Model = None
    specification = None
    ColumnAndCells = collections.namedtuple('ColumnAndCells', ['column', 'cells'])

    def __init__(self, model=None):
        if model is None:
            model = self.Model()
        else:
            assert isinstance(model, self.Model)
        gtk.TreeView.__init__(self, model)
        for prop_name, prop_val in self.specification.properties.items():
            self.set_property(prop_name, prop_val)
        if self.specification.selection_mode is not None:
            self.get_selection().set_mode(self.specification.selection_mode)
        self._columns = collections.OrderedDict()
        for col_d in self.specification.columns:
            self._view_add_column(col_d)
        self.connect("button_press_event", self._handle_button_press_cb)
        self.connect("key_press_event", self._handle_key_press_cb)
        self._connect_model_changed_cbs()
        self._modified_cbs = []
    # END_DEF: __init__()

    def _connect_model_changed_cbs(self):
        """
        Set up the call back for changes to the store so that the
        "sorted" indicator can be turned off if the model changes in
        any way.
        """
        model = self.get_model()
        sig_names = ["row-changed", "row-deleted", "row-has-child-toggled",
            "row-inserted", "rows-reordered"]
        self._change_cb_ids = [model.connect(sig_name, self._model_changed_cb) for sig_name in sig_names]
        self.last_sort_column = None
        self.sort_order = gtk.SORT_ASCENDING
    # END_DEF:

    @staticmethod
    def _create_cell(column, cell_renderer_spec):
        cell = cell_renderer_spec.cell_renderer()
        if cell_renderer_spec.expand is not None:
            if cell_renderer_spec.start:
                column.pack_start(cell, cell_renderer_spec.expand)
            else:
                column.pack_end(cell, cell_renderer_spec.expand)
        else:
            if cell_renderer_spec.start:
                column.pack_start(cell)
            else:
                column.pack_end(cell)
        return cell
    # END_DEF: _create_cell()

    def _view_add_column(self, col_d):
        col = gtk.TreeViewColumn(col_d.title)
        col_cells = View.ColumnAndCells(col, [])
        self._columns[col_d.title] = col_cells
        self.append_column(col)
        for prop_name, prop_val in col_d.properties.items():
            col.set_property(prop_name, prop_val)
        for cell_d in col_d.cells:
            self._view_add_cell(col, cell_d)
        if col_d.sort_key_function is not None:
            col.connect('clicked', self._column_clicked_cb, col_d.sort_key_function)
            col.set_clickable(True)
    # END_DEF: _view_add_column()

    def _view_add_cell(self, col, cell_d):
        cell = self._create_cell(col, cell_d.cell_renderer_spec)
        self._columns[col.get_title()].cells.append(cell)
        for prop_name, prop_val in cell_d.properties.items():
            cell.set_property(prop_name, prop_val)
        if cell_d.cell_data_function_spec is not None:
            col.set_cell_data_func(cell, cell_d.cell_data_function_spec.function, cell_d.cell_data_function_spec.user_data)
        for attr_name, attr_index in cell_d.attributes.items():
            col.add_attribute(cell, attr_name, attr_index)
            if attr_name == 'text':
                cell.connect('edited', self._cell_text_edited_cb, attr_index)
            elif attr_name == 'active':
                cell.connect('toggled', self._cell_toggled_cb, attr_index)
    # END_DEF: _view_add_cell()

    @property
    def model(self):
        return self.get_model()
    # END_DEF: model()

    @model.setter
    def model(self, new_model):
        self.set_model(new_model)
    # END_DEF: model()

    def set_model(self, model):
        assert model is None or isinstance(model, self.Model)
        old_model = self.get_model()
        for sig_cb_id in self._change_cb_ids:
            old_model.disconnect(sig_cb_id)
        gtk.TreeView.set_model(self, model)
        if model is not None:
            self._connect_model_changed_cbs()
    # END_DEF: set_model()

    def _notify_modification(self):
        for cbk, data in self._modified_cbs:
            if data is None:
                cbk()
            else:
                cbk(data)
    # END_DEF: _notify_modification()

    def register_modification_callback(self, cbk, data=None):
        self._modified_cbs.append([cbk, data])
    # END_DEF: register_modification_callback()

    def _handle_button_press_cb(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 2:
                self.get_selection().unselect_all()
                return True
        return False
    # END_DEF: _handle_button_press_cb()

    def _handle_key_press_cb(self, widget, event):
        if event.type == gtk.gdk.KEY_PRESS:
            if event.keyval == gtk.gdk.keyval_from_name('Escape'):
                self.get_selection().unselect_all()
                return True
        return False
    # END_DEF: _handle_key_press_cb()

    def _cell_text_edited_cb(self, cell, path, new_text, index):
        # TODO: need to do type cast on ALL tree editable cells
        if isinstance(cell, gtk.CellRendererSpin):
            self.get_model()[path][index] = self.get_model().types[index](new_text)
        else:
            self.get_model()[path][index] = new_text
        self._notify_modification()
    # END_DEF: _cell_text_edited_cb()

    def _cell_toggled_cb(self, cell, path, index):
        # TODO: test CellRendererToggle
        # should it be model[path][index] = not model[path][index]
        self.model[path][index] = cell.get_active()
        self._notify_modification()
    # END_DEF: _cell_toggled_cb()

    def get_col_with_title(self, title):
        return self._columns[title].column
    # END_DEF: get_col_with_title()

    def get_cell_with_title(self, title, index=0):
        return self._columns[title].cells[index]
    # END_DEF: get_cell_with_title()

    def get_cell(self, col_index, cell_index=0):
        key = list(self._columns.keys())[col_index]
        return self._columns[key].cells[cell_index]
    # END_DEF: get_cell()

    def _model_changed_cb(self, *_args, **_kwargs):
        """
        The model has changed and if the column involved is the
        current sort column the may no longer be sorted so we
        need to turn off the sort indicators.
        """
        # TODO: be more fine grained turning off sort indication
        if self.last_sort_column is not None:
            self.last_sort_column.set_sort_indicator(False)
            self.last_sort_column = None
    # END_DEF:

    def _column_clicked_cb(self, column, sort_key_function):
        """Sort the rows based on the given column"""
        # Heavily based on the FAQ example
        assert column.get_tree_view() == self
        if self.last_sort_column is not None:
            self.last_sort_column.set_sort_indicator(False)

        if self.last_sort_column == column:
           if self.sort_order == gtk.SORT_ASCENDING:
              self.sort_order = gtk.SORT_DESCENDING
           else:
              self.sort_order = gtk.SORT_ASCENDING
        else:
           self.sort_order   = gtk.SORT_ASCENDING
           self.last_sort_column = column
        model = self.get_model()
        if len(model) == 0:
            return
        erows = list(enumerate(model.named()))
        erows.sort(key=sort_key_function)
        if self.sort_order == gtk.SORT_DESCENDING:
            erows.reverse()
        # Turn off reorder callback while we do the reordering
        model.handler_block(self._change_cb_ids[-1])
        model.reorder([r[0] for r in erows])
        model.handler_unblock(self._change_cb_ids[-1])
        column.set_sort_indicator(True)
        column.set_sort_order(self.sort_order)
    # END_DEF: column_clicked_cb
# END_CLASS: View
