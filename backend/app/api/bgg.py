import asyncio
import time
from xml.etree import ElementTree

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/bgg", tags=["bgg"])

_game_cache: dict[int, tuple[float, dict]] = {}
_CACHE_TTL = 3600


def _int(s: str | None) -> int | None:
    try:
        v = int(s or 0)
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _float(s: str | None) -> float | None:
    try:
        v = float(s or 0)
        return round(v, 2) if v > 0 else None
    except (ValueError, TypeError):
        return None


def _attr(el, tag: str) -> str | None:
    child = el.find(tag)
    return child.get("value") if child is not None else None


def _parse_game(item) -> dict:
    name = next(
        (n.get("value") for n in item.findall("name") if n.get("type") == "primary"),
        None,
    )

    ratings = item.find(".//ratings")
    average = weight = users_rated = None
    if ratings is not None:
        average = _float(getattr(ratings.find("average"), "attrib", {}).get("value"))
        weight = _float(getattr(ratings.find("averageweight"), "attrib", {}).get("value"))
        users_rated = _int(getattr(ratings.find("usersrated"), "attrib", {}).get("value"))

    categories = [
        lnk.get("value")
        for lnk in item.findall("link")
        if lnk.get("type") == "boardgamecategory"
    ][:5]
    mechanics = [
        lnk.get("value")
        for lnk in item.findall("link")
        if lnk.get("type") == "boardgamemechanic"
    ][:5]

    return {
        "bgg_id": int(item.get("id")),
        "title": name,
        "thumbnail": (item.findtext("thumbnail") or "").strip() or None,
        "image": (item.findtext("image") or "").strip() or None,
        "year_published": _int(_attr(item, "yearpublished")),
        "min_players": _int(_attr(item, "minplayers")),
        "max_players": _int(_attr(item, "maxplayers")),
        "min_playtime": _int(_attr(item, "minplaytime")),
        "max_playtime": _int(_attr(item, "maxplaytime")),
        "min_age": _int(_attr(item, "minage")),
        "average_rating": average,
        "complexity": weight,
        "users_rated": users_rated,
        "categories": categories,
        "mechanics": mechanics,
    }


async def _fetch_xml(url: str) -> str:
    async with httpx.AsyncClient(timeout=15) as client:
        for _ in range(3):
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.text
            if resp.status_code == 202:
                await asyncio.sleep(2)
                continue
            raise HTTPException(status_code=502, detail="BGG API error")
    raise HTTPException(status_code=504, detail="BGG API timed out")


@router.get("/games")
async def get_bgg_games(ids: str):
    try:
        id_list = [int(i.strip()) for i in ids.split(",") if i.strip()][:50]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid IDs")
    if not id_list:
        raise HTTPException(status_code=400, detail="No IDs provided")

    now = time.time()
    result: dict[str, dict] = {}
    missing: list[int] = []

    for gid in id_list:
        if gid in _game_cache and now - _game_cache[gid][0] < _CACHE_TTL:
            result[str(gid)] = _game_cache[gid][1]
        else:
            missing.append(gid)

    if missing:
        url = f"https://boardgamegeek.com/xmlapi2/thing?id={','.join(str(i) for i in missing)}&stats=1"
        xml = await _fetch_xml(url)
        root = ElementTree.fromstring(xml)
        for item in root.findall("item"):
            data = _parse_game(item)
            gid = data["bgg_id"]
            _game_cache[gid] = (now, data)
            result[str(gid)] = data

    return result


@router.get("/search")
async def search_bgg(q: str):
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Query too short")
    url = f"https://boardgamegeek.com/xmlapi2/search?query={q}&type=boardgame"
    xml = await _fetch_xml(url)
    root = ElementTree.fromstring(xml)
    results = []
    for item in root.findall("item"):
        name_el = next((n for n in item.findall("name") if n.get("type") == "primary"), None)
        if not name_el:
            continue
        year_el = item.find("yearpublished")
        results.append({
            "bgg_id": int(item.get("id")),
            "title": name_el.get("value"),
            "year_published": _int(year_el.get("value") if year_el is not None else None),
        })
    return results[:20]
