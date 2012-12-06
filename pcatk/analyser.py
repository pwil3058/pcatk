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

import gtk

from pcatk import pixbuf
from pcatk import iview

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
    # END_DEF: __init__()

    def get_label(self):
        return self.transformer.LABEL
    # END_DEF: get_label

    def initialize_parameters(self):
        pass
    # END_DEF: initialize_parameters

    def update_pixbuf(self):
        self.pixbuf_view.set_pixbuf(self.transformer.transformed_pixbuf(self.__image))
    # END_DEF: update_pixbuf
# END_CLASS: Analysis

ANALYSES = []

class AnalysisRaw(Analysis):
    TRANSFORMER = pixbuf.TransformerRaw
ANALYSES.append(AnalysisRaw)
# END_CLASS: AnalysisRaw

class AnalysisNotan(Analysis):
    TRANSFORMER = pixbuf.TransformerNotan
ANALYSES.append(AnalysisNotan)
# END_CLASS: AnalysisNotan

class AnalysisValue(Analysis):
    TRANSFORMER = pixbuf.TransformerValue
ANALYSES.append(AnalysisValue)
# END_CLASS: AnalysisValue

class AnalysisRestrictedValue(Analysis):
    TRANSFORMER = pixbuf.TransformerRestrictedValue
ANALYSES.append(AnalysisRestrictedValue)
# END_CLASS: AnalysisRestrictedValue

class AnalysisColourRestrictedValue(Analysis):
    TRANSFORMER = pixbuf.TransformerColourRestrictedValue
ANALYSES.append(AnalysisColourRestrictedValue)
# END_CLASS: AnalysisColourRestrictedValue

class AnalysisRestrictedHue(Analysis):
    TRANSFORMER = pixbuf.TransformerRestrictedHue
ANALYSES.append(AnalysisRestrictedHue)
# END_CLASS: AnalysisRestrictedHue

class AnalysisRestrictedHueValue(Analysis):
    TRANSFORMER = pixbuf.TransformerRestrictedHueValue
ANALYSES.append(AnalysisRestrictedHueValue)
# END_CLASS: AnalysisRestrictedHueValue

class AnalysisHighChroma(Analysis):
    TRANSFORMER = pixbuf.TransformerHighChroma
ANALYSES.append(AnalysisHighChroma)
# END_CLASS: AnalysisHighChroma

class Analyser(gtk.VBox):
    def __init__(self):
        gtk.VBox.__init__(self)
        self.__image = pixbuf.RGBHImage()
        self.__image.connect('progress-made', self._progress_made_cb)
        self.__analyses = [A(self.__image) for A in ANALYSES]
        self.notebook = gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.popup_enable()
        for analysis in self.__analyses:
            self.notebook.append_page(analysis.pixbuf_view, gtk.Label(analysis.get_label()))
        self.notebook.show_all()
        self.progress_bar = gtk.ProgressBar()
        self.pack_start(self.notebook, expand=True, fill=True)
        # Leave packing of the progress_bar to the user
        self.show_all()
    # END_DEF: __init__

    def set_pixbuf(self, pixbuf):
        self.progress_bar.set_text(_('Analysing Image'))
        self.__image.set_from_pixbuf(pixbuf)
        for analysis in self.__analyses:
            self.progress_bar.set_text(_('Generating {0} Image').format(analysis.get_label()))
            analysis.update_pixbuf()
        self.progress_bar.set_text(_(''))
        self.progress_bar.set_fraction(0)
    # END_DEF: set_pixbuf

    def _progress_made_cb(self, _widget, progress):
        """
        Report progress made by anal
        """
        self.progress_bar.set_fraction(progress)
        while gtk.events_pending():
            gtk.main_iteration()
    # END_DEF: _progress_made_cb

    def get_image_size(self):
        return self.__image.size
    # END_DEF: get_image_size
# END_CLASS: Analyser
