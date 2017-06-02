# -*- coding: utf-8 -*-
#
# Copyright 2015 Tarek Galal <tare2.galal@gmail.com>
#
# This file is part of Gajim-OMEMO plugin.
#
# The Gajim-OMEMO plugin is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# Gajim-OMEMO is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# the Gajim-OMEMO plugin.  If not, see <http://www.gnu.org/licenses/>.
#
from .db_helpers import user_version


class SQLDatabase():
    """ SQL Database """

    def __init__(self, dbConn):
        """
        :type dbConn: Connection
        """
        self.dbConn = dbConn
        self.createDb()
        self.migrateDb()
        c = self.dbConn.cursor()
        c.execute("PRAGMA synchronous=NORMAL;")
        c.execute("PRAGMA journal_mode;")
        mode = c.fetchone()[0]
        # WAL is a persistent DB mode, dont override it if user has set it
        if mode != 'wal':
            c.execute("PRAGMA journal_mode=MEMORY;")
        self.dbConn.commit()

    def createDb(self):
        if user_version(self.dbConn) == 0:

            # Creates
            # IdentityKeyStore
            # PreKeyStore
            # SignedPreKeyStore
            # SessionStore
            # EncryptionStore

            create_tables = '''
                CREATE TABLE IF NOT EXISTS identities (
                    _id INTEGER PRIMARY KEY AUTOINCREMENT, recipient_id TEXT,
                    registration_id INTEGER, public_key BLOB, private_key BLOB,
                    next_prekey_id INTEGER, timestamp INTEGER, trust INTEGER,
                    shown INTEGER DEFAULT 0);

                CREATE UNIQUE INDEX IF NOT EXISTS
                    public_key_index ON identities (public_key, recipient_id);

                CREATE TABLE IF NOT EXISTS prekeys(
                    _id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prekey_id INTEGER UNIQUE, sent_to_server BOOLEAN,
                    record BLOB);

                CREATE TABLE IF NOT EXISTS signed_prekeys (
                    _id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prekey_id INTEGER UNIQUE,
                    timestamp NUMERIC DEFAULT CURRENT_TIMESTAMP, record BLOB);

                CREATE TABLE IF NOT EXISTS sessions (
                    _id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient_id TEXT, device_id INTEGER,
                    record BLOB, timestamp INTEGER, active INTEGER DEFAULT 1,
                    UNIQUE(recipient_id, device_id));

                CREATE TABLE IF NOT EXISTS encryption_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jid TEXT UNIQUE,
                    encryption INTEGER
                    );
                '''

            create_db_sql = """
                BEGIN TRANSACTION;
                %s
                PRAGMA user_version=5;
                END TRANSACTION;
                """ % (create_tables)
            self.dbConn.executescript(create_db_sql)

    def migrateDb(self):
        """ Migrates the DB
        """

        # Find all double entrys and delete them
        if user_version(self.dbConn) < 2:
            delete_dupes = """ DELETE FROM identities WHERE _id not in (
                                SELECT MIN(_id)
                                FROM identities
                                GROUP BY
                                recipient_id, public_key
                                );
                            """

            self.dbConn.executescript(""" BEGIN TRANSACTION;
                                     %s
                                     PRAGMA user_version=2;
                                     END TRANSACTION;
                                 """ % (delete_dupes))

        if user_version(self.dbConn) < 3:
            # Create a UNIQUE INDEX so every public key/recipient_id tuple
            # can only be once in the db
            add_index = """ CREATE UNIQUE INDEX IF NOT EXISTS
                            public_key_index
                            ON identities (public_key, recipient_id);
                        """

            self.dbConn.executescript(""" BEGIN TRANSACTION;
                                          %s
                                          PRAGMA user_version=3;
                                          END TRANSACTION;
                                      """ % (add_index))

        if user_version(self.dbConn) < 4:
            # Adds column "active" to the sessions table
            add_active = """ ALTER TABLE sessions
                             ADD COLUMN active INTEGER DEFAULT 1;
                         """

            self.dbConn.executescript(""" BEGIN TRANSACTION;
                                          %s
                                          PRAGMA user_version=4;
                                          END TRANSACTION;
                                      """ % (add_active))

        if user_version(self.dbConn) < 5:
            # Adds DEFAULT Timestamp
            add_timestamp = """
                DROP TABLE signed_prekeys;
                CREATE TABLE IF NOT EXISTS signed_prekeys (
                    _id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prekey_id INTEGER UNIQUE,
                    timestamp NUMERIC DEFAULT CURRENT_TIMESTAMP, record BLOB);
                ALTER TABLE identities ADD COLUMN shown INTEGER DEFAULT 0;
                UPDATE identities SET shown = 1;
            """

            self.dbConn.executescript(""" BEGIN TRANSACTION;
                                          %s
                                          PRAGMA user_version=5;
                                          END TRANSACTION;
                                      """ % (add_timestamp))
