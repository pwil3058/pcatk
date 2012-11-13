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

'''
GTK extensions and wrappers
'''

import collections
import fractions
import sys

import gtk
import gobject
import pango

# TODO: make gtkpwx.py pure
from pcatk import utils

BITS_PER_CHANNEL = 16
ONE = (1 << BITS_PER_CHANNEL) - 1

### Utility Functions

def create_flag_generator():
    """
    Create a new flag generator
    """
    next_flag_num = 0
    while True:
        yield 2 ** next_flag_num
        next_flag_num += 1
# END_DEF: create_flag_generator

def best_foreground(rgb, threshold=0.5):
    wval = (rgb[0] * 0.299 + rgb[1] * 0.587 + rgb[2] * 0.114)
    if wval > ONE * threshold:
        return gtk.gdk.Color(0, 0, 0)
    else:
        return gtk.gdk.Color(ONE, ONE, ONE)
# END_DEF: best_foreground

def gdk_color_to_rgb(gcol):
    gcol_str = gcol.to_string()[1:]
    if len(gcol_str) == 3:
        return [int(gcol_str[i:(i+1)] * 4, 16) for i in range(3)]
    elif len(gcol_str) == 6:
        return [int(gcol_str[i*2:(i+1) * 2] * 2, 16) for i in range(3)]
    return [int(gcol_str[i*4:(i+1) * 4], 16) for i in range(3)]
# END_DEF: gdk_color_to_rgb

def wrap_in_scrolled_window(widget, policy=(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC), with_frame=True, label=None):
    scrw = gtk.ScrolledWindow()
    scrw.set_policy(policy[0], policy[1])
    if isinstance(widget, gtk.Container):
        scrw.add(widget)
    else:
        scrw.add_with_viewport(widget)
    if with_frame:
        frame = gtk.Frame(label)
        frame.add(scrw)
        frame.show_all()
        return frame
    else:
        scrw.show_all()
        return scrw
# END_DEF: wrap_in_scrolled_window

def wrap_in_frame(widget, shadow_type=gtk.SHADOW_NONE):
    """
    Wrap the widget in a frame with the requested shadow type
    """
    frame = gtk.Frame()
    frame.set_shadow_type(shadow_type)
    frame.add(widget)
    return frame
# END_DEF: 

### Useful Named Tuples

class WH(collections.namedtuple('WH', ['width', 'height'])):
    __slots__ = ()

    # These operations are compatible with gtk.gdk.Rectangle
    def __sub__(self, other):
        # don't assume other is WH just that it has width and height attributes
        return WH(width=self.width - other.width, height=self.height - other.height)
    # END_DEF: __sub__

    def __rsub__(self, other):
        # don't assume other is WH just that it has width and height attributes
        return WH(width=other.width - self.width, height=other.height - self.height)
    # END_DEF: __sub__

    def __eq__(self, other):
        # don't assume other is WH just that it has width and height attributes
        return other.width == self.width and other.height == self.height
    # END_DEF: __eq__
# END_CLASS: WH

class XY(collections.namedtuple('XY', ['x', 'y'])):
    __slots__ = ()

    # These operations are compatible with gtk.gdk.Rectangle
    def __sub__(self, other):
        # don't assume other is XY just that it has x and y attributes
        return XY(x=self.x - other.x, y=self.y - other.y)
    # END_DEF: __sub__

    def __rsub__(self, other):
        # don't assume other is XY just that it has x and y attributes
        return XY(x=other.x - self.x, y=other.y - self.y)
    # END_DEF: __sub__

    def __mul__(self, other):
        # allow scaling
        return XY(x=self.x * other, y=self.y * other)
    # END_DEF: __mul__

    def __eq__(self, other):
        # don't assume other is XY just that it has x and y attributes
        return other.x == self.x and other.y == self.y
    # END_DEF: __eq__
# END_CLASS: XY

# A named tuple compatible with gtk.gdk.Rectangle
class RECT(collections.namedtuple('XY', ['x', 'y', 'width', 'height'])):
    __slots__ = ()
    @staticmethod
    def from_xy_wh(xy, wh):
        return RECT(x=xy.x, y=xy.y, width=wh.width, height=wh.height)
    # END_DEF: from_xy_wh
# END_CLASS: RECT

### Conditional Action Groups

