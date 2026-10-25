"""Combine owned service games with the local library without importing them.

Service IDs are namespaced: the same appid on two stores is two licenses,
whereas a local game linked to that license appears only once.
"""

from lutris import services, settings
from lutris.database.services import ServiceGameCollection
from lutris.util.log import logger


def get_library_services():
    """Include authenticated accounts, even if their sidebar row is disabled.

    Non-account catalogs (notably Flathub) are deliberately not owned libraries.
    Local sources are included only when explicitly enabled.
    """
    enabled = services.get_enabled_services()
    for service_id, service_class in services.SERVICES.items():
        if not settings.read_bool_setting(service_id + "_in_games_view", True, section="services"):
            continue
        try:
            service = service_class()
            if service.online:
                if service.is_authenticated():
                    yield service
            elif service_id in enabled and (service.local or service_id in ("steam", "steamwindows")):
                yield service
        except Exception:
            logger.exception("Could not inspect library account %s", service_id)


def merge_library_games(local_games, service_games):
    """Return new dictionaries; never mutate DB rows or conflate stores by title."""
    result = [dict(game) for game in local_games]
    linked = {
        (game.get("service"), str(game.get("service_id")))
        for game in local_games
        if game.get("service") and game.get("service_id") is not None
    }
    for game in service_games:
        identity = (game["service"], str(game["appid"]))
        if identity in linked:
            continue
        linked.add(identity)
        library_id = f"service:{identity[0]}:{identity[1]}"
        result.append(dict(game, id=library_id, _library_id=library_id, installed=0, runner=""))
    return result


def get_owned_service_games():
    games = []
    for service in get_library_services():
        games.extend(ServiceGameCollection.get_for_service(service.id))
    return games


def split_library_id(game_id):
    """Return (service, appid) for a virtual library entry, otherwise None."""
    if str(game_id).startswith("service:"):
        _, service_id, appid = str(game_id).split(":", 2)
        return service_id, appid
    return None
