"""Mopidy HTTP client.

Fully implemented using Mopidy websocket.

"""

import logging
import random
from typing import Any, cast, Dict, List, Optional

from .ws import MopidyWSConnection

LOGGER = logging.getLogger(__name__)


class MopidyHTTPClient:
    def __init__(
        self,
        *,
        ws: MopidyWSConnection,
        favorite_playlist_uri: Optional[str],
    ):
        self._ws = ws
        self._favorite_playlist_uri = favorite_playlist_uri

    def set_favorite_playlist_uri(self, favorite_playlist_uri: Optional[str]) -> None:
        self._favorite_playlist_uri = favorite_playlist_uri

    async def get_state(self) -> Any:
        state = await self._ws.send_command("core.playback.get_state")
        return state

    async def pause(self) -> None:
        await self._ws.send_command("core.playback.pause")

    async def resume(self) -> None:
        await self._ws.send_command("core.playback.resume")

    async def play(self) -> None:
        await self._ws.send_command("core.playback.play")

    async def seek(self, time_position: int) -> Any:
        params = {"time_position": time_position}
        successful = await self._ws.send_command("core.playback.seek", params=params)
        return successful

    async def previous(self) -> None:
        await self._ws.send_command("core.playback.previous")

    async def next(self) -> None:
        await self._ws.send_command("core.playback.next")

    async def get_time_position(self) -> None:
        position = await self._ws.send_command("core.playback.get_time_position")
        return position

    async def get_eot_tlid(self) -> Any:
        eot_tlid = await self._ws.send_command("core.tracklist.get_eot_tlid")
        return eot_tlid

    async def browse_libraries(self) -> List[Dict[str, Any]]:
        libraries = cast(
            List[Dict[str, Any]],
            await self._ws.send_command("core.library.browse", params={"uri": None}),
        )
        LOGGER.debug(f"Found {len(libraries)} libraries")
        return libraries

    async def browse_albums(self) -> List[Any]:
        libraries = await self.browse_libraries()
        albums = []
        for library in libraries:
            name = library.get("name")
            uri = library.get("uri")
            if not name or not uri:
                LOGGER.debug(f"Skipping unexpected library {library!r}")
                continue

            library_albums = await self._ws.send_command(
                "core.library.browse", params={"uri": f"{uri}?type=album"}
            )
            if library_albums is None:
                LOGGER.warning(f"No album found for library {name!r}")
            else:
                LOGGER.debug(f"Found {len(library_albums)} albums in library {name!r}")
                albums += library_albums

        return albums

    async def play_album(self, uri: str = None) -> None:
        """Play album with given URI.

        When ``uri`` is ``None``, then a random album is choosen.

        Args:
            uri: Optional URI of the album to play.

        """
        if uri is None:
            albums = await self.browse_albums()

            if not len(albums):
                return

            album = random.choice(albums)
            LOGGER.debug(f"Will play {album['name']}")
            uri = album["uri"]

        await self._ws.send_command("core.tracklist.clear")
        await self._ws.send_command("core.tracklist.add", params={"uris": [uri]})
        await self._ws.send_command("core.playback.play")

    async def play_favorite_playlist(self) -> None:
        if not self._favorite_playlist_uri:
            LOGGER.debug("Favorite playlist URI not set")
            return

        refs = await self._ws.send_command(
            "core.playlists.get_items", params={"uri": self._favorite_playlist_uri}
        )
        if not refs:
            return

        await self._ws.send_command("core.tracklist.clear")
        uris = [ref["uri"] for ref in refs]
        tltracks = await self._ws.send_command(
            "core.tracklist.add", params={"uris": uris, "at_position": 0}
        )
        tltrack = tltracks[0]
        await self._ws.send_command(
            "core.playback.play", params={"tlid": tltrack["tlid"]}
        )

    async def get_mute(self) -> Any:
        mute = await self._ws.send_command("core.mixer.get_mute")
        return mute

    async def set_mute(self, mute: bool) -> None:
        params = {"mute": mute}
        await self._ws.send_command("core.mixer.set_mute", params=params)

    async def get_volume(self) -> Any:
        volume = await self._ws.send_command("core.mixer.get_volume")
        return volume

    async def set_volume(self, volume: int) -> None:
        params = {"volume": volume}
        await self._ws.send_command("core.mixer.set_volume", params=params)

    async def list_playlists(self) -> List[Dict[str, Any]]:
        list = await self._ws.send_command("core.playlists.as_list")
        return list

    async def get_current_tl_track(self) -> Any:
        track = await self._ws.send_command("core.playback.get_current_tl_track")
        return track

    async def get_images(self, uris: List[str]) -> Dict[str, List[Any]]:
        params = {"uris": uris}
        images = await self._ws.send_command("core.library.get_images", params=params)
        return images
