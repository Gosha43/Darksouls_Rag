from src.scrapers.wiki_scraper import html_to_sections

SAMPLE = """
<div class="mw-parser-output">
<aside class="portable-infobox"><div class="pi-data"><h3 class="pi-data-label">Location</h3>
<div class="pi-data-value">Anor Londo</div></div></aside>
<p>Gwyn was the Lord of Sunlight.<sup class="reference">[1]</sup></p>
<h2>Lore<span class="mw-editsection">[edit]</span></h2>
<p>He linked the First Flame.</p>
<ul><li>Fathered Gwynevere</li></ul>
<table class="navbox"><tr><td>NAVJUNK</td></tr></table>
</div>
"""

def test_sections_and_cleaning():
    secs = html_to_sections(SAMPLE)
    heads = [s["heading"] for s in secs]
    assert "Infobox" in heads and "Lore" in heads
    blob = " ".join(s["text"] for s in secs)
    assert "Location: Anor Londo" in blob
    assert "NAVJUNK" not in blob and "[1]" not in blob and "[edit]" not in blob
    assert "- Fathered Gwynevere" in blob
