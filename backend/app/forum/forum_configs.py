"""
LeakHunter V3 — Forum Configuration Registry

Each forum gets a config dict defining its HTML structure so the Playwright
scraper knows how to login, navigate threads, and extract posts.

For clearweb testing, we include a phpBB config.
For dark web forums, add configs as you register accounts.
"""

FORUM_CONFIGS = {
    # ──────────────────────────────────────────────
    # Clearweb test target — phpBB-based forums
    # ──────────────────────────────────────────────
    "phpbb_test": {
        "description": "Generic phpBB 3.x forum (clearweb test target)",
        "use_tor": False,
        "login_url_path": "/ucp.php?mode=login",
        "username_field": "#username",
        "password_field": "#password",
        "submit_button": "input[name='login']",
        "login_success_indicator": "a[href*='ucp.php?mode=logout']",  # logout link means we're logged in
        "thread_list_url_path": "/search.php?search_id=active_topics",
        "thread_row_selector": "li.row",
        "thread_title_selector": "a.topictitle",
        "thread_link_selector": "a.topictitle",
        "post_content_selector": "div.content",
        "post_author_selector": "a.username, a.username-coloured",
        "post_date_selector": "time",
        "pagination_next_selector": "a[rel='next']",
        "max_pages": 3,
    },

    # ──────────────────────────────────────────────
    # BreachForums (MyBB-based) — placeholder
    # ──────────────────────────────────────────────
    "breachforums": {
        "description": "BreachForums (MyBB-based dark web forum)",
        "use_tor": True,
        "login_url_path": "/member.php?action=login",
        "username_field": "input[name='username']",
        "password_field": "input[name='password']",
        "submit_button": "input[type='submit'][value='Login']",
        "login_success_indicator": "a[href*='member.php?action=logout']",
        "thread_list_url_path": "/search.php?action=getdaily",
        "thread_row_selector": "tr.inline_row",
        "thread_title_selector": "span.subject_new a, span.subject_old a",
        "thread_link_selector": "span.subject_new a, span.subject_old a",
        "post_content_selector": "div.post_body",
        "post_author_selector": "span.largetext a",
        "post_date_selector": "span.post_date",
        "pagination_next_selector": "a.pagination_next",
        "max_pages": 5,
    },

    # ──────────────────────────────────────────────
    # XSS.is (XenForo-based) — placeholder
    # ──────────────────────────────────────────────
    "xss": {
        "description": "XSS.is (XenForo-based dark web forum)",
        "use_tor": True,
        "login_url_path": "/login/",
        "username_field": "input[name='login']",
        "password_field": "input[name='password']",
        "submit_button": "button.button--primary",
        "login_success_indicator": "a[href*='/logout']",
        "thread_list_url_path": "/whats-new/posts/",
        "thread_row_selector": "div.structItem",
        "thread_title_selector": "div.structItem-title a",
        "thread_link_selector": "div.structItem-title a",
        "post_content_selector": "article.message-body div.bbWrapper",
        "post_author_selector": "a.username",
        "post_date_selector": "time.u-dt",
        "pagination_next_selector": "a.pageNav-jump--next",
        "max_pages": 5,
    },
}


def get_forum_config(forum_name: str) -> dict:
    """Returns the config dict for a given forum name, or None if not found."""
    return FORUM_CONFIGS.get(forum_name.lower())


def list_forum_configs() -> list:
    """Returns a list of all registered forum config names."""
    return list(FORUM_CONFIGS.keys())
