from gi.repository import GObject, Peas, Gtk, GConf, RB, GLib, GnomeKeyring
from concurrent import futures
from gmusicapi import Webclient as Api
from gmusicapi import Mobileclient as Mapi
from gettext import lgettext as _
import gettext
import rb
import json


gettext.bindtextdomain("rhythmbox-gmusic", "/usr/share/locale")
gettext.textdomain("rhythmbox-gmusic")

try:
    # for older version
    api = Api(debug_logging=False,verify_ssl=False)
    mapi = Mapi(debug_logging=False,verify_ssl=False)
except TypeError:
    # for newer version
    api = Api()
    mapi = Mapi()

executor = futures.ThreadPoolExecutor(max_workers=1)
settings = GConf.Client.get_default()

APP_KEY = 'rhythmbox-gmusic'
result, KEYRING = GnomeKeyring.get_default_keyring_sync()

GnomeKeyring.unlock_sync(KEYRING, None)


def get_songs():
    try:
        return mapi.get_all_songs()
    except KeyError:
        return []


def get_playlist_songs(id):
    try:
        return api.get_playlist_songs(id)
    except KeyError:
        return []


def get_credentials():
    attrs = GnomeKeyring.Attribute.list_new()
    GnomeKeyring.Attribute.list_append_string(attrs, 'id', APP_KEY)
    result, value = GnomeKeyring.find_items_sync(GnomeKeyring.ItemType.GENERIC_SECRET, attrs)
    if result == GnomeKeyring.Result.OK:
        return json.loads(value[0].secret)
    else:
        return '', ''


