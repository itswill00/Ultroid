# Ultroid - UserBot
# Copyright (C) 2021-2026 TeamUltroid
#
# This file is a part of < https://github.com/TeamUltroid/Ultroid/ >
# PLease read the GNU Affero General Public License in
# <https://github.com/TeamUltroid/pyUltroid/blob/main/LICENSE>.

import ast
import os
import re
import sys

from .. import run_as_module
from . import *

if run_as_module:
    from ..configs import Var


Redis = MongoClient = psycopg2 = Database = None
if Var.REDIS_URI or Var.REDISHOST:
    try:
        from redis import Redis
    except ImportError:
        LOGS.error(
            "'redis' package is required. Install it: pip install redis hiredis"
        )
        Redis = None
elif Var.MONGO_URI:
    try:
        from pymongo import MongoClient
    except ImportError:
        LOGS.error(
            "'pymongo' package is required. Install it: pip install pymongo[srv]"
        )
        MongoClient = None
elif Var.DATABASE_URL:
    try:
        import psycopg2
    except ImportError:
        LOGS.error(
            "'psycopg2-binary' is required for SQL database. Install it: pip install psycopg2-binary"
        )
        psycopg2 = None
else:
    try:
        from localdb import Database
    except ImportError:
        LOGS.error(
            "'localdb.json' package is required. Install it: pip install localdb.json"
        )
        Database = None

# --------------------------------------------------------------------------------------------- #


class _BaseDatabase:
    def __init__(self, *args, **kwargs):
        self._cache = {}

    def get_key(self, key):
        if key in self._cache:
            return self._cache[key]
        value = self._get_data(key)
        self._cache.update({key: value})
        return value

    def re_cache(self):
        self._cache.clear()
        for key in self.keys():
            self._cache.update({key: self.get_key(key)})

    def ping(self):
        return 1

    @property
    def usage(self):
        return 0

    def keys(self):
        return []

    def del_key(self, key):
        if key in self._cache:
            del self._cache[key]
        self.delete(key)
        return True

    def _get_data(self, key=None, data=None):
        if key:
            data = self.get(str(key))
        if data and isinstance(data, str):
            try:
                data = ast.literal_eval(data)
            except BaseException:
                pass
        return data

    def set_key(self, key, value, cache_only=False):
        value = self._get_data(data=value)
        self._cache[key] = value
        if cache_only:
            return
        return self.set(str(key), str(value))

    def rename(self, key1, key2):
        _ = self.get_key(key1)
        if _:
            self.del_key(key1)
            self.set_key(key2, _)
            return 0
        return 1


class MongoDB(_BaseDatabase):
    def __init__(self, key, dbname="UltroidDB"):
        self.dB = MongoClient(key, serverSelectionTimeoutMS=5000)
        self.db = self.dB[dbname]
        self.coll = self.db["UltroidData"]
        # Migration logic
        collections = self.db.list_collection_names()
        if "UltroidData" in collections:
            collections.remove("UltroidData")
        if collections:
            LOGS.info("Migrating old MongoDB collections to new schema...")
            for coll_name in collections:
                if x := self.db[coll_name].find_one({"_id": coll_name}):
                    self.coll.replace_one({"_id": coll_name}, {"_id": coll_name, "value": x["value"]}, upsert=True)
                self.db.drop_collection(coll_name)
            LOGS.info("MongoDB Migration completed.")
        super().__init__()

    def __repr__(self):
        return f"<Ultroid.MonGoDB\n -total_keys: {len(self.keys())}\n>"

    @property
    def name(self):
        return "Mongo"

    @property
    def usage(self):
        return self.db.command("dbstats")["dataSize"]

    def ping(self):
        if self.dB.server_info():
            return True

    def keys(self):
        return [x["_id"] for x in self.coll.find({}, {"_id": 1})]

    def set(self, key, value):
        self.coll.replace_one({"_id": key}, {"_id": key, "value": str(value)}, upsert=True)
        return True

    def delete(self, key):
        self.coll.delete_one({"_id": key})

    def get(self, key):
        if x := self.coll.find_one({"_id": key}):
            return x["value"]

    def flushall(self):
        self.dB.drop_database("UltroidDB")
        self._cache.clear()
        return True


# --------------------------------------------------------------------------------------------- #

# Thanks to "Akash Pattnaik" / @BLUE-DEVIL1134
# for SQL Implementation in Ultroid.
#
# Please use https://elephantsql.com/ !


