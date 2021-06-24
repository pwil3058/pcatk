// Copyright 2020 Peter Williams <pwil3058@gmail.com> <pwil3058@bigpond.net.au>

use std::rc::Rc;

use pw_gix::{
    gtk::{self, prelude::*},
    gtkx::window::RememberGeometry,
    recollections,
    wrapper::*,
};

mod config;
mod pcatk;

fn main() {
    if let Err(err) = gtk::init() {
        panic!("GTK failed to initialize! {}.", err);
    };
    recollections::init(&config::recollection_file_path());
    let win = gtk::Window::new(gtk::WindowType::Toplevel);
    win.set_geometry_from_recollections("main_window", (600, 400));
    if let Some(icon) = icon::pcatkrs_pixbuf(64) {
        win.set_icon(Some(&icon));
    }
    win.set_title("Painter's Colour Assistant Tool Kit");
    let pcatk = pcatk::PaintersColourAssistantTK::new();
    win.add(pcatk.pwo());
    let pcatk_c = Rc::clone(&pcatk);
    win.connect_delete_event(move |_, _| {
        if pcatk_c.ok_to_quit() {
            gtk::Inhibit(false)
        } else {
            gtk::Inhibit(true)
        }
    });
    win.connect_destroy(|_| gtk::main_quit());
    win.show();
    gtk::main()
}

mod icon {
    use pw_gix::{gdk_pixbuf, gtk};

    // XPM
    static PCATKRS_XPM: &[&str] = &[
        "8 8 3 1",
        "R c #FF0000",
        "Y c #FFFF00",
        "_ c #000000",
        "YYRRRRYY",
        "RRYYRRYY",
        "YYRR____",
        "RR______",
        "RRYYRR__",
        "________",
        "YYRRYY__",
        "YYYYYY__",
    ];

    pub fn pcatkrs_pixbuf(size: i32) -> Option<gdk_pixbuf::Pixbuf> {
        gdk_pixbuf::Pixbuf::from_xpm_data(PCATKRS_XPM).scale_simple(
            size,
            size,
            gdk_pixbuf::InterpType::Tiles,
        )
    }

    pub fn _pcatkrs_image(size: i32) -> Option<gtk::Image> {
        if let Some(pixbuf) = pcatkrs_pixbuf(size) {
            Some(gtk::Image::from_pixbuf(Some(&pixbuf)))
        } else {
            None
        }
    }
}