class MaskedConds(collections.namedtuple('MaskedConds', ['condns', 'mask'])):
    __slots__ = ()

    def __or__(self, other):
        return MaskedConds(self.condns | other.condns, self.mask | other.mask)
    # END_DEF: __or__
# END_CLASS: MaskedConds

class ActionCondns(object):
    _flag_generator = create_flag_generator()

    @staticmethod
    def new_flags_and_mask(count):
        """
        Return "count" new condition flags and their mask as a tuple
        """
        flags = [ActionCondns._flag_generator.next() for _i in range(count)]
        mask = sum(flags)
        return tuple(flags + [mask])
    # END_DEF: new_flags_and_mask
# END_CLASS: ActionCondns

AC_DONT_CARE = 0
AC_SELN_NONE, \
AC_SELN_MADE, \
AC_SELN_UNIQUE, \
AC_SELN_PAIR, \
AC_SELN_MASK = ActionCondns.new_flags_and_mask(4)

def get_masked_seln_conditions(seln):
    if seln is None:
        return MaskedConds(AC_DONT_CARE, AC_SELN_MASK)
    selsz = seln.count_selected_rows()
    if selsz == 0:
        return MaskedConds(AC_SELN_NONE, AC_SELN_MASK)
    elif selsz == 1:
        return MaskedConds(AC_SELN_MADE + AC_SELN_UNIQUE, AC_SELN_MASK)
    elif selsz == 2:
        return MaskedConds(AC_SELN_MADE + AC_SELN_PAIR, AC_SELN_MASK)
    else:
        return MaskedConds(AC_SELN_MADE, AC_SELN_MASK)
# END_DEF: get_masked_seln_conditions

class ConditionalActionGroups(object):
    class UnknownAction(Exception): pass
    def __init__(self, name, ui_mgrs=None, selection=None):
        self.groups = dict()
        self.current_condns = 0
        self.ui_mgrs = [] if ui_mgrs is None else ui_mgrs[:]
        self.name = name
        self.set_selection(selection)
    # END_DEF: __init__

    def _group_name(self, condns):
        return '{0}:{1:x}'.format(self.name, condns)
    # END_DEF: _group_name

    def _seln_condns_change_cb(self, seln):
        self.update_condns(get_masked_seln_conditions(seln))
    # END_DEF: _seln_condns_change_cb

    def set_selection(self, seln):
        if seln is None:
            return None
        self.update_condns(get_masked_seln_conditions(seln))
        return seln.connect('changed', self._seln_condns_change_cb)
    # END_DEF: set_selection

    def __getitem__(self, condns):
        if condns not in self.groups:
            self.groups[condns] = gtk.ActionGroup(self._group_name(condns))
            self.groups[condns].set_sensitive((condns & self.current_condns) == condns)
            for ui_mgr in self.ui_mgrs:
                ui_mgr.insert_action_group(self.groups[condns], -1)
        return self.groups[condns]
    # END_DEF: __getitem__

    def copy_action(self, new_condns, action_name):
        action = self.get_action(action_name)
        if not action:
            raise self.UnknownAction(action)
        self[new_condns].add_action(action)
    # END_DEF: copy_action

    def move_action(self, new_condns, action_name):
        for agrp in self.groups.values():
            action = agrp.get_action(action_name)
            if not action:
                raise self.UnknownAction(action)
            agrp.remove_action(action)
            self[new_condns].add_action(action)
    # END_DEF: move_action

    def update_condns(self, changed_condns):
        """
        Update the current condition state
        changed_condns: is a MaskedConds instance
        """
        condns = changed_condns.condns | (self.current_condns & ~changed_condns.mask)
        for key_condns, group in self.groups.items():
            if changed_condns.mask & key_condns:
                group.set_sensitive((key_condns & condns) == key_condns)
        self.current_condns = condns
    # END_DEF: update_condns

    def add_ui_mgr(self, ui_mgr):
        self.ui_mgrs.append(ui_mgr)
        for agrp in self.groups.values():
            ui_mgr.insert_action_group(agrp, -1)
    # END_DEF: add_ui_mgr

    def get_action(self, action_name):
        for agrp in self.groups.values():
            action = agrp.get_action(action_name)
            if action:
                return action
        return None
    # END_DEF: get_action

    def connect_activate(self, action_name, callback, *user_data):
        """
        Connect the callback to the "activate" signal of the named action
        """
        return self.get_action(action_name).connect('activate', callback, *user_data)
    # END_DEF: connect_activate

    def __str__(self):
        string = 'ConditionalActionGroups({0})\n'.format(self.name)
        for condns, group in self.groups.items():
            name = group.get_name()
            member_names = '['
            for member_name in [action.get_name() for action in group.list_actions()]:
                member_names += '{0}, '.format(member_name)
            member_names += ']'
            string += '\tGroup({0:x},{1}): {2}\n'.format(condns, name, member_names)
        return string
    # END_DEF: __str__

    def create_action_button(self, action_name, use_underline=True):
        action = self.get_action(action_name)
        return ActionButton(action, use_underline=use_underline)
    # END_DEF: create_action_button

    def create_action_button_box(self, action_name_list, use_underline=True,
                                 horizontal=True,
                                 expand=True, fill=True, padding=0):
        if horizontal:
            box = gtk.HBox()
        else:
            box = gtk.VBox()
        for action_name in action_name_list:
            button = self.create_action_button(action_name, use_underline)
            box.pack_start(button, expand, fill, padding)
        return box
    # END_DEF: create_action_button_box
