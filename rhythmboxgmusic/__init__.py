from gi.repository import GdkPixbuf, Gio, GLib, GnomeKeyring, Gtk, GObject, Peas
from gi.repository import RB

from concurrent import futures
from gmusicapi import Mobileclient as Mapi
from gettext import lgettext as _
import gettext
import json

gettext.bindtextdomain("rhythmbox-gmusic", "/usr/share/locale")
gettext.textdomain("rhythmbox-gmusic")

mapi = Mapi(False)

executor = futures.ThreadPoolExecutor(max_workers=1)

APP_KEY = 'rhythmbox-gmusic'
result, KEYRING = GnomeKeyring.get_default_keyring_sync()

GnomeKeyring.unlock_sync(KEYRING, None)


def get_playlist_songs(id):
    try:
        #Mobile API can't get a single playlist's contents
        playlists = mapi.get_all_user_playlist_contents()
        for playlist in playlists:
            if playlist['id'] == id:
                return playlist['tracks']
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
        self.source = GObject.new(
            GooglePlayLibrary, shell=shell,
            name="Google Play Music",
            query_model=model,
            plugin=self,
            icon=Gio.ThemedIcon.new("media-playback-start-symbolic"),
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
        return mapi.get_stream_url(id)

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


class GooglePlayBaseSource(RB.Source):
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
        if self.mapi_login():
            self.init_authenticated()
        else:
            infobar = Gtk.InfoBar()
            self.top_box.pack_start(infobar, True, True, 0)
            infobar.set_message_type(Gtk.MessageType.INFO)
            auth_btn = infobar.add_button(_("Click here to login"), 1)
            auth_btn.connect('clicked', self.auth)
            label = Gtk.Label(_("This plugin requires you to authenticate to Google Play"))
            infobar.get_content_area().add(label)
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
            RB.RhythmDBPropType.COMMENT, text.lower(),
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

    def mapi_login(self):
        if mapi.is_authenticated():
            return True
        login, password = get_credentials()
        return mapi.login(login, password, Mapi.FROM_MAC_ADDRESS)

    def auth(self, widget):
        dialog = AuthDialog()
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            login = dialog.login_input.get_text()
            password = dialog.password_input.get_text()
            set_credentials(login, password)
            if self.mapi_login():
                self.init_authenticated()
        dialog.destroy()

    def do_impl_get_entry_view(self):
        return self.songs_view

    def create_entry_from_track_data(self, src_id, id_key, track):
        shell = self.props.shell
        db = shell.props.db
        entry = RB.RhythmDBEntry.new(
            db, gentry, src_id + '/' + track[id_key],
            )
        full_title = []
        if 'title' in track:
            db.entry_set(
                entry, RB.RhythmDBPropType.TITLE,
                track['title']
                )
            full_title.append(track['title'])
        if 'durationMillis' in track:
            db.entry_set(
                entry, RB.RhythmDBPropType.DURATION,
                int(track['durationMillis']) / 1000,
                )
        if 'album' in track:
            db.entry_set(
                entry, RB.RhythmDBPropType.ALBUM,
                track['album'],
                )
            full_title.append(track['album'])
        if 'artist' in track:
            db.entry_set(
                entry, RB.RhythmDBPropType.ARTIST,
                track['artist'],
                )
            full_title.append(track['artist'])
        if 'trackNumber' in track:
            db.entry_set(
                entry, RB.RhythmDBPropType.TRACK_NUMBER,
                int(track['trackNumber']),
                )
        if 'albumArtRef' in track:
            db.entry_set(
                entry, RB.RhythmDBPropType.MB_ALBUMID,
                track['albumArtRef'][0]['url'],
                )
        # rhytmbox OR don't work for custom filters
        db.entry_set(
            entry, RB.RhythmDBPropType.COMMENT,
            ' - '.join(full_title).lower(),
            )
        # rhythmbox segfoalt when new db created from python
        db.entry_set(
            entry, RB.RhythmDBPropType.GENRE,
            'google-play-music',
            )
        return entry

    def load_songs():
        raise NotImplementedError


class GooglePlayLibrary(GooglePlayBaseSource):
    def load_songs(self):
        shell = self.props.shell
        self.trackdata = mapi.get_all_songs()
        for song in self.trackdata:
            try:
                entry = self.create_entry_from_track_data(
                    getattr(self, 'id', 'gmusic'), 'id', song)
                self.props.base_query_model.add_entry(entry, -1)
            except TypeError:  # Already in db
                pass
        shell.props.db.commit()
        self.load_playlists()

    def load_playlists(self):
        shell = self.props.shell
        db = shell.props.db
        self.playlists = mapi.get_all_playlists()
        for playlist in self.playlists:
            model = RB.RhythmDBQueryModel.new_empty(db)
            pl = GObject.new(
                GooglePlayPlaylist, shell=shell,
                name=playlist['name'],
                query_model=model,
                icon=Gio.ThemedIcon.new("playlist")
                )
            pl.setup(playlist['id'], self.trackdata)
            shell.append_display_page(pl, self)


class GooglePlayPlaylist(GooglePlayBaseSource):
    def setup(self, id, trackdata):
        self.id = id
        self.trackdata = trackdata
        GooglePlayBaseSource.setup(self)

    def load_songs(self):
        future = executor.submit(get_playlist_songs, self.id)
        future.add_done_callback(self.init_songs)

    def on_search(self, entry, text):
        db = self.props.shell.props.db
        query_model = RB.RhythmDBQueryModel.new_empty(db)
        query = GLib.PtrArray()
        db.query_append_params(
            query, RB.RhythmDBQueryType.FUZZY_MATCH,
            RB.RhythmDBPropType.COMMENT, text.lower(),
        )
        db.query_append_params(
            query, RB.RhythmDBQueryType.EQUALS,
            RB.RhythmDBPropType.GENRE, 'google-play-music-playlist',
        )
        db.do_full_query_parsed(query_model, query)
        self.browser.set_model(query_model, False)
        self.update_view()

    def init_songs(self, future):
        shell = self.props.shell
        db = shell.props.db
        for track in future.result():
            match = next(
                (td for td in self.trackdata if td['id'] == track['trackId']),
                None
                )
            if match:
                entry = self.create_entry_from_track_data(
                    getattr(self, 'id', '0'), 'id', match
                    )
                db.entry_set(
                    entry, RB.RhythmDBPropType.GENRE,
                    'google-play-music-playlist',
                    )
                self.props.base_query_model.add_entry(entry, -1)
        db.commit()
        delattr(self, 'trackdata') #Memory concerns


GObject.type_register(GooglePlayLibrary)
