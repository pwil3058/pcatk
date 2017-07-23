

class PaintMixer(Gtk.VBox, actions.CAGandUIManager, dialogue.AskerMixin, dialogue.ReporterMixin):
    recollect.define("mixer", "hpaned_position", recollect.Defn(int, -1))
    recollect.define("mixer", "vpaned_position", recollect.Defn(int, -1))
    PAINT = None
    MATCHED_PAINT_LIST_VIEW = None
    PAINT_SERIES_MANAGER = None
    PAINT_STANDARDS_MANAGER = None
    PAINT_INFO_DIALOGUE = gpaint.PaintColourInformationDialogue
    MIXED_PAINT_INFORMATION_DIALOGUE = None
    MIXTURE = None
    MIXED_PAINT = None
    TARGET_COLOUR = None
    UI_DESCR = """
    <ui>
        <toolbar name="mixer_toolbar">
            <toolitem action="print_mixer"/>
        </toolbar>
    </ui>
    """
    AC_HAVE_MIXTURE, AC_MASK = actions.ActionCondns.new_flags_and_mask(1)
    AC_HAVE_TARGET, AC_DONT_HAVE_TARGET, AC_TARGET_MASK = actions.ActionCondns.new_flags_and_mask(2)
    def __init__(self, *, paint_series_manager=None, paint_standards_manager=None):
        Gtk.VBox.__init__(self)
        actions.CAGandUIManager.__init__(self)
        self.action_groups.update_condns(actions.MaskedCondns(self.AC_DONT_HAVE_TARGET, self.AC_TARGET_MASK))
        # Components
        self.paint_series_manager = paint_series_manager if paint_series_manager else self.PAINT_SERIES_MANAGER()
        self.paint_series_manager.connect("add-paint-colours", self._add_colours_to_mixer_cb)
        if self.PAINT_STANDARDS_MANAGER:
            self.standards_manager = paint_standards_manager if paint_standards_manager else self.PAINT_STANDARDS_MANAGER()
        else:
            self.standards_manager = paint_standards_manager
        if self.standards_manager:
            self.standards_manager.connect("set_target_colour", lambda _widget, standard_paint: self._set_new_mixed_colour_fm_standard(standard_paint))
            self.standards_manager.set_target_setable(True)
        self.notes = entries.TextEntryAutoComplete(lexicon.GENERAL_WORDS_LEXICON)
        self.notes.connect("new-words", lexicon.new_general_words_cb)
        self.next_name_label = Gtk.Label(label=_("#???:"))
        self.current_target_colour = None
        self.current_colour_description = entries.TextEntryAutoComplete(lexicon.COLOUR_NAME_LEXICON)
        self.current_colour_description.connect("new-words", lexicon.new_paint_words_cb)
        self.mixpanel = gpaint.ColourMatchArea()
        self.mixpanel.set_size_request(240, 240)
        self.hcvw_display = gpaint.HCVDisplay()
        self.paint_colours = PaintPartsSpinButtonBox()
        self.paint_colours.connect("remove-paint", self._remove_paint_colour_cb)
        self.paint_colours.connect("contributions-changed", self._contributions_changed_cb)
        self.mixed_colours = self.MATCHED_PAINT_LIST_VIEW.MODEL()
        self.mixed_colours_view = self.MATCHED_PAINT_LIST_VIEW(self.mixed_colours)
        self.mixed_colours_view.action_groups.connect_activate("remove_selected_paints", self._remove_mixed_colours_cb)
        self.mixed_count = 0
        self.wheels = gpaint.HueWheelNotebook()
        self.wheels.set_size_request(360, 360)
        self.wheels.set_wheels_colour_info_acb(self._show_wheel_colour_details_cb)
        self.buttons = self.action_groups.create_action_button_box([
            "new_mixed_colour",
            "new_mixed_standard_colour",
            "accept_mixed_colour",
            "simplify_contributions",
            "reset_contributions",
            "cancel_mixed_colour",
            "remove_unused_paints"
        ])
        toolbar = self.ui_manager.get_widget("/mixer_toolbar")
        # Lay out components
        self.pack_start(Gtk.HSeparator(), expand=False, fill=True, padding=0)
        self.pack_start(toolbar, expand=False, fill=True, padding=0)
        self.pack_start(Gtk.HSeparator(), expand=False, fill=True, padding=0)
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_("Notes:")), expand=False, fill=True, padding=0)
        hbox.pack_start(self.notes, expand=True, fill=True, padding=0)
        self.pack_start(hbox, expand=False, fill=True, padding=0)
        hpaned = Gtk.HPaned()
        hpaned.pack1(self.wheels, resize=True, shrink=False)
        vbox = Gtk.VBox()
        vhbox = Gtk.HBox()
        vhbox.pack_start(self.next_name_label, expand=False, fill=True, padding=0)
        vhbox.pack_start(self.current_colour_description, expand=True, fill=True, padding=0)
        vbox.pack_start(vhbox, expand=False, fill=True, padding=0)
        vbox.pack_start(self.hcvw_display, expand=False, fill=True, padding=0)
        vbox.pack_start(gutils.wrap_in_frame(self.mixpanel, Gtk.ShadowType.ETCHED_IN), expand=True, fill=True, padding=0)
        hpaned.pack2(vbox, resize=True, shrink=False)
        vpaned = Gtk.VPaned()
        vpaned.pack1(hpaned, resize=True, shrink=False)
        vbox = Gtk.VBox()
        hbox = Gtk.HBox()
        hbox.pack_start(Gtk.Label(_("Paints:")), expand=False, fill=True, padding=0)
        hbox.pack_start(self.paint_colours, expand=True, fill=True, padding=0)
        vbox.pack_start(hbox, expand=False, fill=True, padding=0)
        vbox.pack_start(self.buttons, expand=False, fill=True, padding=0)
        vbox.pack_start(gutils.wrap_in_scrolled_window(self.mixed_colours_view), expand=True, fill=True, padding=0)
        vpaned.pack2(vbox, resize=True, shrink=False)
        self.pack_start(vpaned, expand=True, fill=True, padding=0)
        vpaned.set_position(recollect.get("mixer", "vpaned_position"))
        hpaned.set_position(recollect.get("mixer", "hpaned_position"))
        vpaned.connect("notify", self._paned_notify_cb)
        hpaned.connect("notify", self._paned_notify_cb)
        self.connect("key-press-event", self.handle_key_press_cb)
        msm = self.ui_manager.get_widget("/mixer_menubar/mixer_series_manager_menu")
        if msm:
            msmm = msm.get_submenu()
            msmm.prepend(self.paint_series_manager.open_menu_item)
            msmm.append(self.paint_series_manager.remove_menu_item)
        if self.standards_manager:
            msm = self.ui_manager.get_widget("/mixer_menubar/mixer_standards_manager_menu")
            if msm:
                msmm = msm.get_submenu()
                msmm.prepend(self.standards_manager.open_menu_item)
                msmm.append(self.standards_manager.remove_menu_item)
        self.show_all()
        self.recalculate_colour([])

    def handle_key_press_cb(self, widget, event):
        if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            if event.keyval in [Gdk.KEY_q, Gdk.KEY_Q]:
                widget._quit_mixer()
                return True
        return False

    def _paned_notify_cb(self, widget, parameter):
        if parameter.name == "position":
            if isinstance(widget, Gtk.HPaned):
                recollect.set("mixer", "hpaned_position", str(widget.get_position()))
            else:
                recollect.set("mixer", "vpaned_position", str(widget.get_position()))

    def populate_action_groups(self):
        """
        Set up the actions for this component
        """
        self.action_groups[actions.AC_DONT_CARE].add_actions([
            ("mixer_file_menu", None, _("File")),
            ("mixer_series_manager_menu", None, _("Paint Colour Series")),
            ("mixer_standards_manager_menu", None, _("Paint Colour Standards")),
            ("reference_resource_menu", None, _("Reference Resources")),
            ("remove_unused_paints", None, _("Remove Unused Paints"), None,
             _("Remove all unused paints from the mixer."),
             lambda _action: self._remove_unused_paints()
            ),
            ("mixer_load_paint_series", None, _("Load"), None,
             _("Load a paint series from a file."),
             lambda _action: self.paint_series_manager.add_paint_series()
            ),
            ("mixer_load_paint_standard", None, _("Load"), None,
             _("Load a paint standard from a file."),
             lambda _action: self.standards_manager.add_paint_standard()
            ),
            ("quit_mixer", Gtk.STOCK_QUIT, None, None,
             _("Quit this program."),
             lambda _action: self._quit_mixer()
            ),
            ("print_mixer", Gtk.STOCK_PRINT, None, None,
             _("Print a text description of the mixer."),
             lambda _action: self.print_mixing_session()
            ),
        ])
        self.action_groups[self.AC_HAVE_MIXTURE].add_actions([
            ("simplify_contributions", None, _("Simplify"), None,
             _("Simplify all paint contributions (by dividing by their greatest common divisor)."),
             lambda _action: self.simplify_parts()
            ),
            ("reset_contributions", None, _("Reset"), None,
             _("Reset all paint contributions to zero."),
             lambda _action: self.reset_parts()
            ),
        ])
        self.action_groups[self.AC_HAVE_MIXTURE|self.AC_HAVE_TARGET].add_actions([
            ("accept_mixed_colour", None, _("Accept"), None,
             _("Accept/finalise this colour and add it to the list of  mixed colours."),
             lambda _action: self._accept_mixed_colour()
            ),
        ])
        self.action_groups[self.AC_HAVE_TARGET].add_actions([
            ("cancel_mixed_colour", None, _("Cancel"), None,
             _("Cancel this mixed colour: clearing the target and resetting contributions to zero."),
             lambda _action: self._reset_mixed_colour()
            ),
        ])
        self.action_groups[self.AC_DONT_HAVE_TARGET].add_actions([
            ("new_mixed_colour", None, _("New"), None,
             _("Start working on a new mixed colour."),
             lambda _action: self._new_mixed_colour_fm_dlg()
            ),
            ("new_mixed_standard_colour", None, _("New (From Standards)"), None,
             _("Start working on a new mixed colour to replicate an existing standard."),
             lambda _action: self._new_mixed_standard_colour()
            ),
        ])
    def _show_wheel_colour_details_cb(self, _action, wheel):
        colour = wheel.popup_colour
        if hasattr(colour, "blobs"):
            self.MIXED_PAINT_INFORMATION_DIALOGUE(colour, self.mixed_colours.get_target_colour(colour)).show()
        elif isinstance(colour, vpaint.TargetColour):
            TargetColourInformationDialogue(colour).show()
        else:
            self.PAINT_INFO_DIALOGUE(colour).show()
        return True
    def __str__(self):
        paint_colours = self.paint_colours.get_colours()
        if len(paint_colours) == 0:
            return _("Empty Mix/Match Description")
        string = _("Paint Colours:\n")
        for pcol in paint_colours:
            string += "{0}: {1}: {2}\n".format(pcol.name, pcol.series.series_id.maker, pcol.series.series_id.name)
        num_mixed_colours = len(self.mixed_colours)
        if num_mixed_colours == 0:
            return string
        # Print the list in the current order chosen by the user
        string += _("Mixed Colours:\n")
        for mc in self.mixed_colours.get_colours():
            string += "{0}: {1}\n".format(mc.name, round(mc.value, 2))
            for cc, parts in mc.blobs:
                if hasattr(cc, "series"):
                    string += "\t {0}:\t{1}: {2}: {3}\n".format(parts, cc.name, cc.series.series_id.maker, cc.series.series_id.name)
                else:
                    string += "\t {0}:\t{1}\n".format(parts, cc.name)
        return string
    def pango_markup_chunks(self):
        """
        Format the palette description as a list of Pango markup chunks
        """
        paint_colours = self.paint_colours.get_paints()
        if len(paint_colours) == 0:
            return [cgi.escape(_("Empty Mix/Match Description"))]
        # TODO: add paint series data in here
        string = "<b>" + cgi.escape(_("Mix/Match Description:")) + "</b> "
        string += cgi.escape(time.strftime("%X: %A %x")) + "\n"
        if self.notes.get_text_length() > 0:
            string += "\n{0}\n".format(cgi.escape(self.notes.get_text()))
        chunks = [string]
        string = "<b>" + cgi.escape(_("Paint Colours:")) + "</b>\n\n"
        for pcol in paint_colours:
            string += "<span background=\"{0}\">\t</span> ".format(pango_rgb_str(pcol.rgb16))
            string += "{0}\n".format(cgi.escape(pcol.name))
        chunks.append(string)
        string = "<b>" + cgi.escape(_("Mixed Colours:")) + "</b>\n\n"
        for tmc in self.mixed_colours:
            mc = tmc[0]
            tc = tmc[1]
            string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(mc.rgb16))
            string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(mc.value_rgb.rgb16))
            string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(mc.hue_rgb.rgb16))
            string += " {0}: {1}\n".format(cgi.escape(mc.name), cgi.escape(mc.notes))
            string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(tc.rgb16))
            string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(tc.value_rgb.rgb16))
            string += "<span background=\"{0}\">\t</span> Target Colour\n".format(pango_rgb_str(tc.hue.rgb.rgb16))
            for blob in mc.blobs:
                string += "{0: 7d}:".format(blob.parts)
                string += "<span background=\"{0}\">\t</span>".format(pango_rgb_str(blob.paint.rgb16))
                string += " {0}\n".format(cgi.escape(blob.paint.name))
            chunks.append(string)
            string = "" # Necessary because we put header in the first chunk
        return chunks
    def _contributions_changed_cb(self, _widget, contributions):
        self.recalculate_colour(contributions)
    def recalculate_colour(self, contributions):
        if len(contributions) > 0:
            new_colour = self.MIXTURE(contributions)
            self.mixpanel.set_bg_colour(new_colour.rgb)
            self.hcvw_display.set_colour(new_colour)
            self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_MIXTURE, self.AC_MASK))
        else:
            self.mixpanel.set_bg_colour(None)
            self.hcvw_display.set_colour(None)
            self.action_groups.update_condns(actions.MaskedCondns(0, self.AC_MASK))
    def _accept_mixed_colour(self):
        self.simplify_parts()
        paint_contribs = self.paint_colours.get_contributions()
        if len(paint_contribs) < 1:
            return
        self.mixed_count += 1
        name = _("Mix #{:03d}").format(self.mixed_count)
        notes = self.current_colour_description.get_text()
        new_colour =  self.MIXED_PAINT(blobs=paint_contribs, name=name, notes=notes)
        target_name = _("Target #{:03d}").format(self.mixed_count)
        target_colour = self.TARGET_COLOUR(target_name, self.current_target_colour, self.current_colour_description.get_text())
        self.mixed_colours.append_paint(new_colour, target_colour)
        self.wheels.add_paint(new_colour)
        self.wheels.add_target_colour(name, target_colour)
        self._reset_mixed_colour()
    def _reset_mixed_colour(self):
        self.reset_parts()
        #self.paint_colours.set_sensitive(False)
        self.mixpanel.clear()
        self.current_colour_description.set_text("")
        self.current_target_colour = None
        self.hcvw_display.set_colour(None)
        self.hcvw_display.set_target_colour(None)
        self.wheels.unset_crosshair()
        self.paint_series_manager.unset_target_colour()
        self.action_groups.update_condns(actions.MaskedCondns(self.AC_DONT_HAVE_TARGET, self.AC_TARGET_MASK))
        if self.standards_manager:
            self.standards_manager.set_target_setable(True)
        self.next_name_label.set_text(_("#???:"))
        self.current_colour_description.set_text("")
    def _set_new_mixed_colour(self, *, description, colour):
        self.current_colour_description.set_text(description)
        self.current_target_colour = colour
        self.mixpanel.set_target_colour(self.current_target_colour)
        self.hcvw_display.set_target_colour(self.current_target_colour)
        self.wheels.set_crosshair(self.current_target_colour)
        self.paint_series_manager.set_target_colour(self.current_target_colour)
        self.action_groups.update_condns(actions.MaskedCondns(self.AC_HAVE_TARGET, self.AC_TARGET_MASK))
        if self.standards_manager:
            self.standards_manager.set_target_setable(False)
        self.next_name_label.set_text(_("#{:03d}:").format(self.mixed_count + 1))
        #self.paint_colours.set_sensitive(True)
    def _new_mixed_colour_fm_dlg(self):
        class Dialogue(NewMixedColourDialogue):
            COLOUR = self.PAINT.COLOUR
        dlg = Dialogue(self.mixed_count + 1, self.get_toplevel())
        if dlg.run() == Gtk.ResponseType.ACCEPT:
            descr = dlg.colour_description.get_text()
            assert len(descr) > 0
            self._set_new_mixed_colour(description=descr, colour=dlg.colour_specifier.colour)
        dlg.destroy()
    def _set_new_mixed_colour_fm_standard(self, standard_paint):
        notes = standard_paint.get_named_extra("notes")
        description = "{}: {}".format(standard_paint.name, notes) if notes else standard_paint.name
        self._set_new_mixed_colour(description=description, colour=standard_paint.colour)
    def _new_mixed_standard_colour(self):
        standard_paint_id = self.standards_manager.ask_standard_paint_name()
        if standard_paint_id:
            standard_paint = self.standards_manager.get_standard_paint(standard_paint_id)
            if standard_paint:
                self._set_new_mixed_colour_fm_standard(standard_paint)
            else:
                self.inform_user(_("{}: unknown paint standard identifier").format(standard_paint_id))
    def reset_parts(self):
        self.paint_colours.reset_parts()
    def simplify_parts(self):
        self.paint_colours.simplify_parts()
    def add_paint(self, paint_colour):
        self.paint_colours.add_paint(paint_colour)
        self.wheels.add_paint(paint_colour)
    def del_paint(self, paint_colour):
        self.paint_colours.del_paint(paint_colour)
        self.wheels.del_paint(paint_colour)
    def del_mixed(self, mixed):
        self.mixed_colours.remove_colour(mixed)
        self.wheels.del_paint(mixed)
        self.wheels.del_target_colour(mixed.name)
    def _add_colours_to_mixer_cb(self, selector, colours):
        for pcol in colours:
            if not self.paint_colours.has_paint(pcol):
                self.add_paint(pcol)
    def _remove_paint_colour_cb(self, widget, colour):
        """
        Respond to a request from a paint colour to be removed
        """
        users = self.mixed_colours.get_paint_users(colour)
        if len(users) > 0:
            string = _("Colour: \"{0}\" is used in:\n").format(colour)
            for user in users:
                string += "\t{0}\n".format(user.name)
            dlg = dialogue.ScrolledMessageDialog(text=string)
            Gdk.beep()
            dlg.run()
            dlg.destroy()
        else:
            self.del_paint(colour)
    def _remove_mixed_colours_cb(self, _action):
        colours = self.mixed_colours_view.get_selected_colours()
        if len(colours) == 0:
            return
        msg = _("The following mixed colours are about to be deleted:\n")
        for colour in colours:
            msg += "\t{0}: {1}\n".format(colour.name, colour.notes)
        msg += _("and will not be recoverable. OK?")
        if self.ask_ok_cancel(msg):
            for colour in colours:
                self.del_mixed(colour)
    def _remove_unused_paints(self):
        paints = self.paint_colours.get_paints_with_zero_parts()
        for paint in paints:
            if len(self.mixed_colours.get_paint_users(paint)) == 0:
                self.del_paint(paint)
    def print_mixing_session(self):
        """
        Print the mixer as simple text
        """
        # TODO: make printing more exotic
        printer.print_markup_chunks(self.pango_markup_chunks())
    def _open_reference_image_viewer_cb(self, _action):
        """
        Launch a window containing a reference image viewer
        """
        ReferenceImageViewer(self.get_toplevel()).show()
    def _quit_mixer(self):
        """
        Exit the program
        """
        # TODO: add checks for unsaved work in mixer before exiting
        Gtk.main_quit()