# END_CLASS: ConditionalActionGroups

CLASS_INDEP_AGS = ConditionalActionGroups('class_indep')

class UIManager(gtk.UIManager):
    # TODO: check to see if this workaround is still necessary
    def __init__(self):
        gtk.UIManager.__init__(self)
        self.connect('connect-proxy', self._ui_manager_connect_proxy)
    # END_DEF: __init__

    @staticmethod
    def _ui_manager_connect_proxy(_ui_mgr, action, widget):
        tooltip = action.get_property('tooltip')
        if isinstance(widget, gtk.MenuItem) and tooltip:
            widget.set_tooltip_text(tooltip)
    # END_DEF: _ui_manager_connect_proxy
# END_CLASS: UIManager

class CAGandUIManager(object):
    '''This is a "mix in" class and needs to be merged with a gtk.Window() descendant'''
    UI_DESCR = '''<ui></ui>'''
    def __init__(self, selection=None, popup=None):
        self.ui_manager = UIManager()
        CLASS_INDEP_AGS.add_ui_mgr(self.ui_manager)
        name = '{0}:{1:x}'.format(self.__class__.__name__, self.__hash__())
        self.action_groups = ConditionalActionGroups(name, ui_mgrs=[self.ui_manager], selection=selection)
        self.populate_action_groups()
        self.ui_manager.add_ui_from_string(self.UI_DESCR)
        self._popup_cb_id = self._popup = None
        self.set_popup(popup)
    # END_DEF: __init__

    def populate_action_groups(self):
        assert False, 'should be derived in subclass'
    # END_DEF: populate_action_groups

    def _button_press_cb(self, widget, event):
        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 3 and self._popup:
                menu = self.ui_manager.get_widget(self._popup)
                menu.popup(None, None, None, event.button, event.time)
                return True
        return False
    # END_DEF: _button_press_cb

    def set_popup(self, popup):
        if self._popup_cb_id is None:
            self._popup_cb_id = self.connect('button_press_event', self._button_press_cb)
            if popup is None:
                self.enable_popup(False)
        elif self._popup is None and popup is not None:
            self.enable_popup(True)
        elif popup is None:
            self.enable_popup(False)
        self._popup = popup
    # END_DEF: set_popup

    def enable_popup(self, enable):
        if self._popup_cb_id is not None:
            if enable:
                self.handler_unblock(self._popup_cb_id)
            else:
                self.handler_block(self._popup_cb_id)
    # END_DEF: enable_popup
# END_CLASS: CAGandUIManager

### Text Entry