class SqlDB(_BaseDatabase):
    def __init__(self, url):
        self._url = url
        self._connection = None
        self._cursor = None
        try:
            self._connection = psycopg2.connect(dsn=url)
            self._connection.autocommit = True
            self._cursor = self._connection.cursor()
            # Migration logic/Initial Table
            self._cursor.execute(
                "CREATE TABLE IF NOT EXISTS UltroidData (key_name TEXT PRIMARY KEY, value_data TEXT)"
            )
            # Check for old table and migrate
            self._cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ultroid')")
            if self._cursor.fetchone()[0]:
                LOGS.info("Migrating old SQL database to new schema...")
                self._cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'ultroid'")
                columns = [_[0] for _ in self._cursor.fetchall() if _[0] != 'ultroidcli']
                for col in columns:
                    self._cursor.execute(f"SELECT {col} FROM Ultroid WHERE {col} IS NOT NULL LIMIT 1")
                    val = self._cursor.fetchone()
                    if val:
                        self._cursor.execute(
                            "INSERT INTO UltroidData (key_name, value_data) VALUES (%s, %s) ON CONFLICT (key_name) DO NOTHING",
                            (col, str(val[0]))
                        )
                self._cursor.execute("DROP TABLE Ultroid")
                LOGS.info("SQL Migration completed.")
        except Exception as error:
            LOGS.exception(error)
            LOGS.info("Invalid SQL Database")
            if self._connection:
                self._connection.close()
            sys.exit()
        super().__init__()

    @property
    def name(self):
        return "SQL"

    @property
    def usage(self):
        self._cursor.execute(
            "SELECT pg_size_pretty(pg_total_relation_size('UltroidData')) AS size"
        )
        data = self._cursor.fetchall()
        return data[0][0]

    def keys(self):
        self._cursor.execute("SELECT key_name FROM UltroidData")
        data = self._cursor.fetchall()
        return [_[0] for _ in data]

    def get(self, variable):
        self._cursor.execute("SELECT value_data FROM UltroidData WHERE key_name = %s", (str(variable),))
        data = self._cursor.fetchone()
        return data[0] if data else None

    def set(self, key, value):
        self._cache.update({key: value})
        self._cursor.execute(
            "INSERT INTO UltroidData (key_name, value_data) VALUES (%s, %s) ON CONFLICT (key_name) DO UPDATE SET value_data = EXCLUDED.value_data",
            (str(key), str(value)),
        )
        return True

    def delete(self, key):
        self._cursor.execute("DELETE FROM UltroidData WHERE key_name = %s", (str(key),))
        return True

    def flushall(self):
        self._cache.clear()
        self._cursor.execute("DROP TABLE UltroidData")
        self._cursor.execute(
            "CREATE TABLE IF NOT EXISTS UltroidData (key_name TEXT PRIMARY KEY, value_data TEXT)"
        )
        return True


# --------------------------------------------------------------------------------------------- #


class RedisDB(_BaseDatabase):
    def __init__(
        self,
        host,
        port,
        password,
        platform="",
        logger=LOGS,
        *args,
        **kwargs,
    ):
        if host and ":" in host:
            spli_ = host.split(":")
            host = spli_[0]
            port = int(spli_[-1])
            if host.startswith("http"):
                logger.error("Your REDIS_URI should not start with http !")
                import sys

                sys.exit()
        elif not host or not port:
            logger.error("Port Number not found")
            import sys

            sys.exit()
        kwargs["host"] = host
        kwargs["password"] = password
        kwargs["port"] = port

        if platform.lower() == "qovery" and not host:
            var, hash_, host, password = "", "", "", ""
            for vars_ in os.environ:
                if vars_.startswith("QOVERY_REDIS_") and vars_.endswith("_HOST"):
                    var = vars_
            if var:
                hash_ = var.split("_", maxsplit=2)[1].split("_")[0]
            if hash_:
                kwargs["host"] = os.environ.get(f"QOVERY_REDIS_{hash_}_HOST")
                kwargs["port"] = os.environ.get(f"QOVERY_REDIS_{hash_}_PORT")
                kwargs["password"] = os.environ.get(f"QOVERY_REDIS_{hash_}_PASSWORD")
        self.db = Redis(**kwargs)
        self.set = self.db.set
        self.get = self.db.get
        self.keys = self.db.keys
        self.delete = self.db.delete
        super().__init__()

    @property
    def name(self):
        return "Redis"

    @property
    def usage(self):
        return sum(self.db.memory_usage(x) for x in self.keys())


# --------------------------------------------------------------------------------------------- #


class LocalDB(_BaseDatabase):
    def __init__(self):
        self.db = Database("ultroid")
        self.get = self.db.get
        self.set = self.db.set
        self.delete = self.db.delete
        super().__init__()

    @property
    def name(self):
        return "LocalDB"

    def keys(self):
        return self._cache.keys()

    def __repr__(self):
        return f"<Ultroid.LocalDB\n -total_keys: {len(self.keys())}\n>"


def UltroidDB():
    from .. import HOSTED_ON

    try:
        if Var.REDIS_URI or Var.REDISHOST:
            if Redis:
                return RedisDB(
                    host=Var.REDIS_URI or Var.REDISHOST,
                    password=Var.REDIS_PASSWORD or Var.REDISPASSWORD,
                    port=Var.REDISPORT,
                    platform=HOSTED_ON,
                    decode_responses=True,
                    socket_timeout=5,
                    retry_on_timeout=True,
                )
        elif Var.MONGO_URI:
            if MongoClient:
                return MongoDB(Var.MONGO_URI)
        elif Var.DATABASE_URL:
            if psycopg2:
                return SqlDB(Var.DATABASE_URL)
        
        # Default to LocalDB silently
        return LocalDB()
    except Exception as err:
        LOGS.debug(err)
        return LocalDB()


# --------------------------------------------------------------------------------------------- #
