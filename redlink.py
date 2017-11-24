#!/usr/bin/env python3

# Copyright Christoffer G. Thomsen 2017
# Distributed under the Boost Software License, Version 1.0.
#    (See accompanying file LICENSE or copy at
#     http://www.boost.org/LICENSE_1_0.txt)

import argparse
from collections import defaultdict
import logging
from operator import itemgetter
import sys

import pywikibot
import pywikibot.xmlreader

import mwparserfromhell


def normalize_title(title):
    return str(title).lower().strip()


def find_red_links(category, dump_path):
    """
    Args:
        category: Site category to search for red links in.
        dump: file object containing the XML dump.

    Returns:
        A dict mapping page titles to sets of red links in those pages.
    """

    logging.info("find_red_links: gathering titles in dump")
    dump = pywikibot.xmlreader.XmlDump(dump_path).parse()
    dump_titles = {normalize_title(str(p.title)) for p in dump if p.ns == "0"}
    logging.info("find_red_links: finished gathering titles")

    red_links = {}
    cat = pywikibot.Category(pywikibot.Site(), title=category)
    articles = {p.title() for p in cat.articles(recurse=True, namespaces=0, content=False)}

    dump = pywikibot.xmlreader.XmlDump(dump_path).parse()
    for page in (p for p in dump if p.title in articles):
        txt = mwparserfromhell.parse(page.text)
        links = (l for l in txt.ifilter_wikilinks() if ":" not in l.title)
        red = set()
        for link in links:
            title = normalize_title(link.title)
            if title not in dump_titles:
                red.add(str(link.title))
        if len(red) > 0:
            red_links[str(page.title)] = red
            logging.info("found {} red links in page {}".format(len(red), str(page.title)))

    return red_links


def sort_links_desc(red_links):
    # Count amount of each red link
    link_count = defaultdict(int)
    for links in red_links.values():
        for link in links:
            link_count[link] += 1

    # Delete empty link from dict. My original script did something that was
    # functionally equivalent to this, not sure if it's actually necessary,
    # so, for now, keep it and log it.
    empty = link_count.pop("", None)
    if empty is not None:
        logging.warning("Found empty title in link_count. n={}".format(empty))

    # Filter out links that contain "#".
    links = [(t, n) for t, n in link_count.items() if "#" not in t]

    # Sort links in descending order by amount of links.
    return sorted(links, key=itemgetter(1), reverse=True)


def main():
    parser = argparse.ArgumentParser(description="Find red links in Wikipedia XML dump.")
    parser.add_argument("-v", action="store_true", help="Verbose logging")
    parser.add_argument("category", help="Category to search")
    parser.add_argument("dump", help="path to XML dump file")
    args = parser.parse_args()

    level = logging.INFO
    if args.v:
        level = logging.DEBUG
    logging.basicConfig(level=level)

    links = sort_links_desc(find_red_links(args.category, args.dump))

    for title, link_count in links:
        print("* {} [[{}]]".format(link_count, title))


if __name__ == "__main__":
    main()
