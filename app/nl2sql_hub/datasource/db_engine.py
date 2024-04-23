import asyncio
import sqlalchemy.types
from sqlalchemy import create_engine, pool, MetaData, inspect, select, func, Table, text
from sqlalchemy.exc import UnsupportedCompilationError, ProgrammingError
from sqlalchemy.schema import CreateTable

from loguru import logger as log

from .datasource import DSColumn, DSTable, DSTableColumnSummary
from .datasource import get_url


class DBException(Exception):
    def __init__(self, msg, detail, raw):
        self.msg = msg
        self.detail = detail
        self.raw = raw
        super().__init__(msg, detail, raw)


# NOTE(gz): hack to support doris type column
from sqlalchemy.dialects.mysql import base as mysql_base

mysql_base.ischema_names["datetimev2"] = mysql_base.ischema_names["datetime"]
mysql_base.ischema_names["largeint"] = mysql_base.ischema_names["bigint"]
mysql_base.ischema_names["decimalv3"] = mysql_base.ischema_names["decimal"]
mysql_base.ischema_names["datev2"] = mysql_base.ischema_names["date"]

_engine_cache = {}


class DBEngine:
    def __init__(self, datasource):
        self.datasource = datasource
        self.engine = create_engine(get_url(datasource), poolclass=pool.NullPool)

    async def query(self, sql):
        # FIXME(gz): use async database driver
        def _query():
            with self.engine.connect() as conn:
                log.info("query sql: {}", sql.strip(";"))
                result = conn.execute(text(sql.strip(";")))
                log.info(f"query {sql} result: {result}")
                cols = result.keys()._keys
                return cols, [list(row) for row in result.fetchall()]

        try:
            res = await asyncio.to_thread(_query)
        except ProgrammingError as e:
            raise DBException("SQL 语句存在错误", str(e), e)
        except Exception as e:
            raise DBException("执行 SQL 语句失败", str(e), e)
        return res

    def fetch_tables_info(self, tables: list[str]):
        m = MetaData()
        m.reflect(bind=self.engine, only=tables)
        ret = list()
        for table_name in tables:
            table = m.tables[table_name]
            table_columns = [
                DSColumn(
                    name=c.name,
                    display_name=c.comment,
                    comment=c.comment,
                    data_type=db_type_to_data_type(c),
                    db_type=str(c.type),
                    is_primary_key=c.primary_key,
                    is_nullable=c.nullable,
                )
                for c in table.columns
            ]
            create_sql = ""
            try:
                create_sql = CreateTable(table).compile(self.engine).string
            except Exception as e:
                log.exception("print create table sql error: %s", e, exc_info=True)
            ret.append(
                DSTable(
                    table_name=table_name,
                    display_name=table.name,
                    comment=table.comment,
                    create_table_sql=create_sql,
                    columns=table_columns,
                )
            )
        return ret

    def table_summary(self, table_name, col: DSColumn):
        column_name = col.name
        metadata = MetaData()
        with self.engine.connect() as conn:
            try:
                table = Table(table_name, metadata, autoload_with=self.engine)
                inspector = inspect(conn)
                db_table_info = inspector.get_columns(table_name)
            except UnsupportedCompilationError as e:
                log.exception("get table info error: %s", e, exc_info=True)
                return
            column = None  # column obj from db by sqlalchemy
            for db_col in db_table_info:
                if db_col["name"] == column_name:
                    column = db_col
                    break
            if column is None:
                log.error(f"column {column_name} not found in table {table_name}")
                return

            col_summary = None
            if col.data_type == DataType.Numeric:
                q = select(
                    func.min(table.c[column_name]), func.max(table.c[column_name])
                )
                min_val, max_val = conn.execute(q).fetchone()
                col_summary = DSTableColumnSummary(
                    table_name=table_name,
                    column_name=column_name,
                    min_value=min_val,
                    max_value=max_val,
                )

            if col.is_enum:
                q = select(table.c[column_name]).distinct()
                distinct_vals = conn.execute(q).fetchall()
                if col_summary:
                    col_summary.distinct_count = len(distinct_vals)
                    col_summary.distinct_values = [v[0] for v in distinct_vals]
                else:
                    col_summary = DSTableColumnSummary(
                        datasource_id=self.datasource.id,
                        table_name=table_name,
                        column_name=column_name,
                        distinct_count=len(distinct_vals),
                        distinct_values=[v[0] for v in distinct_vals],
                    )
            return col_summary

    def tables(self):
        with self.engine.connect() as conn:
            inspector = inspect(conn)
            inspector.get_table_names()
            tableNames = inspect(self.engine).get_table_names()
            return self.fetch_tables_info(tableNames)


def get_db_engine(datasource) -> DBEngine:
    engine = DBEngine(datasource)
    return engine


class DataType:
    Numeric: str = "Numeric"
    String: str = "String"
    Text: str = "Text"
    Date: str = "Date"
    DateTime: str = "DateTime"
    Boolean: str = "Boolean"
    Unknown: str = "Unknown"


def db_type_to_data_type(col):
    t = col.type
    if issubclass(t.__class__, sqlalchemy.types.Numeric) or issubclass(
            t.__class__, sqlalchemy.types.INTEGER
    ):
        return DataType.Numeric
    elif issubclass(t.__class__, sqlalchemy.types.String):
        return DataType.String
    elif issubclass(t.__class__, sqlalchemy.types.Text):
        return DataType.Text
    elif issubclass(t.__class__, sqlalchemy.types.Boolean):
        return DataType.Boolean
    elif issubclass(t.__class__, sqlalchemy.types.Date):
        return DataType.Date
    elif issubclass(t.__class__, sqlalchemy.types.DateTime):
        return DataType.DateTime
    else:
        return DataType.Unknown
