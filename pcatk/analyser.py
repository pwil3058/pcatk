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
Analyse digital images in a painterly way
'''

import fractions

from gi.repository import Gtk

from .gtx import iview

from . import pixbuf

class Analysis(object):
    """
    A wrapper for an artistic analytical view of an image
    """
    TRANSFORMER = None
    def __init__(self, image):
        """
        image: an instance of Image() for which this wrapper provides a
        particular view
        """
        self.__image = image
        self.pixbuf_view = iview.PixbufView()
        self.transformer = self.TRANSFORMER()
        self.update_pixbuf()
    def get_label(self):
        return self.transformer.LABEL
    def initialize_parameters(self):
        pass
    def update_pixbuf(self):
        self.pixbuf_view.set_pixbuf(self.transformer.transformed_pixbuf(self.__image))

ANALYSES = []

class AnalysisRaw(Analysis):
    TRANSFORMER = pixbuf.TransformerRaw
ANALYSES.append(AnalysisRaw)

class AnalysisNotan(Analysis):
    TRANSFORMER = pixbuf.TransformerNotan
ANALYSES.append(AnalysisNotan)

class AnalysisValue(Analysis):
    TRANSFORMER = pixbuf.TransformerValue
ANALYSES.append(AnalysisValue)

class AnalysisRestrictedValue(Analysis):
    TRANSFORMER = pixbuf.TransformerRestrictedValue
ANALYSES.append(AnalysisRestrictedValue)

class AnalysisColourRestrictedValue(Analysis):
    TRANSFORMER = pixbuf.TransformerColourRestrictedValue
ANALYSES.append(AnalysisColourRestrictedValue)

class AnalysisRestrictedHue(Analysis):
    TRANSFORMER = pixbuf.TransformerRestrictedHue
ANALYSES.append(AnalysisRestrictedHue)

class AnalysisRestrictedHueValue(Analysis):
    TRANSFORMER = pixbuf.TransformerRestrictedHueValue
ANALYSES.append(AnalysisRestrictedHueValue)

class AnalysisHighChroma(Analysis):
    TRANSFORMER = pixbuf.TransformerHighChroma
ANALYSES.append(AnalysisHighChroma)

class Analyser(Gtk.VBox):
    def __init__(self):
        Gtk.VBox.__init__(self)
        self.__image = pixbuf.RGBHImage()
        self.__image.connect('progress-made', self._progress_made_cb)
        self.__analyses = [A(self.__image) for A in ANALYSES]
        self.notebook = Gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.popup_enable()
        for analysis in self.__analyses:
            self.notebook.append_page(analysis.pixbuf_view, Gtk.Label(analysis.get_label()))
        self.notebook.show_all()
        self.progress_bar = Gtk.ProgressBar()
        self.pack_start(self.notebook, expand=True, fill=True, padding=0)
        # Leave packing of the progress_bar to the user
        self.show_all()
    def set_pixbuf(self, pixbuf):
        self.progress_bar.set_text(_('Analysing Image'))
        self.__image.set_from_pixbuf(pixbuf)
        for analysis in self.__analyses:
            self.progress_bar.set_text(_('Generating {0} Image').format(analysis.get_label()))
            analysis.update_pixbuf()
        self.progress_bar.set_text(_(''))
        self.progress_bar.set_fraction(0)
    def _progress_made_cb(self, _widget, progress):
        """
        Report progress made by anal
        """
        self.progress_bar.set_fraction(progress)
        while Gtk.events_pending():
            Gtk.main_iteration()
    def get_image_size(self):
        return self.__image.size
