"""SQL Server source implementation.

This source connects to a SQL Server database and generates entities for each table
based on its schema structure. It dynamically creates entity classes at runtime
using the PolymorphicEntity system.
"""

from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional, Type

import aioodbc

from airweave.platform.auth.schemas import AuthType
from airweave.platform.decorators import source
from airweave.platform.entities._base import ChunkEntity, PolymorphicEntity
from airweave.platform.sources._base import BaseSource

# Mapping of SQL Server types to Python types
SQLSERVER_TYPE_MAP = {
    "int": int,
    "bigint": int,
    "smallint": int,
    "tinyint": int,
    "decimal": float,
    "numeric": float,
    "float": float,
    "real": float,
    "money": float,
    "smallmoney": float,
    "varchar": str,
    "nvarchar": str,
    "char": str,
    "nchar": str,
    "text": str,
    "ntext": str,
    "bit": bool,
    "datetime": datetime,
    "datetime2": datetime,
    "datetimeoffset": datetime,
    "date": datetime,
    "time": datetime,
    "xml": str,
}


@source(
    "SQL Server", "sql_server", AuthType.config_class, "SQLServerAuthConfig", labels=["Database"]
)
class SQLServerSource(BaseSource):
    """SQL Server source implementation.

    This source connects to a SQL Server database and generates entities for each table
    in the specified schemas. It uses database introspection to:
    1. Discover tables and their structures
    2. Create appropriate entity classes dynamically
    3. Generate entities for each table's data
    """

    def __init__(self):
        """Initialize the SQL Server source."""
        self.conn: Optional[aioodbc.Connection] = None
        self.entity_classes: Dict[str, Type[PolymorphicEntity]] = {}

    @classmethod
    async def create(cls, config: Dict[str, Any]) -> "SQLServerSource":
        """Create a new SQL Server source instance.

        Args:
            config: Dictionary containing connection details:
                - host: Database host
                - port: Database port
                - database: Database name
                - user: Username
                - password: Password
                - schema: Schema to sync (defaults to 'dbo')
                - tables: Table to sync (defaults to '*')
        """
        instance = cls()
        instance.config = config.model_dump()
        return instance

    async def _connect(self) -> None:
        """Establish database connection with timeout and error handling."""
        if not self.conn:
            try:
                # Convert localhost to 127.0.0.1 to avoid DNS resolution issues
                host = (
                    "127.0.0.1"
                    if self.config["host"].lower() in ("localhost", "127.0.0.1")
                    else self.config["host"]
                )

                dsn = (
                    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
                    f"SERVER={host},{self.config['port']};"
                    f"DATABASE={self.config['database']};"
                    f"UID={self.config['user']};"
                    f"PWD={self.config['password']};"
                    "Timeout=10;"
                )

                self.conn = await aioodbc.connect(dsn=dsn)
            except Exception as e:
                raise ValueError(f"Database connection failed: {str(e)}") from e

    async def _get_table_info(self, schema: str, table: str) -> Dict[str, Any]:
        """Get table structure information.

        Args:
            schema: Schema name
            table: Table name

        Returns:
            Dictionary containing column information and primary keys
        """
        async with self.conn.cursor() as cursor:
            # Get column information
            columns_query = """
                SELECT
                    c.COLUMN_NAME,
                    c.DATA_TYPE,
                    c.IS_NULLABLE,
                    c.COLUMN_DEFAULT
                FROM INFORMATION_SCHEMA.COLUMNS c
                WHERE c.TABLE_SCHEMA = ? AND c.TABLE_NAME = ?
                ORDER BY c.ORDINAL_POSITION
            """
            await cursor.execute(columns_query, (schema, table))
            columns = await cursor.fetchall()

            # Get primary key information
            pk_query = """
                SELECT c.COLUMN_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE c
                    ON tc.CONSTRAINT_NAME = c.CONSTRAINT_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                    AND tc.TABLE_SCHEMA = ?
                    AND tc.TABLE_NAME = ?
            """
            await cursor.execute(pk_query, (schema, table))
            primary_keys = [row[0] for row in await cursor.fetchall()]

            # Build column metadata
            column_info = {}
            for col in columns:
                sql_type = col[1].lower()
                python_type = SQLSERVER_TYPE_MAP.get(sql_type, Any)

                column_info[col[0]] = {
                    "python_type": python_type,
                    "nullable": col[2] == "YES",
                    "default": col[3],
                    "sql_type": sql_type,
                }

            return {
                "columns": column_info,
                "primary_keys": primary_keys,
            }

    async def _create_entity_class(self, schema: str, table: str) -> Type[PolymorphicEntity]:
        """Create a entity class for a specific table.

        Args:
            schema: Schema name
            table: Table name

        Returns:
            Dynamically created entity class for the table
        """
        table_info = await self._get_table_info(schema, table)

        return PolymorphicEntity.create_table_entity_class(
            table_name=table,
            schema_name=schema,
            columns=table_info["columns"],
            primary_keys=table_info["primary_keys"],
        )

    async def _get_tables(self, schema: str) -> List[str]:
        """Get list of tables in a schema.

        Args:
            schema: Schema name

        Returns:
            List of table names
        """
        async with self.conn.cursor() as cursor:
            query = """
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = ?
                AND TABLE_TYPE = 'BASE TABLE'
            """
            await cursor.execute(query, (schema,))
            tables = await cursor.fetchall()
            return [table[0] for table in tables]

    async def generate_entities(self) -> AsyncGenerator[ChunkEntity, None]:
        """Generate entities for all tables in specified schemas."""
        try:
            await self._connect()

            schema = self.config.get("schema", "dbo")
            tables_config = self.config.get("tables", "*")

            # Handle both wildcard and CSV list of tables
            if tables_config == "*":
                tables = await self._get_tables(schema)
            else:
                # Split by comma and strip whitespace
                tables = [t.strip() for t in tables_config.split(",")]
                # Validate that all specified tables exist
                available_tables = await self._get_tables(schema)
                invalid_tables = set(tables) - set(available_tables)
                if invalid_tables:
                    raise ValueError(
                        f"Tables not found in schema '{schema}': {', '.join(invalid_tables)}"
                    )

            async with self.conn.cursor() as cursor:
                for table in tables:
                    # Create entity class if not already created
                    if f"{schema}.{table}" not in self.entity_classes:
                        self.entity_classes[f"{schema}.{table}"] = await self._create_entity_class(
                            schema, table
                        )

                    entity_class = self.entity_classes[f"{schema}.{table}"]

                    # Fetch and yield data
                    BATCH_SIZE = 50
                    offset = 0

                    while True:
                        # Fetch records in batches using OFFSET FETCH
                        batch_query = f"""
                            SELECT *
                            FROM [{schema}].[{table}]
                            ORDER BY (SELECT NULL)
                            OFFSET {offset} ROWS
                            FETCH NEXT {BATCH_SIZE} ROWS ONLY
                        """
                        await cursor.execute(batch_query)
                        records = await cursor.fetchall()

                        # Break if no more records
                        if not records:
                            break

                        # Get column names from cursor description
                        columns = [column[0] for column in cursor.description]

                        # Process the batch
                        for record in records:
                            # Convert record to dictionary using column names
                            data = dict(zip(columns, record, strict=False))
                            model_fields = entity_class.model_fields
                            primary_keys = model_fields["primary_key_columns"].default_factory()
                            pk_values = [str(data[pk]) for pk in primary_keys]
                            entity_id = f"{schema}.{table}:" + ":".join(pk_values)

                            entity = entity_class(entity_id=entity_id, **data)
                            yield entity

                        # Increment offset for next batch
                        offset += BATCH_SIZE

        finally:
            if self.conn:
                await self.conn.close()
                self.conn = None
