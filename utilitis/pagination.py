from urllib.parse import urlencode


# ========== Reusable Pagination Utility ==========
def get_pager(url, total, page=1, per_page=12, url_args=None):
    """
    Ei function ta ANY controller e, ANY model er jonno pagination korte pare.

    :param url: base url (jemon '/projects', '/tasks', '/invoices')
    :param total: total record count (search_count theke ashbe)
    :param page: current page number (kw.get('page', 1) theke ashbe)
    :param per_page: proti page e koto ta item (12, 6, 20 - jekono value dite parben)
    :param url_args: extra filter/query params (status, search etc.)
    :return: pagination er shob info soho ekta dict
    """
    url_args = url_args or {}
    page = int(page) if str(page).isdigit() else 1

    total_pages = max(1, -(-total // per_page))  # ceil division (round up)
    page = max(1, min(page, total_pages))         # page range er baire gele fix hobe

    offset = (page - 1) * per_page

    # "Showing X-Y of Z" text er jonno
    start = offset + 1 if total else 0
    end = min(offset + per_page, total)

    filtered_url_args = {
        str(key): value
        for key, value in url_args.items()
        if value not in (None, '', False)
    }
    query_string = urlencode(filtered_url_args)
    query_string_xml = query_string.replace("&", "&amp;")

    return {
        'page': page,
        'per_page': per_page,
        'offset': offset,
        'total': total,
        'total_pages': total_pages,
        'start': start,
        'end': end,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1,
        'next_page': page + 1,
        'pages': list(range(1, total_pages + 1)),
        'url': url,
        'url_args': url_args,
        'query_string': query_string,
        'query_string_xml': query_string_xml,
    }