class EntryCompletionMultiWord(gtk.EntryCompletion):
    """
    Extend EntryCompletion to handle mult-word text.
    """

    def __init__(self, model=None):
        """
        model: an argument to allow the TreeModel to be set at creation.
        """
        gtk.EntryCompletion.__init__(self)
        if model is not None:
            self.set_model(model)
        self.set_match_func(self.match_func)
        self.connect("match-selected", self.match_selected_cb)
        self.set_popup_set_width(False)
    # END_DEF: __init__()

    @staticmethod
    def match_func(completion, key_string, model_iter, _data=None):
        """
        Does the (partial) word in front of the cursor match the item?
        """
        cursor_index = completion.get_entry().get_position()
        pword_start = utils.find_start_last_word(text=key_string, before=cursor_index)
        pword = key_string[pword_start:cursor_index].lower()
        if not pword:
            return False
        text_col = completion.get_text_column()
        model = completion.get_model()
        mword = model.get_value(model_iter, text_col)
        return mword and mword.lower().startswith(pword)
    # END_DEF: match_func
 
    @staticmethod
    def match_selected_cb(completion, model, model_iter):
        """
        Handle "match-selected" signal.
        """
        entry = completion.get_entry()
        cursor_index = entry.get_position()
        # just in case get_text() is overloaded e.g. to add learning
        text = gtk.Entry.get_text(entry)

        text_col = completion.get_text_column()
        mword = model.get_value(model_iter, text_col)
        new_text = utils.replace_last_word(text=text, new_word=mword, before=cursor_index)
        entry.set_text(new_text)
        # move the cursor behind the new word
        entry.set_position(cursor_index + len(new_text) - len(text))
        return True
    # END_DEF: match_selected_cb
# END_CLASS EntryCompletionMultiword

class TextEntryAutoComplete(gtk.Entry):
    def __init__(self, lexicon=None, learn=True, multiword=True, **kwargs):
        '''
        multiword: if True use individual words in entry as the target of autocompletion
        '''
        gtk.Entry.__init__(self, **kwargs)
        self.__multiword = multiword
        if self.__multiword:
            completion = EntryCompletionMultiWord()
        else:
            completion = gtk.EntryCompletion()
        self.set_completion(completion)
        cell = gtk.CellRendererText()
        completion.pack_start(cell)
        completion.set_text_column(0)
        self.set_lexicon(lexicon)
        self.set_learn(learn)
    # END_DEF: __init__

    def set_lexicon(self, lexicon):
        if lexicon is not None:
            self.get_completion().set_model(lexicon)
    # END_DEF: set_lexicon

    def set_learn(self, enable):
        """
        Set whether learning should happen
        """
        self.learn = enable
    # END_DEF: set_learn

    def get_text(self):
        text = gtk.Entry.get_text(self)
        if self.learn:
            completion = self.get_completion()
            model = completion.get_model()
            text_col = completion.get_text_column()
            lexicon = [row[text_col] for row in model]
            lexicon.sort()
            if self.__multiword:
                new_words = []
                for word in utils.extract_words(text):
                    if not utils.contains(lexicon, word):
                        new_words.append(word)
                for word in new_words:
                    model.append([word])
            else:
                text = text.strip()
                if text not in lexicon:
                    model.append([text])
        return text
    # END_DEF: get_text
# END_CLASS: TextEntryAutoComplete

### Miscellaneous Data Entry

class Choice(gtk.ComboBox):
    def __init__(self, choices):
        gtk.ComboBox.__init__(self, gtk.ListStore(str))
        cell = gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, 'text', 0)
        for choice in choices:
            self.get_model().append([choice])
    # END_DEF: __init__

    def get_selection(self):
        index = self.get_active()
        return index if index >= 0 else None
    # END_DEF: get_selection

    def set_selection(self, index):
        self.set_active(index if index is not None else -1)
    # END_DEF: set_selection
# END_CLASS: Choice

class ColouredLabel(gtk.EventBox):
    def __init__(self, label=''):
        gtk.EventBox.__init__(self)
        self.label = gtk.Label(label)
        self.add(self.label)
        self.show_all()
    # END_DEF: __init__()

    def modify_base(self, state, colour):
        gtk.EventBox.modify_base(self, state, colour)
        self.label.modify_base(state, colour)
    # END_DEF: modify_base

    def modify_text(self, state, colour):
        gtk.EventBox.modify_text(self, state, colour)
        self.label.modify_text(state, colour)
    # END_DEF: modify_text

    def modify_fg(self, state, colour):
        gtk.EventBox.modify_fg(self, state, colour)
        self.label.modify_fg(state, colour)
    # END_DEF: modify_fg
# END_CLASS: ColouredLabel

