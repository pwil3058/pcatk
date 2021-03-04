// Copyright 2020 Peter Williams <pwil3058@gmail.com> <pwil3058@bigpond.net.au>

use std::{process::Command, rc::Rc};

use pw_gix::{
    gdk_pixbufx::viewer::PixbufViewBuilder,
    gtk::{self, prelude::*},
    gtkx::window::RememberGeometry,
    sample,
    wrapper::*,
};

use apaint_gtk::{
    characteristics::CharacteristicType,
    colour::ScalarAttribute,
    factory::{BasicPaintFactory, BasicPaintFactoryBuilder},
    mixer::palette::{PalettePaintMixer, PalettePaintMixerBuilder},
};

use crate::config;

#[derive(PWO, Wrapper)]
pub struct PaintersColourAssistantTK {
    vbox: gtk::Box,
    palette: Rc<PalettePaintMixer>,
    factory: Rc<BasicPaintFactory>,
}

impl PaintersColourAssistantTK {
    pub fn new() -> Rc<Self> {
        let attributes = vec![
            ScalarAttribute::Chroma,
            ScalarAttribute::Value,
            ScalarAttribute::Warmth,
        ];
        let characteristics = vec![
            CharacteristicType::Transparency,
            CharacteristicType::Permanence,
        ];
        let palette = PalettePaintMixerBuilder::new()
            .attributes(&attributes)
            .characteristics(&characteristics)
            .config_dir_path(&config::config_dir_path())
            .build();
        let factory = BasicPaintFactoryBuilder::new()
            .attributes(&attributes)
            .characteristics(&characteristics)
            .build();
        let pcatk = Rc::new(Self {
            vbox: gtk::Box::new(gtk::Orientation::Vertical, 0),
            palette,
            factory,
        });
        let hbox = gtk::Box::new(gtk::Orientation::Horizontal, 0);
        pcatk.vbox.pack_start(&hbox, false, false, 0);

        let stack = gtk::StackBuilder::new().build();
        stack.add_titled(&pcatk.palette.pwo(), "palette", "Palette");
        stack.add_titled(&pcatk.factory.pwo(), "factory", "Paint Editor/Factory");
        pcatk.vbox.pack_start(&stack, true, true, 0);
        let stack_switcher = gtk::StackSwitcherBuilder::new()
            .tooltip_text("Select mode.")
            .stack(&stack)
            .build();
        hbox.pack_start(&stack_switcher, true, true, 0);

        let seperator = gtk::SeparatorBuilder::new().build();
        hbox.pack_start(&seperator, false, false, 0);

        let button = gtk::Button::with_label("PDF Viewer");
        hbox.pack_start(&button, false, false, 0);
        let pcatk_c = Rc::clone(&pcatk);
        button.connect_clicked(move |_| pcatk_c.launch_pdf_viewer());

        let button = gtk::Button::with_label("Image Viewer");
        hbox.pack_start(&button, false, false, 0);
        button.connect_clicked(move |_| launch_image_viewer());

        if sample::screen_sampling_available() {
            let btn = gtk::Button::with_label("Take Sample");
            btn.set_tooltip_text(Some("Take a sample of a portion of the screen"));
            let pcatk_c = Rc::clone(&pcatk);
            btn.connect_clicked(move |_| {
                if let Err(err) = sample::take_screen_sample() {
                    pcatk_c.report_error("Failure", &err);
                }
            });
            hbox.pack_start(&btn, false, false, 0);
        }

        pcatk.vbox.show_all();

        pcatk
    }

    pub fn ok_to_quit(&self) -> bool {
        let buttons = [
            ("Cancel", gtk::ResponseType::Cancel),
            ("Continue Discarding Changes", gtk::ResponseType::Other(1)),
        ];
        let question = if self.palette.needs_saving() {
            if self.factory.needs_saving() {
                Some("Palette and Paints Editor/Factory have unsaved changes!")
            } else {
                Some("Palette has unsaved changes!")
            }
        } else if self.factory.needs_saving() {
            Some("Paints Editor/Factory has unsaved changes!")
        } else {
            None
        };
        if let Some(question) = question {
            if self.ask_question(question, None, &buttons) == gtk::ResponseType::Cancel {
                return false;
            }
        }
        true
    }

    fn launch_pdf_viewer(&self) {
        // TODO: make pdf viewer configurable
        let viewer = "xreader";
        if let Err(err) = Command::new(viewer).spawn() {
            let msg = format!("Error running \"{}\"", viewer);
            self.report_error(&msg, &err);
        }
    }
}

fn launch_image_viewer() {
    let window = gtk::Window::new(gtk::WindowType::Toplevel);
    window.set_geometry_from_recollections("pcatk_gtk::image_viewer", (200, 200));
    window.set_destroy_with_parent(true);
    window.set_title("pcatk_gtk: Image Viewer");

    let view = PixbufViewBuilder::new().load_last_image(true).build();
    window.add(&view.pwo());
    window.show_all();

    window.present();
}
