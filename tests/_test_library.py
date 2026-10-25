"""Unified-library identities, filtering, actions and offline catalog recovery."""

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from lutris import settings
from lutris.database import games, schema, sql
from lutris.gui.lutriswindow import LutrisWindow
from lutris.gui.views.base import GameView
from lutris.gui.views.store_item import StoreItem
from lutris.library import get_library_services, merge_library_games, split_library_id
from lutris.search import GameSearch
from lutris.services.base import BaseService, LutrisCoverartMedium


class LibraryTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.db_patch = patch.object(settings, "DB_PATH", self.directory.name + "/pga.db")
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        schema.syncdb()
        self.remote = [
            {"id": 1, "service": "gog", "appid": "42", "slug": "cloud-game", "name": "Cloud Game"},
            {"id": 2, "service": "egs", "appid": "42", "slug": "other-game", "name": "Other Game"},
        ]

    def get_library(self, **filters):
        window = SimpleNamespace(
            filters={"category": "all", **filters},
            service=None,
            dynamic_categories_game_factories={},
            get_game_search=lambda: GameSearch(filters.get("text", "")),
            apply_view_sort=lambda entries: entries,
        )
        window.get_sql_filters = lambda: LutrisWindow.get_sql_filters(window)
        window.filter_games = lambda entries, searches=None: LutrisWindow.filter_games(window, entries, searches)
        with patch("lutris.gui.lutriswindow.get_owned_service_games", return_value=self.remote):
            return LutrisWindow.get_games_from_filters(window)

    def test_uninstalled_accounts_are_visible_without_importing(self):
        local_id = games.add_game(name="Local Game", runner="linux", installed=1)
        result = self.get_library()
        self.assertEqual({entry["name"] for entry in result}, {"Local Game", "Cloud Game", "Other Game"})
        self.assertEqual(len(games.get_games()), 1)
        self.assertEqual(result[0]["id"], local_id)
        self.assertEqual(split_library_id(result[1]["id"]), ("gog", "42"))
        self.assertEqual(split_library_id(result[2]["id"]), ("egs", "42"))

    def test_linked_local_game_is_not_duplicated(self):
        games.add_game(name="Installed GOG", runner="wine", installed=1, service="gog", service_id="42")
        result = self.get_library()
        self.assertEqual({entry["name"] for entry in result}, {"Installed GOG", "Other Game"})

    def test_hidden_linked_game_cannot_reappear_from_service(self):
        from lutris.database import categories

        game_id = games.add_game(name="Hidden GOG", runner="wine", service="gog", service_id="42")
        category_id = categories.add_category(".hidden")
        categories.add_game_to_category(game_id, category_id)
        self.assertEqual([entry["name"] for entry in self.get_library()], ["Other Game"])

    def test_install_filter_and_search_apply_to_cloud_entries(self):
        games.add_game(name="Local Game", runner="linux", installed=1)
        self.assertEqual([entry["name"] for entry in self.get_library(installed=True)], ["Local Game"])
        self.assertEqual([entry["name"] for entry in self.get_library(text="Cloud")], ["Cloud Game"])
        self.assertEqual(
            [entry["name"] for entry in self.get_library(text="source:gog installed:false")], ["Cloud Game"]
        )

    def test_service_row_id_does_not_match_unrelated_hidden_local_id(self):
        from lutris.database import categories

        game_id = games.add_game(name="Hidden Local", runner="linux")
        category_id = categories.add_category(".hidden")
        categories.add_game_to_category(game_id, category_id)
        self.assertEqual(len(self.get_library()), 2)

    def test_merge_does_not_mutate_rows_and_ids_remain_unique(self):
        result = merge_library_games([], self.remote + self.remote)
        self.assertEqual(len(result), 2)
        self.assertNotIn("_library_id", self.remote[0])
        media = LutrisCoverartMedium()
        self.assertEqual(StoreItem(result[0], None, media).id, "service:gog:42")
        self.assertIsNone(split_library_id("42"))
        self.assertEqual(split_library_id("service:egs:namespace:42"), ("egs", "namespace:42"))

    def test_cloud_actions_resolve_the_correct_service_and_local_install(self):
        for entry in self.remote:
            sql.db_insert(settings.DB_PATH, "service_games", entry)
        view = GameView()
        resolved = view._get_games_by_ids(["service:gog:42", "service:egs:42"])
        self.assertEqual([(game.service, game.appid) for game in resolved], [("gog", "42"), ("egs", "42")])
        game_id = games.add_game(name="Installed", runner="wine", installed=1, service="gog", service_id="42")
        self.assertEqual(view._get_games_by_ids(["service:gog:42"])[0].id, str(game_id))

    def test_failed_reload_restores_previous_catalog(self):
        sql.db_insert(settings.DB_PATH, "service_games", self.remote[0])

        class BrokenService(BaseService):
            id = "gog"
            name = "GOG"

            def load(self):
                raise RuntimeError("Network offline")

        errors = []

        def synchronous_call(function, callback):
            try:
                callback(function(), None)
            except RuntimeError as error:
                callback(None, error)

        with patch("lutris.services.base.AsyncCall", side_effect=synchronous_call):
            BrokenService().start_reload(errors.append)
        self.assertIsInstance(errors[0], RuntimeError)
        self.assertEqual(sql.filtered_query(settings.DB_PATH, "service_games")[0]["appid"], "42")

    def test_connected_accounts_do_not_require_enabled_sidebar_rows(self):
        connected = SimpleNamespace(id="gog", online=True, is_authenticated=lambda: True)
        disconnected = SimpleNamespace(id="egs", online=True, is_authenticated=lambda: False)
        catalog = SimpleNamespace(id="flathub", online=False, local=False)
        with (
            patch(
                "lutris.library.services.SERVICES",
                {"gog": lambda: connected, "egs": lambda: disconnected, "flathub": lambda: catalog},
            ),
            patch("lutris.library.services.get_enabled_services", return_value={}),
            patch("lutris.library.settings.read_bool_setting", return_value=True),
        ):
            self.assertEqual(list(get_library_services()), [connected])

    def test_double_click_routes_remote_game_to_service_installer(self):
        provider = Mock(id="gog")
        provider.install_by_id.return_value = None
        with patch.dict("lutris.gui.lutriswindow.services.SERVICES", {"gog": lambda: provider}):
            LutrisWindow.on_game_activated(SimpleNamespace(service=None), None, "service:gog:42")
        provider.install_by_id.assert_called_once_with("42")