class ColouredButton(gtk.Button):
    def __init__(self, *args, **kwargs):
        if 'label' not in kwargs:
            # The label child won't be created until the label is set
            kwargs['label'] = ''
        if 'colour' in kwargs:
            colour = kwargs['colour']
            del kwargs['colour']
        else:
            colour = None
        gtk.Button.__init__(self, *args, **kwargs)
        if sys.platform[:3] == 'win':
            # Crude workaround for Windows 7
            label = self.get_children()[0]
            clabel = ColouredLabel(label.get_text())
            self.remove(label)
            self.add(clabel)
        self.label =  self.get_children()[0]
        style = self.get_style()
        self._ratio = {}
        self._ratio[gtk.STATE_NORMAL] = fractions.Fraction(1)
        nbg = sum(gdk_color_to_rgb(style.bg[gtk.STATE_NORMAL]))
        for state in [gtk.STATE_ACTIVE, gtk.STATE_PRELIGHT]:
            sbg = sum(gdk_color_to_rgb(style.bg[state]))
            self._ratio[state] = fractions.Fraction(sbg, nbg)
        if colour is not None:
            self.set_colour(colour)
    # END_DEF: __init__

    def set_colour(self, colour):
        for state in [gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_ACTIVE]:
            rgb = [min(int(colour[i] * self._ratio[state]), 65535) for i in range(3)]
            bg_gcolour = gtk.gdk.Color(*rgb)
            fg_gcolour = best_foreground(rgb)
            for widget in [self, self.label]:
                bg_colour = widget.get_colormap().alloc_color(bg_gcolour)
                fg_colour = widget.get_colormap().alloc_color(fg_gcolour)
                widget.modify_base(state, bg_colour)
                widget.modify_bg(state, bg_colour)
                widget.modify_fg(state, fg_colour)
                widget.modify_text(state, fg_colour)
    # END_DEF: set_colour
# END_CLASS: ColouredButton

class ColouredSpinButton(gtk.SpinButton):
    def __init__(self, *args, **kwargs):
        if 'colour' in kwargs:
            colour = kwargs['colour']
            del kwargs['colour']
        else:
            colour = None
        gtk.SpinButton.__init__(self, *args, **kwargs)
        style = self.get_style()
        self._ratio = {}
        self._ratio[gtk.STATE_NORMAL] = 1
        nbg = sum(gdk_color_to_rgb(style.bg[gtk.STATE_NORMAL]))
        for state in [gtk.STATE_ACTIVE, gtk.STATE_PRELIGHT]:
            sbg = sum(gdk_color_to_rgb(style.bg[state]))
            self._ratio[state] = fractions.Fraction(sbg, nbg)
        if colour is not None:
            self.set_colour(colour)
    # END_DEF: __init__()

    def set_colour(self, colour):
        """
        Set the background colour.
        colour: an rgb value describing the required background colour
        """
        for state in [gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_ACTIVE]:
            rgb = [min(int(colour[i] * self._ratio[state]), 65535) for i in range(3)]
            bg_colour = self.get_colormap().alloc_color(gtk.gdk.Color(*rgb))
            fg_colour = self.get_colormap().alloc_color(best_foreground(rgb))
            self.modify_base(state, bg_colour)
            self.modify_bg(state, bg_colour)
            self.modify_fg(state, fg_colour)
            self.modify_text(state, fg_colour)
    # END_DEF: ColouredSpinButton
# END_CLASS: ColouredSpinButton

class ActionButton(gtk.Button):
    def __init__(self, action, use_underline=True):
        label = action.get_property("label")
        stock_id = action.get_property("stock-id")
        if label is not None:
            # Empty (NB not None) label means use image only
            gtk.Button.__init__(self, use_underline=use_underline)
            if stock_id is not None:
                image = gtk.Image()
                image.set_from_stock(stock_id, gtk.ICON_SIZE_BUTTON)
                self.set_image(image)
            if label:
                self.set_label(label)
        else:
            gtk.Button.__init__(self, stock=stock_id, label=label, use_underline=use_underline)
        self.set_tooltip_text(action.get_property("tooltip"))
        action.connect_proxy(self)
    # END_DEF: __init__
# END_CLASS: ActionButton

class ActionButtonList:
    def __init__(self, action_group_list, action_name_list=None, use_underline=True):
        self.list = []
        self.dict = {}
        if action_name_list:
            for a_name in action_name_list:
                for a_group in action_group_list:
                    action = a_group.get_action(a_name)
                    if action:
                        button = ActionButton(action, use_underline)
                        self.list.append(button)
                        self.dict[a_name] = button
                        break
        else:
            for a_group in action_group_list:
                for action in a_group.list_actions():
                    button = ActionButton(action, use_underline)
                    self.list.append(button)
                    self.dict[action.get_name()] = button
    # END_DEF: __init__
# END_CLASS: ActionButtonList

