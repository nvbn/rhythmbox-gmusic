from gi.repository import GObject, Peas, Gtk, GConf, RB, GLib
from gmusicapi.api import Api
from gettext import lgettext as _
import gettext
import rb
gettext.bindtextdomain("rhythmbox-gmusic", "/usr/share/locale")
gettext.textdomain("rhythmbox-gmusic")
api = Api()
settings = GConf.Client.get_default()


LOGIN_KEY = '/apps/gnome/rhythmbox/google-play-music/login'
PASSWORD_KEY = '/apps/gnome/rhythmbox/google-play-music/password'


class GooglePlayMusic(GObject.Object, Peas.Activatable):
    __gtype_name = 'GooglePlayMusicPlugin'
    object = GObject.property(type=GObject.GObject)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        shell = self.object
        db = shell.props.db
        model = RB.RhythmDBQueryModel.new_empty(db)
        theme = Gtk.IconTheme.get_default()
        what, width, height = Gtk.icon_size_lookup(Gtk.IconSize.LARGE_TOOLBAR)
        icon = rb.try_load_icon(theme, "media-playback-start", width, 0)
        self.source = GObject.new(
            GPlaySource, shell=shell,
            name="Google Music",
            query_model=model,
            plugin=self,
            pixbuf=icon,
        )
        self.source.setup()
        group = RB.DisplayPageGroup.get_by_id("library")
        shell.append_display_page(self.source, group)

    def do_deactivate(self):
        self.source.delete_thyself()
        self.source = None


class GEntry(RB.RhythmDBEntryType):
    def do_get_playback_uri(self, entry):
        id = entry.dup_string(RB.RhythmDBPropType.LOCATION).split('/')[1]
        return api.get_stream_url(id)

    def do_can_sync_metadata(self, entry):
        return True
gentry = GEntry()


class AuthDialog(Gtk.Dialog):
    def __init__(self):
        Gtk.Dialog.__init__(self,
            _('Your Google account credentials'), None, 0, (
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK,
        ))
        top_label = Gtk.Label(_('Please enter your Google account credentials'))
        login_label = Gtk.Label(_("Login:"))
        self.login_input = Gtk.Entry()
        login_box = Gtk.HBox()
        login_box.add(login_label)
        login_box.add(self.login_input)
        password_label = Gtk.Label(_("Password:"))
        self.password_input = Gtk.Entry()
        self.password_input.set_visibility(False)
        password_box = Gtk.HBox()
        password_box.add(password_label)
        password_box.add(self.password_input)
        vbox = Gtk.VBox()
        vbox.add(top_label)
        vbox.add(login_box)
        vbox.add(password_box)
        box = self.get_content_area()
        box.add(vbox)
        self.show_all()


