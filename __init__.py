# -*- coding: utf-8 -*-
#from .plugin import blueprint, menu, plugin_load, plugin_unload, plugin_info
from framework import SystemModelSetting
try:
    import xmltodict
except:
    from framework import app
    import os
    try: os.system(f"{app.config['config']['pip']} install xmltodict")
    except: pass


from .plugin import P
blueprint = P.blueprint
menu = P.menu
plugin_load = P.plugin_load
plugin_unload = P.plugin_unload
plugin_info = P.plugin_info

from .server_util import MetadataServerUtil
from .site_util import SiteUtil
from .site_daum import SiteDaumTv
from .site_daum_movie import SiteDaumMovie
from .site_tmdb import SiteTmdbTv, SiteTmdbMovie, SiteTmdbFtv
from .site_tving import SiteTvingTv, SiteTvingMovie
from .site_wavve import SiteWavveTv, SiteWavveMovie
from .site_naver import SiteNaverMovie
from .site_naver_book import SiteNaverBook
from .site_watcha import SiteWatchaMovie, SiteWatchaTv
from .site_tvdb import SiteTvdbTv

from .site_dmm import SiteDmm
from .site_javbus import SiteJavbus
from .site_jav321 import SiteJav321
from .site_mgstage import SiteMgstageDvd, SiteMgstageAma
from .site_vibe import SiteVibe