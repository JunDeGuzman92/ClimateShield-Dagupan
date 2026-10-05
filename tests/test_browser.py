"""Real-browser check (headless Chrome): the storm time-lapse loads tiles, plays, and the stats strip
never covers the map. Skipped automatically if Chrome isn't installed."""
import re
import subprocess
from pathlib import Path

import pytest

from conftest import ARTIFACTS

CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
pytestmark = pytest.mark.skipif(not CHROME.exists(), reason="Chrome not installed")


def test_timelapse_plays_and_layout_is_clear(layers):
    import cinema
    import mapfilm
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out = ARTIFACTS / "storm_test.html"
    fr = mapfilm.storm_frames(layers, cinema.FLOOD_STORIES["unprepared"])
    html = mapfilm.storm_map(layers, fr, "Unprepared city", "sub", height=500).get_root().render()
    probe = """<script>setTimeout(function(){
      var m=document.querySelector('.folium-map').getBoundingClientRect();
      var h=document.querySelector('.cs-strip').getBoundingClientRect();
      document.body.setAttribute('data-geo',[m.top,m.bottom,h.top,h.bottom].map(Math.round).join(','));},3000);
      </script></body>"""
    out.write_text(html.replace("</body>", probe), encoding="utf-8")
    dom = subprocess.run([str(CHROME), "--headless=new", "--disable-gpu", "--no-sandbox", "--window-size=1400,900",
                          "--virtual-time-budget=6000", "--dump-dom", out.as_uri()],
                         capture_output=True, text=True, encoding="utf-8", timeout=180).stdout
    assert 'data-cs-ready="1"' in dom, "player script never initialised"
    mt, mb, ht, hb = map(int, re.search(r'data-geo="([^"]+)"', dom).group(1).split(","))
    assert mb - mt == 500, "map lost its height"
    assert ht >= mb, "stats strip overlaps the map"
    assert hb <= 500 + 186, "strip taller than the space the app reserves"
    hour = re.search(r'id="hh_map_[0-9a-f]+"[^>]*>([^<]*)<', dom).group(1)
    assert not hour.startswith("0 /"), f"time-lapse did not advance (shows {hour})"