def set_credentials(username, password):
    if KEYRING is not None:
        GnomeKeyring.create_sync(KEYRING, None)
    attrs = GnomeKeyring.Attribute.list_new()
    GnomeKeyring.Attribute.list_append_string(attrs, 'id', APP_KEY)
    GnomeKeyring.item_create_sync(
        KEYRING, GnomeKeyring.ItemType.GENERIC_SECRET, APP_KEY,
        attrs, json.dumps([username, password]), True,
    )


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
    def __init__(self):
        RB.RhythmDBEntryType.__init__(self)

    def do_get_playback_uri(self, entry):
        id = entry.dup_string(RB.RhythmDBPropType.LOCATION).split('/')[1]
        return api.get_stream_urls(id)[0]

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
        self.top_box = Gtk.VBox()
        if self.api_login() and self.mapi_login():
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
            self.top_box.pack_start(hbox, False, False, 0)
            self.auth_box = hbox

        self.browser = RB.LibraryBrowser.new(shell.props.db, gentry)
        self.browser.set_model(self.props.base_query_model, False)
        self.browser.connect("notify::output-model", self.update_view)
        self.browser.set_size_request(-1, 200)

        self.search_widget = RB.SearchEntry.new(False)
        self.search_widget.connect("search", self.on_search)

        search_box = Gtk.Alignment.new(1, 0, 0, 1)
        search_box.add(self.search_widget)

        self.top_box.pack_start(search_box, False, False, 5)
        self.top_box.pack_start(self.browser, True, True, 0)

        self.update_view()

        self.vbox.add1(self.top_box)
        self.vbox.add2(self.songs_view)
        self.pack_start(self.vbox, True, True, 0)
        self.show_all()

    def on_search(self, entry, text):
        db = self.props.shell.props.db
        query_model = RB.RhythmDBQueryModel.new_empty(db)
        query = GLib.PtrArray()
        db.query_append_params(
            query, RB.RhythmDBQueryType.FUZZY_MATCH,
            RB.RhythmDBPropType.COMMENT, text.lower().encode('utf8'),
        )
        db.query_append_params(
            query, RB.RhythmDBQueryType.EQUALS,
            RB.RhythmDBPropType.GENRE, 'google-play-music',  # shit!
        )
        db.do_full_query_parsed(query_model, query)
        self.browser.set_model(query_model, False)
        self.update_view()

    def update_view(self, *args):
        self.songs_view.set_model(self.browser.props.output_model)
        self.props.query_model = self.browser.props.output_model

    def init_authenticated(self):
        if hasattr(self, 'auth_box'):
            self.top_box.remove(self.auth_box)
        self.load_songs()

    def init_songs(self, songs):
        shell = self.props.shell
        for song in songs.result():
            try:
                entry = RB.RhythmDBEntry.new(
                    shell.props.db, gentry,
                    getattr(self, 'id', '0') + '/' + song['id'],
                )
                full_title = []
                if 'title' in song:
                    shell.props.db.entry_set(
                        entry, RB.RhythmDBPropType.TITLE,
                        song['title'].encode('utf8'),
                    )
                    full_title.append(song['title'])
                if 'durationMillis' in song:
                    shell.props.db.entry_set(
                        entry, RB.RhythmDBPropType.DURATION,
                        int(song['durationMillis']) / 1000,
                    )
                if 'artist' in song:
                    shell.props.db.entry_set(
                        entry, RB.RhythmDBPropType.ARTIST,
                        song['artist'].encode('utf8'),
                    )
                    full_title.append(song['artist'])
                if 'album' in song:
                    shell.props.db.entry_set(
                        entry, RB.RhythmDBPropType.ALBUM,
                        song['album'].encode('utf8'),
                    )
                    full_title.append(song['album'])
                if 'trackNumber' in song:
                    shell.props.db.entry_set(
                        entry, RB.RhythmDBPropType.TRACK_NUMBER,
                        int(song['trackNumber']),
                    )
                # rhytmbox OR don't work for custom filters
                shell.props.db.entry_set(
                    entry, RB.RhythmDBPropType.COMMENT,
                    ' - '.join(full_title).lower().encode('utf8'),
                )
                # rhythmbox segfoalt when new db created from python
                shell.props.db.entry_set(
                    entry, RB.RhythmDBPropType.GENRE,
                    'google-play-music',
                )
                self.props.base_query_model.add_entry(entry, -1)
            except TypeError:  # Already in db
                pass
        shell.props.db.commit()

    def api_login(self):
        if api.is_authenticated():
            return True
        login, password = get_credentials()
        return api.login(login, password)

    def mapi_login(self):
        if mapi.is_authenticated():
            return True
        login, password = get_credentials()
        return mapi.login(login, password)

    def auth(self, widget):
        dialog = AuthDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            login = dialog.login_input.get_text()
            password = dialog.password_input.get_text()
            set_credentials(login, password)
            if self.api_login() and self.mapi_login():
                self.init_authenticated()
        dialog.destroy()

    def do_impl_get_entry_view(self):
        return self.songs_view

    def load_songs(self):
        raise NotImplementedError


class GPlaylist(GBaseSource):
    def setup(self, id):
        self.id = id
        GBaseSource.setup(self)

    def load_songs(self):
        future = executor.submit(get_playlist_songs, self.id)
        future.add_done_callback(self.init_songs)


class GPlaySource(GBaseSource):
    def init_authenticated(self):
        GBaseSource.init_authenticated(self)
        # Fix later - let's get normal songs working first.
        # self.playlists = []
        # playlists = mapi.get_all_playlists()
        # #user = playlists.get('user', {})
        # shell = self.props.shell
        # db = shell.props.db
        # for playlist in playlists:
        #     model = RB.RhythmDBQueryModel.new_empty(db)
        #     pl = GObject.new(
        #         GPlaylist, shell=shell, name=playlist['name'].encode('utf8'),
        #         query_model=model,
        #         )
        #     pl.setup(playlist['id'])
        #     shell.append_display_page(pl, self)

    def load_songs(self):
        future = executor.submit(get_songs)
        future.add_done_callback(self.init_songs)


GObject.type_register(GPlaySource)
