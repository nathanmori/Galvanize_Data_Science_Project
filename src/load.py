# -*- coding: utf-8 -*-

# Author: Nathan Mori <nathanmori@gmail.com>

import psycopg2
import pdb
import os
import pandas as pd
from time import time
import sys
from sys import argv


def open_conn():
    """
    Open psycopg2 connection.

    Reads credentials from os environment variables.

    Parameters
    ----------
    None

    Returns
    -------
    conn : connection object
        Opened psycopg2 connection.

    c : cursor object
        Cursor in opened connection.
    """

    params = {
      'database': os.environ['TALENTFUL_PG_DATABASE'],
      'user': os.environ['TALENTFUL_PG_USER'],
      'password': os.environ['TALENTFUL_PG_PASSWORD'],
      'host': os.environ['TALENTFUL_PG_HOST'],
      'port': os.environ['TALENTFUL_PG_PORT']}
    conn = psycopg2.connect(**params)
    c = conn.cursor()

    return conn, c


def close_conn(conn):
    """
    Close psycopg2 connection.

    Parameters
    ----------
    conn : connection object
        psycopg2 connection to be closed.

    Returns
    -------
    None
    """
    
    conn.commit()
    conn.close()


def start_time(text):
    """
    Reports action and time at start of run.

    Parameters
    ----------
    text : string
        Description of action started, to be reported.

    Returns
    -------
    time : float
        Time at start of run.
    """

    sys.stdout.write(text.ljust(25))

    return time()


def end_time(start):
    """
    

    Parameters
    ----------


    Returns
    -------

    """

    print 'DONE (%.2f seconds).' % (time() - start)


def query_to_df(query):
    """
    

    Parameters
    ----------


    Returns
    -------

    """

    #print '\nExecuting query:'
    #print ' '.join(query.split())

    conn, c = open_conn()
    c.execute(query)
    data = c.fetchall()
    cols = [desc[0] for desc in c.description]
    close_conn(conn)

    return pd.DataFrame(data, columns=cols)


def query_columns(table):
    """
    

    Parameters
    ----------


    Returns
    -------

    """

    query = 'select * from %s limit 0' % table
    conn, c = open_conn()
    c.execute(query)
    cols = [desc[0] for desc in c.description]
    close_conn(conn)

    return cols


def load():
    """
    

    Parameters
    ----------


    Returns
    -------

    """

    start = start_time('Loading data...')

    cols = query_columns('github_meetup_staging')
    # NOTE: id is a unique and meaningless identifier
    # NOTE: name_similar, profile_pics_processed === True
    # NOTE: randomly_paired === False
    # NOTE: ignore face_pics
    # NOTE: profile_pics_matched === verified === correct_match
    # NOTE: github_meetup_combined is missing values
    # NOTE: ADDING github, meetup back in to check duplicates
    # NOTE: github_meetup_combined is not significant
    drop_cols = ['id',
                 'name_similar',
                 'profile_pics_processed',
                 'randomly_paired',
                 'face_pics_processed',
                 'face_pics_matched',
                 'verified',
                 'profile_pics_matched',
                 'github_meetup_combined']
    keep_cols = [col for col in cols if col not in drop_cols]
    col_string = ', '.join(keep_cols)

    matches_query = '''
        with matches as
        (
            select
                github
                , meetup
            from
                github_meetup_staging
            where
                correct_match = 't'
        )
        select
            %s
            , github_users.deserialized_text_document_vector as github_text
            , meetup_users.deserialized_text_document_vector as meetup_text
        from
            github_meetup_staging as similars
            left join github_users
                on similars.github = github_users.id
            left join meetup_users
                on similars.meetup = meetup_users.id
        where
            similars.github in (select github from matches)
            or similars.meetup in (select meetup from matches)
        ''' % col_string
    df = query_to_df(matches_query)

    end_time(start)

    return df

"""
NEED TO ADDRESS DUPLICATE github, meetup IN matches
- same person? consider a match OR label for multi-profiles?
- different person? drop rows OR create separate label for non-match matches
"""

if __name__ == '__main__':

    df = load()

    if 'write' in argv:

        if 'shard' in argv:
            
            ints_in_argv = [int(arg) for arg in argv if arg.isdigit()]
            rows = ints_in_argv[0] if ints_in_argv else 100
            df.head(rows).to_csv('../data/similars_shard.csv', encoding='utf-8')

        else:
            df.to_csv('../data/similars.csv', index=False, encoding='utf-8')
