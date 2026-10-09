from job_tracker.utils.html_text import html_to_text


def test_blocks_become_paragraphs_and_list_items_bullets() -> None:
    html = "<h2>What you'll do</h2><ul><li><p>Build   services</p></li><li>Ship &amp; run them</li></ul><p>Thanks</p>"

    assert html_to_text(html) == "What you'll do\n\n- Build services\n\n- Ship & run them\n\nThanks"


def test_blank_runs_collapse() -> None:
    assert html_to_text("<div>One</div><br><br><br><div>Two</div>") == "One\n\nTwo"
