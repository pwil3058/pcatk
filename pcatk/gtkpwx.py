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

class ColourableLabel(gtk.EventBox):
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
# END_CLASS: ColourableLabel

class ColouredLabel(ColourableLabel):
    def __init__(self, label, colour=None):
        ColourableLabel.__init__(self, label=label)
        if colour is not None:
            self.set_colour(colour)
    # END_DEF: __init__()

    def set_colour(self, colour):
        bg_colour = self.get_colormap().alloc_color(gtk.gdk.Color(*colour))
        fg_colour = self.get_colormap().alloc_color(best_foreground(colour))
        for state in [gtk.STATE_NORMAL, gtk.STATE_PRELIGHT, gtk.STATE_ACTIVE]:
            self.modify_base(state, bg_colour)
            self.modify_bg(state, bg_colour)
            self.modify_fg(state, fg_colour)
            self.modify_text(state, fg_colour)
    # END_DEF: set_colour
# END_CLASS: ColouredLabel

class ColouredButton(gtk.EventBox):
    prelit_width = 2
    unprelit_width = 0
    state_value_ratio = {
        gtk.STATE_NORMAL: fractions.Fraction(1),
        gtk.STATE_ACTIVE: fractions.Fraction(1, 2),
        gtk.STATE_PRELIGHT: fractions.Fraction(1),
        gtk.STATE_SELECTED: fractions.Fraction(1),
        gtk.STATE_INSENSITIVE: fractions.Fraction(1, 4)
    }
    def __init__(self, colour=None, label=None):
        self.label = gtk.Label(label)
        gtk.EventBox.__init__(self)
        self.set_size_request(25, 25)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK|gtk.gdk.BUTTON_RELEASE_MASK|gtk.gdk.LEAVE_NOTIFY_MASK|gtk.gdk.FOCUS_CHANGE_MASK)
        self.connect('button-press-event', self._button_press_cb)
        self.connect('button-release-event', self._button_release_cb)
        self.connect('enter-notify-event', self._enter_notify_cb)
        self.connect('leave-notify-event', self._leave_notify_cb)
        self.frame = gtk.Frame()
        self.frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.frame.set_border_width(self.unprelit_width)
        self.frame.add(self.label)
        self.add(self.frame)
        if colour is not None:
            self.set_colour(colour)
        self.show_all()
    # END_DEF: __init__

    def _button_press_cb(self, widget, event):
        if event.button != 1:
            return False
        self.frame.set_shadow_type(gtk.SHADOW_IN)
        self.set_state(gtk.STATE_ACTIVE)
    # END_DEF: _button_press_cb

    def _button_release_cb(self, widget, event):
        if event.button != 1:
            return False
        self.frame.set_shadow_type(gtk.SHADOW_OUT)
        self.set_state(gtk.STATE_PRELIGHT)
        self.emit('clicked')
    # END_DEF: _button_release_cb

    def _enter_notify_cb(self, widget, event):
        self.frame.set_shadow_type(gtk.SHADOW_OUT)
        self.frame.set_border_width(self.prelit_width)
        self.set_state(gtk.STATE_PRELIGHT)
    # END_DEF: _enter_notify_cb

    def _leave_notify_cb(self, widget, event):
        self.frame.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.frame.set_border_width(self.unprelit_width)
        self.set_state(gtk.STATE_NORMAL)
    # END_DEF: _leave_notify_cb

    def set_colour(self, colour):
        self.colour = colour
        for state, value_ratio in self.state_value_ratio.items():
            rgb = [min(int(colour[i] * value_ratio), 65535) for i in range(3)]
            bg_gcolour = self.get_colormap().alloc_color(gtk.gdk.Color(*rgb))
            fg_gcolour = self.get_colormap().alloc_color(best_foreground(rgb))
            self.modify_base(state, bg_gcolour)
            self.modify_bg(state, bg_gcolour)
            self.modify_fg(state, fg_gcolour)
            self.modify_text(state, fg_gcolour)
    # END_DEF: set_colour
gobject.signal_new('clicked', ColouredButton, gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
# END_CLASS: ColouredButton

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
