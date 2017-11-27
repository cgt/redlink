#!/usr/bin/env python3

# vim: et:ts=4:sw=4:sts=4

from collections import namedtuple
import argparse
import logging
import os.path
import sys

import pymysql


Redlink = namedtuple("Redlink", ["title", "n"])


def redlinks(conn, categories):
    assert len(categories) >= 1

    with conn.cursor() as cur:
        q = """
            SELECT pl_title, count(pl_from) AS n FROM
            (
                SELECT DISTINCT pl_title, pl_from FROM pagelinks
                JOIN categorylinks ON pl_from = cl_from
                LEFT JOIN page ON pl_title = page_title
                WHERE
                    cl_to IN ({0})
                    AND
                    cl_type = 'page'
                    AND
                    page_id IS NULL
            ) AS tmp
            GROUP BY pl_title
            ORDER BY n DESC
            """
        q = q.format(", ".join(["%s"] * len(categories)))
        cur.execute(q, (*categories,))
        return [Redlink(x[0].decode("utf-8"), x[1]) for x in cur.fetchall()]


def all_subcats(conn, category):
    logging.debug("Getting subcategories for category {}.".format(category))
    with conn.cursor() as cur:
        q = """
            SELECT page_title FROM categorylinks
            JOIN page ON cl_from = page_id
            WHERE cl_to=%s and cl_type = 'subcat'
            """
        cur.execute(q, (category,))
        subcats = {x[0].decode("utf-8") for x in cur.fetchall()}
        new_subcats = set()
        for sc in subcats:
            new_subcats |= all_subcats(conn, sc)
        return subcats | new_subcats


def main(host, port, db, category):
    conn = pymysql.connect(
        database=db,
        host=host,
        port=port,
        read_default_file=os.path.expanduser("~/replica.my.cnf"),
        charset="utf8mb4",
    )

    try:
        conn.begin()
        cats = set([category]) | all_subcats(conn, category)
        logging.debug(
            "Got {} categories total. Getting redlinks.".format(len(cats))
        )
        for rl in redlinks(conn, cats):
            print("* {} [[{}]]".format(rl.n, rl.title.replace("_", " ")))

    finally:
        conn.commit()
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", action="store_true", help="Verbose logging")
    parser.add_argument("category", help="Category to search for red links")
    parser.add_argument("--dbhost", default="127.0.0.1", help="(default: %(default)s)")
    parser.add_argument("--dbport", default="4711", help="(default: %(default)s)")
    parser.add_argument("--dbname", default="dawiki_p", help="(default: %(default)s)")
    args = parser.parse_args()

    if args.v:
        logging.basicConfig(level=logging.DEBUG)

    main(
        host=args.dbhost,
        port=args.dbport,
        db=args.dbname,
        category=args.category,
    )
