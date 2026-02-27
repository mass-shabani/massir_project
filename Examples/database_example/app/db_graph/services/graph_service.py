"""
Graph Service
─────────────────────────────────────────────────────────────
Collects live schema metadata from the active database
connection and assembles a JSON payload for the front-end
graph renderer.

Payload shape
─────────────
{
  "connected": bool,
  "connection_name": str,
  "tables": [
    {
      "name": str,
      "columns": [
        {
          "name": str,
          "type": str,
          "primary_key": bool,
          "nullable": bool,
          "unique": bool,
          "auto_increment": bool,
          "default": any,
          "length": int | None
        }
      ],
      "indexes": [
        { "name": str, "columns": [str], "unique": bool }
      ],
      "row_count": int | None
    }
  ],
  "edges": [
    {
      "name": str,
      "from_table": str,
      "from_columns": [str],
      "to_table": str,
      "to_columns": [str],
      "on_delete": str,
      "on_update": str
    }
  ],
  "stats": {
    "tables": int,
    "edges": int,
    "columns": int,
    "indexes": int
  }
}
"""
from typing import Any, Dict, List, Optional


class GraphService:
    """Builds the graph payload from live database metadata."""

    def __init__(self, connection_service):
        self._conn    = connection_service
        self._db      = connection_service.get_database_service()
        self._log     = connection_service._log

    # ── public ──────────────────────────────────────────────────

    @property
    def _active(self) -> Optional[str]:
        return self._conn.get_active_connection_name()

    async def get_graph_data(self) -> Dict[str, Any]:
        """Return the complete graph payload."""
        if not self._conn.is_connected() or not self._active:
            return {
                "connected":       False,
                "connection_name": "",
                "tables":          [],
                "edges":           [],
                "stats":           {}
            }

        try:
            table_names = await self._list_tables()
            all_indexes = await self._list_indexes()
            all_fks     = await self._list_foreign_keys()

            # index lookup: table → [idx, ...]
            idx_by_table: Dict[str, list] = {}
            for idx in all_indexes:
                t = idx.get("table", "")
                idx_by_table.setdefault(t, []).append(idx)

            tables       = []
            total_cols   = 0
            total_idx    = 0

            for tname in table_names:
                columns   = await self._get_columns(tname)
                tidx      = idx_by_table.get(tname, [])
                row_count = await self._get_row_count(tname)

                tables.append({
                    "name":      tname,
                    "columns":   columns,
                    "indexes": [
                        {
                            "name":    i.get("name", ""),
                            "columns": i.get("columns", []),
                            "unique":  bool(i.get("unique", False)),
                        }
                        for i in tidx
                    ],
                    "row_count": row_count,
                })
                total_cols += len(columns)
                total_idx  += len(tidx)

            # build edges from foreign keys
            edges = [
                {
                    "name":         fk.get("name", ""),
                    "from_table":   fk.get("table", ""),
                    "from_columns": fk.get("columns", []),
                    "to_table":     fk.get("ref_table", ""),
                    "to_columns":   fk.get("ref_columns", []),
                    "on_delete":    fk.get("on_delete", "RESTRICT"),
                    "on_update":    fk.get("on_update", "RESTRICT"),
                }
                for fk in all_fks
            ]

            return {
                "connected":       True,
                "connection_name": self._active,
                "tables":          tables,
                "edges":           edges,
                "stats": {
                    "tables":  len(tables),
                    "edges":   len(edges),
                    "columns": total_cols,
                    "indexes": total_idx,
                },
            }

        except Exception as exc:
            self._log(f"GraphService.get_graph_data error: {exc}", "ERROR")
            return {
                "connected": False,
                "connection_name": self._active or "",
                "tables":    [],
                "edges":     [],
                "stats":     {},
                "error":     str(exc),
            }

    # ── private helpers ──────────────────────────────────────────

    async def _list_tables(self) -> List[str]:
        try:
            conn = self._db.get_connection(self._active)
            return await conn.list_tables() or []
        except Exception as e:
            self._log(f"_list_tables error: {e}", "ERROR")
            return []

    async def _get_columns(self, table_name: str) -> List[dict]:
        try:
            # get_table_schema returns list[dict] (col.to_dict() per column)
            return await self._db.get_table_schema(table_name, self._active) or []
        except Exception as e:
            self._log(f"_get_columns({table_name}) error: {e}", "ERROR")
            return []

    async def _list_indexes(self) -> List[dict]:
        try:
            return await self._db.list_indexes(connection=self._active) or []
        except Exception as e:
            self._log(f"_list_indexes error: {e}", "ERROR")
            return []

    async def _list_foreign_keys(self) -> List[dict]:
        try:
            return await self._db.list_foreign_keys(connection=self._active) or []
        except Exception as e:
            self._log(f"_list_foreign_keys error: {e}", "ERROR")
            return []

    async def _get_row_count(self, table_name: str) -> Optional[int]:
        try:
            result = await self._db.fetch_one(
                f'SELECT COUNT(*) AS cnt FROM "{table_name}"',
                connection=self._active
            )
            return result.get("cnt", 0) if result else 0
        except Exception:
            return None