class ActionHButtonBox(gtk.HBox):
    def __init__(self, action_group_list, action_name_list=None,
                 use_underline=True, expand=True, fill=True, padding=0):
        gtk.HBox.__init__(self)
        self.button_list = ActionButtonList(action_group_list, action_name_list, use_underline)
        for button in self.button_list.list:
            self.pack_start(button, expand, fill, padding)
    # END_DEF: __init__
# END_CLASS: ActionHButtonBox

### Lists and Trees

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
        self.set_values(model_iter, *col_values)
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

### Dialogues

class ScrolledMessageDialog(gtk.Dialog):
    icons = {
        gtk.MESSAGE_INFO: gtk.STOCK_DIALOG_INFO,
        gtk.MESSAGE_WARNING: gtk.STOCK_DIALOG_WARNING,
        gtk.MESSAGE_QUESTION: gtk.STOCK_DIALOG_QUESTION,
        gtk.MESSAGE_ERROR: gtk.STOCK_DIALOG_ERROR,
    }
    labels = {
        gtk.MESSAGE_INFO: _('FYI'),
        gtk.MESSAGE_WARNING: _('Warning'),
        gtk.MESSAGE_QUESTION: _('Question'),
        gtk.MESSAGE_ERROR: _('Error'),
    }

    @staticmethod
    def copy_cb(tview):
        tview.get_buffer().copy_clipboard(gtk.clipboard_get())
    # END_DEF: copy_cb

    def __init__(self, parent=None, flags=gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT, type=gtk.MESSAGE_INFO, buttons=None, message_format=None):
        gtk.Dialog.__init__(self, title='{0}: {1}'.format(sys.argv[0], self.labels[type]), parent=parent, flags=flags, buttons=buttons)
        hbox = gtk.HBox()
        icon = gtk.Image()
        icon.set_from_stock(self.icons[type], gtk.ICON_SIZE_DIALOG)
        hbox.pack_start(icon, expand=False, fill=False)
        label = gtk.Label(self.labels[type])
        label.modify_font(pango.FontDescription('bold 35'))
        hbox.pack_start(label, expand=False, fill=False)
        self.get_content_area().pack_start(hbox, expand=False, fill=False)
        sbw = gtk.ScrolledWindow()
        sbw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        tview = gtk.TextView()
        tview.set_size_request(480,120)
        tview.set_editable(False)
        tview.get_buffer().set_text(message_format.strip())
        tview.connect('copy-clipboard', ScrolledMessageDialog.copy_cb)
        sbw.add(tview)
        self.get_content_area().pack_end(sbw, expand=True, fill=True)
        self.show_all()
        self.set_resizable(True)
    # END_DEF: __init__
# END_CLASS: ScrolledMessageDialog

class CancelOKDialog(gtk.Dialog):
    def __init__(self, title=None, parent=None):
        flags = gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OK, gtk.RESPONSE_OK)
        gtk.Dialog.__init__(self, title, parent, flags, buttons)
    # END_DEF: __init__
# END_CLASS: CancelOKDialog

class TextEntryDialog(CancelOKDialog):
    def __init__(self, title=None, prompt=None, suggestion="", parent=None):
        CancelOKDialog.__init__(self, title, parent)
        self.hbox = gtk.HBox()
        self.vbox.add(self.hbox)
        self.hbox.show()
        if prompt:
            self.hbox.pack_start(gtk.Label(prompt), fill=False, expand=False)
        self.entry = gtk.Entry()
        self.entry.set_width_chars(32)
        self.entry.set_text(suggestion)
        self.hbox.pack_start(self.entry)
        self.show_all()
    # END_DEF: __init__
# END_CLASS: TextEntryDialog

class UnsavedChangesDialogue(gtk.Dialog):
    # TODO: make a better UnsavedChangesDialogue()
    SAVE_AND_CONTINUE, CONTINUE_UNSAVED = range(1, 3)

    def __init__(self, parent, message):
        buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        buttons += (_('Save and Continue'), UnsavedChangesDialogue.SAVE_AND_CONTINUE)
        buttons += (_('Continue Without Saving'), UnsavedChangesDialogue.CONTINUE_UNSAVED)
        gtk.Dialog.__init__(self,
            parent=parent,
            flags=gtk.DIALOG_MODAL,
            buttons=buttons,
        )
        self.vbox.pack_start(gtk.Label(message))
        self.show_all()
    # END_DEF: __init__
# END_CLASS: UnsavedChangesDialogue
