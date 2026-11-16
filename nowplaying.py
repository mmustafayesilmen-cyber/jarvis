"""Şu an çalan medya bilgisi (Windows medya denetimi / SMTC): tarayıcıdaki YouTube Music, Spotify vb. Ses okunmaz; yalnızca başlık, sanatçı,
çalma durumu ve konum alınır. Jarvis'in kendi oynatıcısı (study_music) için ayrıca kendi bilgisi kullanılır."""
import asyncio


async def _get():
    from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as M
    mgr = await M.request_async()
    ses = mgr.get_current_session()
    if ses is None:
        return None
    props = await ses.try_get_media_properties_async()
    pb = ses.get_playback_info()
    tl = ses.get_timeline_properties()
    pos = tl.position.total_seconds() if tl and tl.position else 0.0
    end = tl.end_time.total_seconds() if tl and tl.end_time else 0.0
    playing = int(pb.playback_status) == 4
    # Tarayıcı konumu yalnızca ara sıra günceller: son güncellemeden bu yana geçen süreyi ekle, yoksa konum hep eski kalır
    try:
        if playing and tl and tl.last_updated_time:
            import datetime
            lu = tl.last_updated_time
            now = datetime.datetime.now(lu.tzinfo) if lu.tzinfo else datetime.datetime.now()
            gap = (now - lu).total_seconds()
            if 0 <= gap < 3600:
                pos += gap * (pb.playback_rate or 1.0)
    except Exception:
        pass
    if end > 0:
        pos = min(pos, end)
    # 4 = Playing
    return {"title": props.title or "", "artist": props.artist or "", "playing": int(pb.playback_status) == 4,
            "pos": pos, "dur": end, "app": ses.source_app_user_model_id or ""}


def current():
    """{'title','artist','playing','pos','dur','app'} ya da None."""
    try:
        return asyncio.run(_get())
    except Exception as e:
        print("nowplaying hatası:", e, flush=True)
        return None