class GBaseSource(RB.Source):
    def setup(self):
        shell = self.props.shell
        self.songs_view = RB.EntryView.new(
            db=shell.props.db,
            shell_player=shell.props.shell_player,
            is_drag_source=True,
            is_drag_dest=False,
        )
        self.songs_view.append_column(
            RB.EntryViewColumn.TRACK_NUMBER, True,
        )
        self.songs_view.append_column(
            RB.EntryViewColumn.TITLE, True,
        )
        self.songs_view.append_column(
            RB.EntryViewColumn.ARTIST, True,
        )
        self.songs_view.append_column(
            RB.EntryViewColumn.ALBUM, True,
        )
        self.songs_view.append_column(
            RB.EntryViewColumn.DURATION, True,
        )
        self.songs_view.connect('notify::sort-order',
            lambda *args, **kwargs: self.songs_view.resort_model(),
        )
        self.songs_view.connect('entry-activated',
            lambda view, entry: shell.props.shell_player.play_entry(entry, self),
        )
        self.vbox = Gtk.Paned.new(Gtk.Orientation.VERTICAL)

        if self.login():
            self.init_authenticated()
        else:
            label = Gtk.Label(
                _("This plugin requires you to authenticate to Google Play"),
            )
            auth_btn = Gtk.Button(_("Click here to login"))
            auth_btn.connect('clicked', self.auth)
            hbox = Gtk.HBox()
            hbox.add(label)
            hbox.add(auth_btn)
            hbox.set_size_request(100, 30)
            self.vbox = Gtk.VBox()
            self.vbox.pack_start(hbox, False, False, 0)
            self.auth_box = hbox
        self.browser = RB.LibraryBrowser.new(shell.props.db, gentry)
        self.browser.set_model(self.props.query_model, False)
        self.browser.connect("notify::output-model", self.update_view)
        self.songs_view.set_model(self.browser.props.output_model)
        self.vbox.add1(self.browser)
        self.vbox.add2(self.songs_view)
        self.pack_start(self.vbox, True, True, 0)
        self.show_all()

    def update_view(self, *args):
        self.songs_view.set_model(self.browser.props.output_model)

    def init_authenticated(self):
        if hasattr(self, 'auth_box'):
            self.vbox.remove(self.auth_box)
        GLib.idle_add(self.init_songs)

    def init_songs(self):
        shell = self.props.shell
        for song in self.get_songs():
            try:
                entry = RB.RhythmDBEntry.new(
                    shell.props.db, gentry,
                    getattr(self, 'id', '0') + '/' + song['id'],
                )
                shell.props.db.entry_set(
                    entry, RB.RhythmDBPropType.TITLE,
                    song['title'].encode('utf8'),
                )
                shell.props.db.entry_set(
                    entry, RB.RhythmDBPropType.DURATION,
                    int(song['durationMillis']) / 1000,
                )
                shell.props.db.entry_set(
                    entry, RB.RhythmDBPropType.ARTIST,
                    song['artist'].encode('utf8'),
                )
                shell.props.db.entry_set(
                    entry, RB.RhythmDBPropType.ALBUM,
                    song['album'].encode('utf8'),
                )
                shell.props.db.entry_set(
                    entry, RB.RhythmDBPropType.TRACK_NUMBER,
                    int(song['track']),
                )
                self.props.query_model.add_entry(entry, -1)
            except TypeError:  # Already in db
                pass
        shell.props.db.commit()
        # self.songs_view.set_model(self.props.query_model)

    def login(self):
        if api.is_authenticated():
            return True
        login = settings.get_string(LOGIN_KEY)
        password = settings.get_string(PASSWORD_KEY)
        return api.login(login, password)

    def auth(self, widget):
        dialog = AuthDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            settings.set_string(LOGIN_KEY, dialog.login_input.get_text())
            settings.set_string(PASSWORD_KEY, dialog.password_input.get_text())
            if self.login():
                self.init_authenticated()
        dialog.destroy()

    def do_impl_get_entry_view(self):
        return self.songs_view

    def get_songs(self):
        raise NotImplemented


class GPlaylist(GBaseSource):
    def setup(self, id):
        self.id = id
        GBaseSource.setup(self)

    def get_songs(self):
        return []
        return api.get_playlist_songs(self.id)


class GPlaySource(GBaseSource):
    def init_authenticated(self):
        GBaseSource.init_authenticated(self)
        self.playlists = []
        try:
            playlists = api.get_all_playlist_ids()
        except KeyError:
            playlists = {}
        user, instant = playlists.get('user', {}), playlists.get('instant', {})
        shell = self.props.shell
        db = shell.props.db
        for name, id in user.items() + instant.items():
            model = RB.RhythmDBQueryModel.new_empty(db)
            pl = GObject.new(
                GPlaylist, shell=shell, name=name.encode('utf8'),
                query_model=model,
            )
            pl.setup(id)
            shell.append_display_page(pl, self)

    def get_songs(self):
        return api.get_all_songs()


GObject.type_register(GPlaySource)
