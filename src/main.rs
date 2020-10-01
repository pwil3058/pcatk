use pw_gix::{
    gio::{self, ApplicationExt, prelude::ApplicationExtManual},
    gtk::{self, prelude::*},
    gdk_pixbufx::iview::*,
    gtkx::{dialog::dialog_user::DialogUser, window::*},
    recollections, sample, wrapper::*
};

use epaint::art_paint::*;

use pcatk_rs::config;
use pcatk_rs::icon;

fn launch_image_viewer() {
    let window = gtk::Window::new(gtk::WindowType::Toplevel);
    window.set_geometry_from_recollections("image_viewer", (200, 200));
    window.set_destroy_with_parent(true);
    window.set_title("pcatk: Image Viewer");

    let iview = PixbufView::create();
    window.add(&iview.pwo());
    window.show_all();

    iview.reload_last_image();

    window.present();
}

fn activate(app: &gtk::Application) {
    let window = gtk::ApplicationWindow::new(app);
    let app_icon = icon::pcatkrs_pixbuf();
    window.set_title("Artists' Colour Mixing TK");
    window.set_icon(Some(&app_icon));
    window.set_geometry_from_recollections("main_window", (200, 200));
    let stack = gtk::Stack::new();
    let data_path = config::get_paint_series_files_data_path();
    let mixer = ArtPaintMixer::create(&data_path, None);
    mixer.set_manager_icons(&app_icon);
    stack.add_titled(&mixer.pwo(), "palette", "Palette");
    let editor = BasicArtPaintEditor::create();
    stack.add_titled(
        &editor.pwo(),
        "series_paint_editor",
        "Series Paint Editor/Creator",
    );
    let stack_switcher = gtk::StackSwitcher::new();
    stack_switcher.set_stack(Some(&stack));
    let hbox = gtk::Box::new(gtk::Orientation::Horizontal, 0);
    hbox.pack_start(&gtk::Label::new(Some("Mode:")), false, false, 0);
    hbox.pack_start(&stack_switcher, false, false, 2);
    hbox.pack_start(
        &gtk::Box::new(gtk::Orientation::Horizontal, 0),
        true,
        true,
        0,
    );
    let button = gtk::Button::with_label("Image Viewer");
    hbox.pack_start(&button, false, false, 0);
    button.connect_clicked(|_| launch_image_viewer());
    if sample::screen_sampling_available() {
        let btn = gtk::Button::with_label("Take Sample");
        btn.set_tooltip_text(Some("Take a sample of a portion of the screen"));
        let window_c = window.clone();
        btn.connect_clicked(move |_| {
            if let Err(err) = sample::take_screen_sample() {
                window_c.report_error("Failure", &err);
            }
        });
        hbox.pack_start(&btn, false, false, 0);
    }
    let vbox = gtk::Box::new(gtk::Orientation::Vertical, 0);
    vbox.pack_start(&hbox, false, false, 0);
    vbox.pack_start(&stack, true, true, 0);
    window.add(&vbox);
    window.connect_delete_event(move |_, _| {
        let buttons = [
            ("Cancel", gtk::ResponseType::Cancel),
            ("Continue Discarding Changes", gtk::ResponseType::Other(1)),
        ];
        if editor.get_file_status().needs_saving() {
            if editor.ask_question(
                "The Series Paint Editor has unsaved changes!",
                None,
                &buttons,
            ) == gtk::ResponseType::Cancel
            {
                return gtk::Inhibit(true);
            }
        };
        gtk::Inhibit(false)
    });
    window.show_all();
    stack.set_visible_child(&mixer.pwo());
}

fn main() {
    recollections::init(&config::get_gui_config_dir_path().join("recollections"));
    let flags = gio::ApplicationFlags::empty();
    let app = gtk::Application::new(None, flags)
        .unwrap_or_else(|err| panic!("{:?}: line {:?}: {:?}", file!(), line!(), err));
    app.connect_activate(activate);
    app.run(&[]);
}
